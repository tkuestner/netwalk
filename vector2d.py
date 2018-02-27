import collections
import enum
import math


# noinspection PyUnresolvedReferences
class Vector2d(collections.namedtuple('Vector2d', ['x', 'y'])):
    """Two-dimensional vector (x, y)

    Derived from  `namedtuple('Vector2d', ['x', 'y'])`

    :ivar x: The first coordinate
    :ivar y: The second coordinate

    >>> Vector2d(4, 5).x
    4
    >>> Vector2d(4, 5)[1]
    5
    >>> -Vector2d(1, 1) + Vector2d(2, 3)
    Vector2d(x=1, y=2)
    """

    __slots__ = ()

    def __add__(self, other):
        """Add two vectors

        :param other: :class:`Vector2d` or sequence to be added
        :rtype: Vector2d
        """
        return Vector2d(self.x + other[0], self.y + other[1])

    def __sub__(self, other):
        """Subtract two vectors

        :param other: :class:`Vector2d` or sequence to be added
        :rtype: Vector2d
        """
        return Vector2d(self.x - other[0], self.y - other[1])

    def __neg__(self):
        """Vector of same length, opposite direction

        :rtype: Vector2d
        """
        return Vector2d(-self.x, -self.y)

    def length(self):
        """The Euclidean length of the vector"""
        return math.sqrt(self.x ** 2 + self.y ** 2)

    def normalized(self):
        """A new :class:`Vector2d` with the same direction, but length 1"""
        return Vector2d(self.x / self.length(), self.y / self.length())


_proxy_directions = [
    {'index': 0, 'angle': 0, 'vector': Vector2d(1, 0)},
    {'index': 1, 'angle': 90, 'vector': Vector2d(0, 1)},
    {'index': 2, 'angle': 180, 'vector': Vector2d(-1, 0)},
    {'index': 3, 'angle': 270, 'vector': Vector2d(0, -1)}
]

_angle_direction = {d['angle']: d for d in _proxy_directions}
_vector_direction = {d['vector']: d for d in _proxy_directions}


class Direction(enum.Enum):
    """Enumeration of the cardinal directions

    >>> Direction.UP.angle
    90
    >>> Direction.create(angle=180).vector
    Vector2d(x=-1, y=0)
    """
    right = _proxy_directions[0]  #: alias EAST
    up = _proxy_directions[1]  #: alias NORTH
    left = _proxy_directions[2]  #: alias WEST
    down = _proxy_directions[3]  #: alias SOUTH

    north = up
    south = down
    west = left
    east = right

    def __init__(self, values):
        self._index = values['index']
        self._angle = values['angle']
        self._vector = values['vector']

    @classmethod
    def create(cls, **kwargs):
        """Create a direction from keyword arguments 'angle' or 'vector'"""
        # NOTE Could also round to nearest cardinal direction
        try:
            return Direction(_angle_direction[kwargs['angle'] % 360])
        except KeyError:
            pass
        try:
            return Direction(_vector_direction[kwargs['vector']])
        except KeyError:
            raise ValueError("Cannot create direction from '{}'".format(kwargs))

    @property
    def index(self):
        """Property: the index of the direction"""
        return self._index

    @property
    def angle(self):
        """Property: the angle from the x-axis"""
        return self._angle

    @property
    def vector(self):
        """Property: the direction as a vector in an x/y coordinate systems"""
        return self._vector

    def rotate(self, n: int = 1, **kwargs):
        """Return direction rotated `n` times counter-clockwise"""
        if kwargs.get('clockwise', False):
            return Direction.create(angle=self.angle - 90 * n)
        else:
            return Direction.create(angle=self.angle + 90 * n)

    def __neg__(self):
        """Reverse direction"""
        return Direction.create(vector=-self.vector)


if __name__ == '__main__':
    import doctest
    doctest.testmod()
