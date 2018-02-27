import collections
import enum
import itertools
import random

from grid import Grid
from utilities import clamp, weighted_choice
from vector2d import Direction, Vector2d


# noinspection PyArgumentList
Difficulty = enum.Enum('Difficulty', ['easy', 'medium', 'hard'])  #: Game difficulty: `easy`, `medium` or `hard`


class Options:
    """Game options

    :ivar int columns: Number of tiles along the width of the game board
    :ivar int rows: Number of tiles along the height of the game board
    :ivar Difficulty difficulty: Easy, medium or hard. Changes frequency of different tile types.
    :ivar bool wrap: If true, the game board is wrapped (like playing on a torus)
    """
    def __init__(self, columns=10, rows=10, difficulty=Difficulty.medium, wrap=False):
        self.columns = columns
        self.rows = rows
        self.difficulty = difficulty
        self.wrap = wrap


@enum.unique
class LinkType(enum.Enum):
    """The number and arrangement of edges in a tile"""
    empty = 0  #: empty, no  edges
    dead_end = 1  #: dead end, one edge
    corner = 2  #: corner, two edges
    straight = 3  #: straight, two opposite edges
    t_intersection = 4  #: t-intersection, three edges
    cross_intersection = 5  #: cross-intersection, four edges

    @property
    def arms(self):
        # Cf. images/*.png
        return {
            self.empty: [False, False, False, False],
            self.dead_end: [True, False, False, False],
            self.corner: [True, True, False, False],
            self.straight: [True, False, True, False],
            self.t_intersection: [True, True, True, False],
            self.cross_intersection: [True, True, True, True]
        }[self]


# noinspection PyArgumentList
EntityType = enum.Enum('EntityType', 'link source drain')  #: Tile type: `link`, `source` or `drain`


class Tile:
    """A square on the game board

    :ivar LinkType link: The number and arrangement of edges in the tile
    :ivar vector2d.Direction orientation: The orientation of the tile (where right is the original position)
    :ivar EntityType entity: Whether it's a simple link, a source or a drain
    """
    def __init__(self, link, orientation, entity=None):
        self.link = link
        self.orientation = orientation
        self.entity = entity if entity else EntityType.drain if self.link == LinkType.dead_end else EntityType.link


class Wall(collections.namedtuple('Wall', ['position', 'orientation'])):
    """Class representing a wall

    Derived from `namedtuple('Wall', ['position', 'direction'])`

    :ivar Vector2d position: The wall's position. As walls are associated with the tile above or to the right of them,
        the position is actually this tiles coordinates.
    :ivar Orientation orientation: The wall's orientation (i.e. horizontal or vertical)
    """
    __slots__ = ()

    # noinspection PyArgumentList
    Orientation = enum.Enum('Orientation', ['horizontal', 'vertical'])  #: Wall orientation: `horizontal` or `vertical`


class Puzzle:
    """Class representing a puzzle, i.e. a game board with tiles, walls, a source, multiple drains, etc.

    :ivar grid.Grid grid: A grid of :class:`Tile` objects
    :ivar list walls: A list of :class:`Wall` objects
    :ivar vector2d.Vector2d source: The coordinates of the source
    :ivar int expected_moves: The number of moves required to solve the puzzle
    :ivar bool wrap: True if wrapping borders are enabled
    """
    def __init__(self, grid, walls, source, expected_moves, wrap):
        self.grid = grid
        self.walls = walls
        self.source = source
        self.expected_moves = expected_moves
        self.wrap = wrap


