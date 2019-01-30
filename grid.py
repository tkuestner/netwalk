from vector2d import Direction, Vector2d

import itertools


class Grid:
    # Replacement for grid, coordinate system only

    def __init__(self, columns, rows, periodic=True):
        if not isinstance(columns, int) or columns < 0:
            raise ValueError("columns must be non-negative integer")
        if not isinstance(rows, int) or rows < 0:
            raise ValueError("columns must be non-negative integer")
        self.columns = columns
        self.rows = rows
        self.periodic = periodic

    def valid(self, coordinates):  # maybe call param 'node'
        if self.periodic:
            return True
        return 0 <= coordinates[0] < self.columns and 0 <= coordinates[1] < self.rows

    def normalize(self, coordinates):
        return Vector2d(coordinates[0] % self.columns, coordinates[1] % self.rows)

    def neighbors(self, coordinates):
        for direction in Direction:
            neighbor = Vector2d(*coordinates) + direction.vector
            if self.periodic:
                # neighbor = Vector2d(neighbor[0] % self.columns, neighbor[1] % self.rows)
                yield self.normalize(neighbor)
            elif self.valid(neighbor):
                yield neighbor

    def __iter__(self):
        for x, y in itertools.product(range(self.columns), range(self.rows)):
            yield Vector2d(x, y)


class GridContainer:
    # Grid with objects at nodes

    def __init__(self, grid, initial_value=None):
        self.grid = grid
        self.columns = self.grid.columns
        self.rows = self.grid.rows
        self.periodic = self.grid.periodic
        # self._length = columns * rows
        self._data = [initial_value for _ in range(self.columns * self.rows)]

    # NOTE Corresponds to itertools.product(range(columns), range(rows))
    def _index(self, coordinates):
        if self.grid.valid(coordinates):
            return coordinates[0] * self.rows + coordinates[1]
        elif self.periodic:
            coordinates = self.grid.normalize(coordinates)
            return coordinates[0] * self.rows + coordinates[1]
        else:
            raise IndexError("Cannot access {} in grid".format(coordinates))

    def __getitem__(self, coordinates):
        return self._data[self._index(coordinates)]

    def __setitem__(self, coordinates, value):
        self._data[self._index(coordinates)] = value

    # Iterator for pairs of (coordinates, object)
    def __iter__(self):
        for node in self.grid:
            yield (node, self[node])

    # Iterator for objects (without coordinates)
    def items(self):
        for node in self.grid:
            yield self[node]
