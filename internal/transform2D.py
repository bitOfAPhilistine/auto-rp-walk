from internal.profiler import profiler
from internal.vector2 import Vector2
import math


class Transform2D:
    # Rotation will be stored in radians, -pi to pi
    @profiler
    def __init__(self, position: Vector2 = Vector2(0, 0), rotation: float = 0.0):
        self.position = position
        self.rotation = rotation

    # Returns the squared distance between this transform and another transform, counting 180 degree rotation as 1 meter of distance
    @profiler
    def sq_distance(self, other: "Transform2D") -> float:
        rotDist = abs(self.rotation - other.rotation) / math.pi
        if rotDist > 1.0:
            rotDist = 2.0 - rotDist
        
        return self.position.sq_distance(other.position) + rotDist ** 2

    @profiler
    def distance(self, other: "Transform2D") -> float:
        return math.sqrt(self.sq_distance(other))

    @profiler
    def copy(self):
        return Transform2D(self.position.copy(), self.rotation)