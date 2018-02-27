class Grid:
    """ Container data type, two-dimensional grid (or matrix)

    Grid is subscriptable (with 2-dimensional indices, e.g., :class:`vector2d.Vector2d`) and iterable

    :ivar int columns: Number of columns, first coordinate in range [0, columns)
    :ivar int rows: Number of rows, second coordinate in range [0, rows)
    :param initial_value: Value (or object) used to initialize the grid's elements. No shallow or deep copy
     is performed.

    >>> g = Grid(2, 3, 4)
    >>> print(g[1, 1])
    4
    >>> g[0, 0] = 5
    >>> print(g[g.normalize((2, 3))])
    5
    >>> g = Grid(2, 2, set())
    >>> g[0, 0].add(8)
    >>> print(g[1, 1])
    {8}
    """

    def __init__(self, columns, rows, initial_value=None):
        if not isinstance(columns, int) or columns < 0:
            raise ValueError("columns must be non-negative integer")
        if not isinstance(rows, int) or rows < 0:
            raise ValueError("columns must be non-negative integer")
        self.columns = columns
        self.rows = rows
        self._length = columns * rows
        self._data = [initial_value for _ in range(columns * rows)]

    def valid_index(self, index):
        """True if index is inside :math:`[0, columns) \\times [0, rows)`, false otherwise

        :param index: 2-dimensional index. Subscriptable object, e.g. :class:`tuple` or :class:`vector2d.Vector2d`
        """
        return 0 <= index[0] < self.columns and 0 <= index[1] < self.rows

    def _index(self, coordinates):
        # NOTE Corresponds to itertools.product(range(columns), range(rows))
        return coordinates[0] * self.rows + coordinates[1]

    def __getitem__(self, coordinates):
        return self._data[self._index(coordinates)]

    def __setitem__(self, coordinates, value):
        self._data[self._index(coordinates)] = value

    def __len__(self):
        return self._length

    def __iter__(self):
        return self._data.__iter__()


if __name__ == '__main__':
    import doctest
    doctest.testmod()
