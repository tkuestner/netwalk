import builder
from builder import LinkType, Wall
from grid import Grid, GridContainer
from vector2d import Direction, Vector2d

from collections import deque
import enum
import itertools
import timeit
import random


class Edges:
    """Edges of an undirected square grid graph

    :ivar int columns: the number of columns of the square grid
    :ivar int rows: the number of rows of the square grid
    :ivar _edges: Internal dictionary to store a Edges.State for each edge

    .. automethod:: __getitem__
    .. automethod:: __setitem__
    """

    class State(enum.Enum):
        """State of an edge: unknown, present or absent"""
        unknown = 0
        present = 1
        absent = 2

    def __init__(self, columns, rows, edges=None):
        self.columns = columns
        self.rows = rows
        if edges:
            self._edges = edges
        else:
            self._edges = {}
            self._add_edges()

    def _add_edges(self):
        for x, y in itertools.product(range(self.columns), range(self.rows)):
            node = Vector2d(x, y)
            right_neighbor = Vector2d((x + 1) % self.columns, y)
            top_neighbor = Vector2d(x, (y + 1) % self.rows)
            self._edges[node, right_neighbor] = Edges.State.unknown
            self._edges[right_neighbor, node] = Edges.State.unknown
            self._edges[node, top_neighbor] = Edges.State.unknown
            self._edges[top_neighbor, node] = Edges.State.unknown

    def __getitem__(self, nodes):
        """ Query the state of the edge between nodes

        :param nodes: The edge, given by two nodes
        :type nodes: (Vector2d, Vector2d)
        :rtype: Edges.State
        """
        return self._edges[nodes]

    def __setitem__(self, nodes, value):
        """ Set the state of the edge between nodes

        :param nodes: The edge, given by two nodes
        :type nodes: (Vector2d, Vector2d)
        :param Edges.State value: Value to set
        """
        assert isinstance(value, Edges.State)
        # Set both edges, as this graph is undirected
        opposite_edge = (nodes[1], nodes[0])
        self._edges[nodes] = value
        self._edges[opposite_edge] = value

    def clone(self):
        return Edges(self.columns, self.rows, self._edges.copy())


def rotate_left(l, n):
    """Rotate a list n elements to the left"""
    n = n % len(l)
    return l[n:] + l[:n]


def rotate_right(l, n):
    """Rotate a list n elmenents to the right"""
    n = n % len(l)
    return l[-n:] + l[:-n]


base_connectors = {
    LinkType.empty: [False, False, False, False],
    LinkType.dead_end: [True, False, False, False],
    LinkType.corner: [True, True, False, False],
    LinkType.straight: [True, False, True, False],
    LinkType.t_intersection: [True, True, True, False],
    LinkType.cross_intersection: [True, True, True, True]
}


tile_connectors = {
    link_type: {d: rotate_right(base_connectors[link_type], d.index) for d in Direction} for link_type in LinkType
}


