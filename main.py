from internal.profiler import profiler
from internal.vector2 import Vector2
from pythonosc import udp_client
import tkinter as tk
import config, openvr, math, time


running = True
state: function = None
ovr: openvr.IVRSystem = None

hipTrackerIndex = None


class transform2D:
    # Rotation will be stored in radians, -pi to pi
    @profiler
    def __init__(self, position: Vector2 = Vector2(0, 0), rotation: float = 0.0):
        self.position = position
        self.rotation = rotation

    # Returns the squared distance between this transform and another transform, counting 180 degree rotation as 1 meter of distance
    @profiler
    def sq_distance(self, other: "transform2D") -> float:
        rotDist = abs(self.rotation - other.rotation) / math.pi
        if rotDist > 1.0:
            rotDist = 2.0 - rotDist
        
        return self.position.sq_distance(other.position) + rotDist ** 2

    @profiler
    def distance(self, other: "transform2D") -> float:
        return math.sqrt(self.sq_distance(other))

class path2D(list):
    @profiler
    def __init__(self, points: list[transform2D] = []):
        self.points = points

    # Allow using a float for the index, which will interpolate between points
    @profiler
    def __getitem__(self, index: float) -> transform2D:
        if isinstance(index, int):
            return self.points[index % len(self.points)]
        
        lowerIndex = int(math.floor(index)) % len(self.points)
        upperIndex = int(math.ceil(index)) % len(self.points)

        if lowerIndex == upperIndex:
            return self.points[lowerIndex]

        lowerPoint = self.points[lowerIndex]
        upperPoint = self.points[upperIndex]

        t = index - lowerIndex

        interpPosition = lowerPoint.position * (1 - t) + upperPoint.position * t
        interpRotation = lowerPoint.rotation * (1 - t) + upperPoint.rotation * t

        return transform2D(interpPosition, interpRotation)

    @profiler
    def find_closest_point(self, point: transform2D) -> float:
        closestIndex = 0
        closestDistance = float('inf')

        for i, p in enumerate(self.points):
            edgeVector = self[i + 1].position - p.position
            t = max(0, min(1, ((point.position - p.position) * edgeVector) / (edgeVector * edgeVector))) if edgeVector != Vector2(0, 0) else 0

            edgeClosestIndex = i + t
            edgeClosestDist = point.sq_distance(self[edgeClosestIndex])

            if edgeClosestDist < closestDistance:
                closestIndex = edgeClosestIndex
                closestDistance = edgeClosestDist
        
        return closestIndex


# Need to get the transform of a device in 2D space, with rotation being the yaw angle
@profiler
def getDeviceTransform(ovr: openvr.IVRSystem, index: int) -> transform2D:
    pose = ovr.getDeviceToAbsoluteTrackingPose(openvr.TrackingUniverseStanding, 0, openvr.k_unMaxTrackedDeviceCount)[index]

    if not pose.bPoseIsValid:
        return None

    matrix = pose.mDeviceToAbsoluteTracking

    return transform2D(Vector2(matrix[0][3], matrix[2][3]), math.atan2(matrix[1][0], matrix[0][0]))


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


def on_close():
    global running
    running = False
    root.destroy()
root.protocol("WM_DELETE_WINDOW", on_close)

def setState(newState: function):
    global state
    state = newState
    print(f"State set to {state.__qualname__ if state != None else None}")

def setStateButton(newState: function) -> function:
    def inner():
        global state
        state = newState
        print(f"State set to {state.__qualname__}")
    return inner

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

def calibrateOffset(dt: float):
    pass

calibrateOffsetButton = tk.Button(
    root,
    text="Calibrate hip offset",
    command=setStateButton(calibrateOffset)
)
calibrateOffsetButton.place(anchor="s", relx=0.5, rely=1, relheight=1/8, relwidth=1/3)

def activeNoPath(dt: float):
    pass

activateButton = tk.Button(
    root,
    text="Activate",
    command=setStateButton(activeNoPath)
)
activateButton.place(anchor="se", relx=1, rely=1, relheight=1/8, relwidth=1/3)

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
                            break
                    
            except FileNotFoundError:
                if state != findHipTracker:
                    setState(findHipTracker)
                hipTrackerIndex = -1

        startTime = time.time()

        if state != None:
            state(dt)

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