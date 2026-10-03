from math import *
import math
import numpy as np


class Point:
    x = 0
    y = 0

    def __init__(self, *coordinate):
        try:
            self.x = coordinate[0][0]
            self.y = coordinate[0][1]
        except (TypeError, IndexError, KeyError, AttributeError):
            self.x = coordinate[0]
            self.y = coordinate[1]

    def __str__(self):
        return 'Point(' + str(self.x) + ', ' + str(self.y) + ')'

    def to_int(self):
        return (int(self.x + 0.5), int(self.y + 0.5))

    def to_float(self):
        return (self.x, self.y)

    def __add__(self, other):
        return Point(self.x + other.x, self.y + other.y)

    def __sub__(self, other):
        return Point(self.x - other.x, self.y - other.y)

    def __mul__(self, other):
        return Point(self.x * other, self.y * other)

    def __truediv__(self, other):
        return Point(self.x / other, self.y / other)

    def __abs__(self):
        return Point(abs(self.x), abs(self.y))

    def __eq__(self, other):
        return self.x == other.x and self.y == other.y

    def __ne__(self, other):
        return self.x != other.x or self.y != other.y

    def __iter__(self):
        yield iter((self.x, self.y))

    def __getitem__(self, item):
        return (self.x, self.x)[item]

class Direction:
    __degrees = None
    __sin_cos = None
    __perpendicular = None
    def __init__(self, radians):
        self.radians = radians

    def get_degrees(self):
        if self.__degrees is None:
            self.__degrees = math.degrees(self.radians)
        return self.__degrees

    def get_radians(self):
        return self.radians

    def get_sin_cos(self):
        if self.__sin_cos is None:
            self.__sin_cos = math.sin(self.radians), math.cos(self.radians)
        return self.__sin_cos

    def __add__(self, other):
        if type(other) is Direction:
            return Direction((self.get_radians() + other.get_radians()) / 2)
        else:
            return Direction(self.get_radians() + other)

    def perpendicular(self):
        if self.__perpendicular is None:
            self.__perpendicular = (Direction((self.radians + math.pi / 2 + math.pi) % (math.pi * 2)),
                    Direction((self.radians + math.pi / 2) % (math.pi * 2)))
        return self.__perpendicular

    def __reversed__(self):
        return Direction((self.radians + math.pi) % (math.pi * 2))

    def __neg__(self):
        return Direction((self.radians + math.pi) % (math.pi * 2))

    def __invert__(self):
        return Direction((self.radians - math.pi) % (math.pi * 2))

class Vector:
    direction = 0
    dist = 0

    def __init__(self, *coordinate):
        '''угл в радианах и длина в попугаях'''
        try:
            self.direction = Direction(coordinate[0][0])
            self.dist = coordinate[0][1]
        except (TypeError, IndexError, KeyError, AttributeError):
            self.direction = coordinate[0]
            self.dist = coordinate[1]
    def __str__(self):
        return 'Vector('+str(self.direction)+ ')'
    def get_direction(self):
        return self.direction

    def __add__(self, other):
        if type(other) is Vector:
            r1, t1, r2, t2 = self.direction.get_radians(), self.dist, other.direction.get_radians(), other.dist
            c, s = cos(t2 - t1), sin(t2 - t1)
            return Vector(t1 + atan2(r2 * s, r1 + r2 * c), sqrt((r1 + r2 * c) ** 2 + (r2 * s) ** 2))
        else:
            return Vector()

    def __reversed__(self):
        return Vector((self.direction + math.pi) % (math.pi * 2))

    def __neg__(self):
        return Vector((self.direction + math.pi) % (math.pi * 2))

    def __invert(self):
        return Vector((self.direction - math.pi) % (math.pi * 2))