class Builder:
    """Class for creating randomized puzzles"""

    # Difficulty settings, weight for each type of tile
    difficulties = {
        Difficulty.easy: {
            LinkType.cross_intersection: 1,
            LinkType.t_intersection: 1,
            LinkType.corner: 4,
            LinkType.straight: 3,
            LinkType.dead_end: 1,
            LinkType.empty: 1
        },
        Difficulty.medium: {
            LinkType.cross_intersection: 0,
            LinkType.t_intersection: 1,
            LinkType.corner: 5,
            LinkType.straight: 2,
            LinkType.dead_end: 1,
            LinkType.empty: 1
        },
        Difficulty.hard: {
            LinkType.cross_intersection: 0,
            LinkType.t_intersection: 2,
            LinkType.corner: 5,
            LinkType.straight: 0,
            LinkType.dead_end: 1,
            LinkType.empty: 1
        }
    }

    class Edges:
        """List (of length four) representing the possible edges of a node. Item true if edge is present."""
        def __init__(self):
            self._edges = [False, False, False, False]

        def __getitem__(self, direction):
            return self._edges[direction.index]

        def __setitem__(self, direction, value):
            self._edges[direction.index] = value

        @property
        def all(self):
            return self._edges

    class Node:
        """Node in the tree. Holds edges. Kind of proto-Tile."""
        def __init__(self):
            self.edges = Builder.Edges()

        def to_tile(self):
            return {
                (True, True, True, True): Tile(LinkType.cross_intersection, Direction.right),
                (True, True, True, False): Tile(LinkType.t_intersection, Direction.right),
                (False, True, True, True): Tile(LinkType.t_intersection, Direction.up),
                (True, False, True, True): Tile(LinkType.t_intersection, Direction.left),
                (True, True, False, True): Tile(LinkType.t_intersection, Direction.down),
                (True, True, False, False): Tile(LinkType.corner, Direction.right),
                (False, True, True, False): Tile(LinkType.corner, Direction.up),
                (False, False, True, True): Tile(LinkType.corner, Direction.left),
                (True, False, False, True): Tile(LinkType.corner, Direction.down),
                (True, False, True, False): Tile(LinkType.straight, Direction.right),
                (False, True, False, True): Tile(LinkType.straight, Direction.up),
                (True, False, False, False): Tile(LinkType.dead_end, Direction.right),
                (False, True, False, False): Tile(LinkType.dead_end, Direction.up),
                (False, False, True, False): Tile(LinkType.dead_end, Direction.left),
                (False, False, False, True): Tile(LinkType.dead_end, Direction.down),
                (False, False, False, False): Tile(LinkType.empty, Direction.right)
            }[tuple(self.edges.all)]

    def __init__(self, options):
        """Set up the builder with some options.

        Call run to create a puzzle based on the given options.

        :param Options options: Options
        """
        self.columns = options.columns
        self.rows = options.rows
        self.difficulty = options.difficulty
        self.wrap = options.wrap
        self._source = None
        self._nodes = None

    def run(self):
        """Execute the builder

        :return: The created puzzle
        :rtype: Puzzle
        """
        self._source = Vector2d(self.columns // 2, self.rows // 2)
        grid = self._create_tree()
        walls = self._create_walls()
        rotated_tiles = self._rotate(grid)
        return Puzzle(grid, walls, self._source, rotated_tiles, self.wrap)

    @classmethod
    def example(cls):
        """A simple example puzzle"""
        grid = Grid(columns=5, rows=5)
        grid[0, 2] = Tile(LinkType.dead_end, Direction.down)
        grid[1, 2] = Tile(LinkType.t_intersection, Direction.right)
        grid[2, 2] = Tile(LinkType.corner, Direction.left)
        grid[0, 1] = Tile(LinkType.dead_end, Direction.down)
        grid[1, 1] = Tile(LinkType.t_intersection, Direction.down)
        grid[1, 1].entity = EntityType.source
        grid[2, 1] = Tile(LinkType.straight, Direction.right)
        grid[0, 0] = Tile(LinkType.dead_end, Direction.down)
        grid[1, 0] = Tile(LinkType.corner, Direction.up)
        grid[2, 0] = Tile(LinkType.dead_end, Direction.right)
        walls = {Wall(Vector2d(0, 2), Wall.Orientation.horizontal),
                 Wall(Vector2d(2, 1), Wall.Orientation.vertical)}
        return Puzzle(grid, walls, source=Vector2d(1, 1), expected_moves=7, wrap=False)

    def _create_tree(self):
        """Create the underlying tree.

        The algorithm starts with a source in the center and chooses an already visited tile at random to extend the
        tree to a random unvisited tile.
        """
        self._nodes = Grid(self.columns, self.rows)
        nodes = self._nodes  # alias
        for x, y in itertools.product(range(self.columns), range(self.rows)):
            nodes[x, y] = Builder.Node()
        visited = Grid(self.columns, self.rows, False)
        visited[self._source] = True
        boundary = {self._source}
        while True:
            new_boundary = set()
            moves = []  # [(parent, child, direction), ...]
            for parent in boundary:
                for direction in Direction:
                    child = parent + direction.vector
                    if self.wrap:
                        child = Vector2d(child.x % self.columns, child.y % self.rows)
                    if 0 <= child.x < self.columns and 0 <= child.y < self.rows and not visited[child]:
                        moves.append((parent, child, direction))
                        new_boundary.add(parent)
            if not moves:
                break
            weights = []
            for p, _, d in moves:
                nodes[p].edges[d] = True
                link = nodes[p].to_tile().link
                nodes[p].edges[d] = False
                weights.append(self.difficulties[self.difficulty][link])
            parent, child, direction = weighted_choice(moves, weights)
            new_boundary.add(child)
            visited[child] = True
            nodes[parent].edges[direction] = True
            nodes[child].edges[-direction] = True
            boundary = new_boundary

        # Transform nodes/edges into tiles with link type and orientation
        tiles = Grid(self.columns, self.rows)
        for x, y in itertools.product(range(self.columns), range(self.rows)):
            tiles[x, y] = nodes[x, y].to_tile()
        tiles[self._source].entity = EntityType.source
        return tiles

    def _create_walls(self, percent=0.06, rsd=0.4):
        """Randomly place some walls

        The actual number of walls is drawn from a normal distribution.

        :param float percent: Mean percent of walls to be created
        :param float rsd: Relative standard deviation
        """
        walls = set()  # collect all possible walls
        for x, y in itertools.product(range(self.columns), range(self.rows)):
            if (self.wrap or y != 0) and not self._nodes[x, y].edges[Direction.down]:
                walls.add(Wall(Vector2d(x, y), Wall.Orientation.horizontal))
            if (self.wrap or x != 0) and not self._nodes[x, y].edges[Direction.left]:
                walls.add(Wall(Vector2d(x, y), Wall.Orientation.vertical))
        mean = len(walls) * percent
        count = clamp(int(random.gauss(mean, rsd * mean)), 0, len(walls))
        walls = random.sample(walls, count)
        return walls

    def _rotate(self, grid, percent=0.8, rsd=0.1):
        """Rotate a random selection of tiles

        The actual number of rotated tile is drawn from a normal distribution.

        :param grid.Grid grid: Grid of :class:`Tile` objects
        :param float percent: Mean percent of tiles to be rotated
        :param float rsd: Relative standard deviation
        """
        rotatable = set()  # collect all rotatable tiles
        for x, y in itertools.product(range(self.columns), range(self.rows)):
            if grid[x, y].link not in (LinkType.cross_intersection, LinkType.empty):
                rotatable.add(grid[x, y])
        mean = len(rotatable) * percent
        count = clamp(int(random.gauss(mean, rsd * mean)), 1, len(rotatable))
        for tile in random.sample(rotatable, count):
            if tile.link == LinkType.straight:
                tile.orientation = tile.orientation.rotate()
            else:
                tile.orientation = tile.orientation.rotate(random.choice(range(1, 4)))
        return count
