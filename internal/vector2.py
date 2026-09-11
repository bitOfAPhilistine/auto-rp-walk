from internal.profiler import profiler

import math


class Vector2:
    @profiler
    def __init__(self, x: float | int, y: float | int = None):
        if y != None:
            self.x, self.y = x, y
        else:
            self.x, self.y = x, x

    @profiler
    def __eq__(self, other) -> bool:
        return self.x == other.x and self.y == other.y
    
    @profiler
    def __gt__(self, other) -> bool:
        if isinstance(other, Vector2):
            return self.x > other.x and self.y > other.y
        if isinstance(other, (int, float)):
            return self.magnitude() > other
    
    @profiler
    def __lt__(self, other) -> bool:
        if isinstance(other, Vector2):
            return self.x < other.x and self.y < other.y
        if isinstance(other, (int, float)):
            return self.magnitude() < other

    @profiler
    def __add__(self, other):
        if isinstance(other, Vector2):
            return Vector2(self.x + other.x, self.y + other.y)
        if isinstance(other, (int, float)):
            return Vector2(self.x + other, self.y + other)

    @profiler
    def __sub__(self, other):
        if isinstance(other, Vector2):
            return Vector2(self.x - other.x, self.y - other.y)
        if isinstance(other, (int, float)):
            return Vector2(self.x - other, self.y - other)

    @profiler
    def __mul__(self, other):
        if isinstance(other, Vector2):
            return Vector2(self.x * other.x, self.y * other.y)
        if isinstance(other, (int, float)):
            return Vector2(self.x * other, self.y * other)

    @profiler
    def __truediv__(self, other):
        if isinstance(other, Vector2):
            return Vector2(self.x / other.x, self.y / other.y)
        if isinstance(other, (int, float)):
            return Vector2(self.x / other, self.y / other)

    @profiler
    def __repr__(self) -> str:
        return f"Vector2({self.x}, {self.y})"
    
    @profiler
    def __iter__(self):
        yield self.x
        yield self.y

    @profiler
    def magnitude(self):
        return math.sqrt(self.sq_magnitude())

    @profiler
    def sq_magnitude(self):
        return self.x**2 + self.y**2

    @profiler
    def normalize(self):
        sq_mag = self.sq_magnitude()
        if sq_mag == 0.0:
            return Vector2(0, 0)
        return Vector2(self.x**2 / sq_mag, self.y**2 / sq_mag)

    @profiler
    def distance(self, other):
        return math.sqrt(self.sq_distance(other))

    @profiler
    def sq_distance(self, other):
        return (other.x - self.x) ** 2 + (other.y - self.y) ** 2

    @profiler
    def scale(self, factor):
        return Vector2(self.x * factor, self.y * factor)
    
    @profiler
    def copy(self):
        return Vector2(self.x, self.y)
    
    @profiler
    def tuple(self):
        return (self.x, self.y)