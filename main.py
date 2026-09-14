from internal.profiler import profiler
from internal.vector2 import Vector2
from internal.transform2D import Transform2D
from internal.timer import Timer
from pythonosc import udp_client
import tkinter as tk
import config, openvr, math, time, asyncio


running = True
state: function = None
ovr: openvr.IVRSystem = None

hipTrackerIndex = None
offset: Transform2D = None


# Need to get the transform of a device in 2D space, with rotation being the yaw angle
@profiler
def getDeviceTransform(index: int) -> Transform2D:
    pose = ovr.getDeviceToAbsoluteTrackingPose(openvr.TrackingUniverseStanding, 0, openvr.k_unMaxTrackedDeviceCount)[index]

    if not pose.bPoseIsValid:
        return None

    matrix = pose.mDeviceToAbsoluteTracking

    return Transform2D(Vector2(matrix[0][3], matrix[2][3]), math.atan2(matrix[1][0], matrix[0][0]))


# Initialize the main window
root = tk.Tk()
root.title("Auto RP Walk")
root.geometry(f"{config.CANVAS_WIDTH}x{config.CANVAS_HEIGHT}")

# Create the canvas, offset to the center of the world
frame = tk.Frame(root, width=config.CANVAS_WIDTH, height=config.CANVAS_HEIGHT)
canvas = tk.Canvas(frame, width=config.CANVAS_WIDTH, height=config.CANVAS_HEIGHT, offset="center", background="black")

alert = canvas.create_text(
    config.CANVAS_WIDTH / 2, config.CANVAS_HEIGHT / 2 - 40,
    fill="white", anchor="center", font=("Ubuntu", 40), justify="center", width=config.CANVAS_WIDTH / 2
)

@profiler
def getDeltaTimeAndWait(exit: bool = False):
    dt = 0
    lastCalled = time.time()

    yield config.TARGET_FRAMERATE

    while not exit:
        dt = time.time() - lastCalled
        if dt < config.TARGET_FRAMERATE:
            time.sleep(config.TARGET_FRAMERATE - dt)
            yield config.TARGET_FRAMERATE
        else:
            yield dt

    return dt

def setState(newState: function) {
    global state
    state = newState
    print(f"State set to {state.__qualname__}")
}

def close():
    print("Exiting...")
    global running
    running = False
    root.destroy()
root.protocol("WM_DELETE_WINDOW", close)

@profiler
def initialize():
    if ovr == None:
        try:
            ovr = openvr.init(openvr.VRApplication_Background)
            print("OpenVR initialized")
        except openvr.error_code.InitError_Init_NoServerForBackgroundApp:
            canvas.itemconfig(alert, text="SteamVR not found")
            if state != None:
                setState(None)
            ovr = None
    elif hipTrackerIndex == None:
        try:
            with open("hip-tracker-serial-number.txt", "r") as f:
                hipTrackerSerial = f.read()
                for i in range(openvr.k_unMaxTrackedDeviceCount):
                    if ovr.getTrackedDeviceClass(i) == openvr.TrackedDeviceClass_GenericTracker and hipTrackerSerial == ovr.getStringTrackedDeviceProperty(i, openvr.Prop_SerialNumber_String):
                        hipTrackerIndex = i
                        print(f"Hip tracker identified at index {i}, serial {hipTrackerSerial}")
                        break
                if hipTrackerIndex == None:
                    canvas.itemconfig(alert, text="Enable your hip tracker, or identify it if it is already on")
        except:
            print("hip-tracker-serial-number.txt not found or invalid")
            setState(findHipTracker)
            hipTrackerIndex = -1
    elif offset == None:
        canvas.itemconfig(alert, text="Hip offset not set, please calibrate")
    else:
        setState(None)

@profiler
def findHipTracker():
    tracker = None
    for i in range(openvr.k_unMaxTrackedDeviceCount):
        if ovr.getTrackedDeviceClass(i) == openvr.TrackedDeviceClass_GenericTracker:
            if tracker == None:
                tracker = i
            else:
                canvas.itemconfig(alert, text="Disable all trackers except for the hip")
                return
    
    if tracker == None:
        canvas.itemconfig(alert, text="Enable only the hip tracker")
        return

    global hipTrackerIndex
    hipTrackerIndex = tracker
    hipTrackerSerial = ovr.getStringTrackedDeviceProperty(tracker, openvr.Prop_SerialNumber_String)
    print(f"Hip tracker identified as {hipTrackerSerial}")
    with open("hip-tracker-serial-number.txt", "w") as f:
        f.write(hipTrackerSerial)
    
    setState(None)

findHipTrackerButton = tk.Button(
    root,
    text="Set hip tracker",
    command=findHipTracker
)
findHipTrackerButton.place(anchor="sw", relx=0, rely=1, relheight=1/8, relwidth=1/3)

@profiler
def calibrateOffset():
    global offset

    lastOffset: Transform2D
    avgOffset: Transform2D
    calibrateOffsetTimer = Timer(1)

    while running:
        dt = getDeltaTimeAndWait()

        headTransform = getDeviceTransform(0)
        hipTransform = getDeviceTransform(hipTrackerIndex)

        if headTransform == None:
            print("Error: head transform is none!")
            break
        elif hipTransform == None:
            print("Error: hip transform is none!")
            break

        currentOffset = Transform2D(hipTransform.position - headTransform.position, hipTransform.rotation - headTransform.rotation)

        if lastOffset and lastOffset.sq_distance(currentOffset) >= config.DIST_THRES ** 2:
            canvas.itemconfig(alert, text="Please hold still")
            calibrateOffsetTimer.restart()
            avgOffset = currentOffset.copy()
            print("Too much movement, calibration restarted")
        elif calibrateOffsetTimer.done():
            offset = avgOffset
            print(f"Calibration complete, set to {offset}")
            break
        else:
            canvas.itemconfig(alert, text="Calibrating...")
            progress = calibrateOffsetTimer.progress()
            avgOffset.position = avgOffset.position * progress + currentOffset.position * (1 - progress)
            avgOffset.rotation = avgOffset.rotation * progress + currentOffset.rotation * (1 - progress)
            print(f"Current Offset: {currentOffset}")
            print(f"Average Offset: {avgOffset}")

        lastOffset = currentOffset
        root.update()

    setState(None)
    getDeltaTimeAndWait(exit=True)

calibrateOffsetButton = tk.Button(
    root,
    text="Calibrate hip offset",
    command=calibrateOffset
)
calibrateOffsetButton.place(anchor="s", relx=0.5, rely=1, relheight=1/8, relwidth=1/3)

@profiler
def activeNoPath():
    pass

activateButton = tk.Button(
    root,
    text="Activate",
    command=activeNoPath
)
activateButton.place(anchor="se", relx=1, rely=1, relheight=1/8, relwidth=1/3)

@profiler
def activeWithPath():
    pass

frame.pack()
canvas.pack()


if __name__ == "__main__":
    setState(initialize)

    while running:
        canvas.itemconfig(alert, text="")

        if state != None:
            state()

        if offset != None:
            print(f"Offset: {offset}")

        root.update()