class Solver:
    """Main class. Netwalk puzzle solver.

    Initialize with :class:`builder.Puzzle` and call :func:`run()`

    The solver basically implements a back-tracking algorithm. Whenever forward inference (implemented in method
    _forward_inference) gets stuck, a random tile is chosen. Separate states (class Solver.State) a generated from the
    possibilities left for this tile and pushed into a queue. The state at the front of the queue is retrieved for
    continuing the algorithm.
    """

    class State:
        """State of the game board, including tiles and edges."""
        def __init__(self, tiles, edges):
            self.tiles = tiles
            self.edges = edges

        def clone(self):
            """Clone (i.e. deep-copy) the state."""
            new_grid_container = GridContainer(self.tiles.grid)
            for node in self.tiles.grid:
                new_grid_container[node] = Solver.Tile(self.tiles[node].link,
                                                       self.tiles[node].possible_orientations.copy())
            new_edges = self.edges.clone()
            return Solver.State(new_grid_container, new_edges)

    class WorkItem:
        """A state and a work list of tiles combined, to be stored in the queue."""
        def __init__(self, state, work):
            self.state = state
            self.work = work

    class Tile:
        """A game tile, given by its link type. Stores a list of possible orientations left for this tile."""
        def __init__(self, link, possible_orientations=None):
            self.link = link
            if possible_orientations:
                self.possible_orientations = possible_orientations
            else:
                # noinspection PyTypeChecker
                self.possible_orientations = {
                    LinkType.empty: [Direction.right],
                    LinkType.dead_end: list(Direction),
                    LinkType.corner: list(Direction),
                    LinkType.straight: [Direction.right, Direction.up],
                    LinkType.t_intersection: list(Direction),
                    LinkType.cross_intersection: [Direction.right]
                }[link]

    def __init__(self, puzzle):
        self.columns = puzzle.grid.columns
        self.rows = puzzle.grid.rows
        self.source = puzzle.source
        self.grid = Grid(puzzle.grid.columns, puzzle.grid.rows)
        self.tiles = GridContainer(self.grid)
        for node in self.grid:
            self.tiles[node] = Solver.Tile(puzzle.grid[node].link)
        self.edges = Edges(self.columns, self.rows)
        if not puzzle.wrap:
            self._handle_boundary()
        self._handle_walls(puzzle.walls)
        self._handle_adjacent_drains()
        self.solutions = []

    def _handle_boundary(self):
        """Initialize edges, depending on the 'wrapping' option of the game."""
        for x in range(self.columns):
            self.edges[Vector2d(x, 0), Vector2d(x, self.rows - 1)] = Edges.State.absent
        for y in range(self.rows):
            self.edges[Vector2d(0, y), Vector2d(self.columns - 1, y)] = Edges.State.absent

    def _handle_walls(self, walls):
        """Remove edges where there are walls."""
        for w in walls:
            tile1 = w.position
            tile2 = None
            if w.orientation == Wall.Orientation.horizontal:
                tile2 = w.position - Vector2d(0, 1)
            if w.orientation == Wall.Orientation.vertical:
                tile2 = w.position - Vector2d(1, 0)
            tile1 = self.grid.normalize(tile1)
            tile2 = self.grid.normalize(tile2)
            self.edges[tile1, tile2] = Edges.State.absent

    def _handle_simple_tiles(self, state):
        """For simple tiles like cross intersections there is only one possible orientation."""
        for node in self.grid:
            if self.tiles[node].link in (LinkType.empty, LinkType.cross_intersection):
                self._inspect_tile(node, state)

    def _handle_adjacent_drains(self):
        for node in self.grid:
            if self.tiles[node].link == LinkType.dead_end:
                for d in [Direction.right, Direction.up]:
                    neighbor = self.grid.normalize(node + d.vector)
                    if self.tiles[neighbor] == LinkType.dead_end:
                        self.edges[node, neighbor] = Edges.State.absent

    def run(self):
        """Run the solver. This might take some time."""
        all_tiles = deque(n for n in self.grid)
        initial_state = Solver.State(self.tiles, self.edges)
        self._handle_simple_tiles(initial_state)
        work_stack = [Solver.WorkItem(initial_state, all_tiles)]
        while work_stack:
            item = work_stack.pop()
            state = item.state
            work = item.work
            investigate = self._forward_inference(state, work)
            if not investigate:
                continue  # Pop next state from stack
            # Choose tile with least amount of possible orientations left
            minimum = None
            min_pos = Vector2d(0, 0)
            for node in self.grid:
                orientations = len(state.tiles[node].possible_orientations)
                if orientations >= 2 and (minimum is None or orientations < minimum):
                    minimum = orientations
                    min_pos = node
            assert minimum is not None
            for o in state.tiles[min_pos].possible_orientations:
                neighbors = deque(self.grid.neighbors(min_pos))
                child_state = state.clone()
                child_state.tiles[min_pos].possible_orientations = [o]
                self._inspect_tile(min_pos, child_state)  # apply this orientation to edges
                work_stack.append(Solver.WorkItem(child_state, neighbors))
        print("Found {} solution(s)".format(len(self.solutions)))

    def _forward_inference(self, state, work):
        """Forward inference part of the back-tracking algorithm.

        Given a state and a list of tiles of intereset (work), try to reduce the number of possible orientations of
        tiles.
        """
        while work:
            pos = work.popleft()
            tile = state.tiles[pos]
            before = len(tile.possible_orientations)
            if before > 1:
                self._inspect_tile(pos, state)
            after = len(tile.possible_orientations)
            assert after <= before
            if after == before:
                continue
            elif 0 < after < before:
                for neighbor in self.grid.neighbors(pos):
                    if neighbor not in work:
                        work.append(neighbor)
            else:  # after <= 0
                return False

        partial_solution = all(len(state.tiles[node].possible_orientations) == 1 for node in self.grid)

        if not partial_solution:
            return True  # Store state and investigate children

        solution = self._check_power(state)
        if solution:
            self.solutions.append(state)

        return False  # Do not investigate further

    def _inspect_tile(self, node, state):
        """Inspect a single tile/node and try to reduce the number of possible orientations left by trying one after
        another.
        """
        tile = state.tiles[node]

        if len(tile.possible_orientations) <= 0:
            return len(tile.possible_orientations)

        tile.possible_orientations = [o for o in tile.possible_orientations if self._valid_orientation(node, o, state)]

        # noinspection PyTypeChecker
        for i, d in enumerate(Direction):
            collected_edges = []
            for o in tile.possible_orientations:
                connectors = tile_connectors[tile.link][o]
                collected_edges.append(connectors[i])
            # Reduce: check all edges are the same, either all True or all False
            if collected_edges and collected_edges.count(collected_edges[0]) == len(collected_edges):
                edge_state = collected_edges[0]
            else:
                continue
            child = node + d.vector
            child = Vector2d(child.x % self.columns, child.y % self.rows)
            # edge_state is either True or False
            if state.edges[node, child] is not Edges.State.unknown:
                assert ((edge_state is True and state.edges[node, child] is Edges.State.present) or
                        (edge_state is False and state.edges[node, child] is Edges.State.absent))
            state.edges[node, child] = Edges.State.present if edge_state is True else Edges.State.absent

    def _valid_orientation(self, node, orientation, state):
        """Check if for a given node/tile, the given orientation is possible, i.e. compatible with the surrounding
        tiles.
        """
        connectors = tile_connectors[state.tiles[node].link][orientation]
        for d in Direction:
            child = node + d.vector
            child = Vector2d(child.x % self.columns, child.y % self.rows)
            if state.edges[node, child] is Edges.State.unknown:
                continue
            elif ((connectors[d.index] is True and state.edges[node, child] is Edges.State.absent) or
                  (connectors[d.index] is False and state.edges[node, child] is Edges.State.present)):
                return False
        return True

    def _check_power(self, state):
        """Check if every tile on the grid has power."""
        power = GridContainer(self.grid, False)
        work = {self.source}
        while work:
            node = work.pop()
            power[node] = True
            for neighbor in self.grid.neighbors(node):
                if state.edges[node, neighbor] is Edges.State.present and not power[neighbor]:
                    work.add(neighbor)
        return all(power[node] for node in self.grid)


def run_test():
    example = False
    if example:
        puzzle = builder.Builder.example()
    else:
        random.seed(0)
        options = builder.Options(20, 20)
        b = builder.Builder(options)
        puzzle = b.run()
    solver = Solver(puzzle)
    start = timeit.default_timer()
    solver.run()
    stop = timeit.default_timer()
    print('Time: ', stop - start)


if __name__ == '__main__':
    run_test()
