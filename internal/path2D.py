from internal.profiler import profiler
from internal.vector2 import Vector2
from internal.transform2D import Transform2D
import math


class Edge:
    @profiler
    def __init__(self, point1: Transform2D, point2: Transform2D):
        self.point1 = point1
        self.point2 = point2

class Path2D(list):
    @profiler
    def __init__(self, points: list[Transform2D] = []):
        self.points = points

    # Allow using a float for the index, which will interpolate between points
    @profiler
    def __getitem__(self, index: float) -> Transform2D:
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

        return Transform2D(interpPosition, interpRotation)

    @profiler
    def find_closest_point(self, point: Transform2D) -> float:
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