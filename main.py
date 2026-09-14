from internal.profiler import profiler
from internal.vector2 import Vector2
from internal.transform2D import Transform2D
from internal.timer import Timer
from pythonosc import udp_client
import tkinter as tk
import config, openvr, math, time


running = True
state: function = None
initState = False
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

class Indicator:
    def __init__(self, transform: Transform2D, scale: float, canvasBounds: tuple[Vector2, Vector2]):
        self.transform = transform
        self.scale = scale
        self.canvasBounds = canvasBounds

def on_close():
    global running
    running = False
    root.destroy()
root.protocol("WM_DELETE_WINDOW", on_close)

def setState(newState: function):
    global state, initState
    state = newState
    initState = True
    print(f"State set to {state.__qualname__ if state != None else None}")

def setStateButton(newState: function) -> function:
    def inner():
        global state, initState
        state = newState
        initState = True
        print(f"State set to {state.__qualname__}")
    return inner

@profiler
def findHipTracker(dt: float):
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
    command=setStateButton(findHipTracker)
)
findHipTrackerButton.place(anchor="sw", relx=0, rely=1, relheight=1/8, relwidth=1/3)

lastOffset: Transform2D
avgOffset: Transform2D
calibrateOffsetTimer: Timer

@profiler
def calibrateOffset(dt: float):
    global initState, offset, lastOffset, avgOffset, calibrateOffsetTimer

    headTransform = getDeviceTransform(0)
    hipTransform = getDeviceTransform(hipTrackerIndex)

    if headTransform == None:
        print("Error: head transform is none!")
        return
    elif hipTransform == None:
        print("Error: hip transform is none!")
        return

    currentOffset = Transform2D(hipTransform.position - headTransform.position, hipTransform.rotation - headTransform.rotation)

    if initState:
        lastOffset = currentOffset.copy()
        avgOffset = currentOffset.copy()
        calibrateOffsetTimer = Timer(1)

        initState = False

    if lastOffset.sq_distance(currentOffset) >= config.DIST_THRES ** 2:
        canvas.itemconfig(alert, text="Please hold still")
        calibrateOffsetTimer.restart()
        avgOffset = currentOffset.copy()
        print("Too much movement, calibration restarted")
    elif calibrateOffsetTimer.done():
        offset = avgOffset
        setState(None)
        print(f"Calibration complete, set to {offset}")
    else:
        canvas.itemconfig(alert, text="Calibrating...")
        progress = calibrateOffsetTimer.progress()
        avgOffset.position = avgOffset.position * progress + currentOffset.position * (1 - progress)
        avgOffset.rotation = avgOffset.rotation * progress + currentOffset.rotation * (1 - progress)
        print(f"Current Offset: {currentOffset}")
        print(f"Average Offset: {avgOffset}")

    lastOffset = currentOffset

calibrateOffsetButton = tk.Button(
    root,
    text="Calibrate hip offset",
    command=setStateButton(calibrateOffset)
)
calibrateOffsetButton.place(anchor="s", relx=0.5, rely=1, relheight=1/8, relwidth=1/3)

@profiler
def activeNoPath(dt: float):
    pass

activateButton = tk.Button(
    root,
    text="Activate",
    command=setStateButton(activeNoPath)
)
activateButton.place(anchor="se", relx=1, rely=1, relheight=1/8, relwidth=1/3)

@profiler
def activeWithPath(dt: float):
    pass

frame.pack()
canvas.pack()


if __name__ == "__main__":
    dt = config.TARGET_FRAMERATE

    while running:
        canvas.itemconfig(alert, text="")

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

        startTime = time.time()

        if state != None:
            state(dt)

        if offset != None:
            print(offset)

        try:
            root.update()
        except tk.TclError:
            break

        frameTime = time.time() - startTime
        if frameTime < config.TARGET_FRAMERATE:
            dt = config.TARGET_FRAMERATE
            time.sleep(config.TARGET_FRAMERATE - frameTime)
        else:
            dt = frameTime