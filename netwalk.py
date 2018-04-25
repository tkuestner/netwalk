# import kivy
# kivy.require('1.10.0')

import cProfile
import itertools
import queue
import threading

from kivy.app import App
from kivy.animation import Animation
from kivy.clock import Clock, mainthread
from kivy.core.window import Window
from kivy.properties import BooleanProperty, DictProperty, NumericProperty, ObjectProperty, OptionProperty
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.widget import Widget

from builder import Builder, Difficulty, EntityType, LinkType, Options, Wall
from grid import Grid
from vector2d import Direction, Vector2d


tilesize = 40


class TileWidget(ButtonBehavior, Widget):
    """
    Basic widget that represents a square tile of the game board

    :ivar kivy.properties.NumericProperty angle: rotational angle of the widget, animated
    :ivar kivy.properties.BooleanProperty powered: true if tile is connected to the source
    :ivar kivy.properties.BooleanProperty locked: true if the user cannot rotate the tile
    :ivar kivy.properties.OptionProperty link: derived from :class:`builder.LinkType`.

    :ivar int orientation: Angle in steps of 90 degrees (i.e. 0, 90, 180 or 170 degrees)

    :Events:
        `on_change`: Emitted when the tile starts rotating.
    """

    angle = NumericProperty(0)
    powered = BooleanProperty(False)
    locked = BooleanProperty(False)
    link = OptionProperty('empty', options=LinkType.__members__.keys())

    def __init__(self, tile, **kwargs):
        self.angle = tile.orientation.angle
        self.link = tile.link.name
        self.size = tilesize, tilesize
        super(TileWidget, self).__init__(**kwargs)
        self.orientation = self.angle
        self._arms = LinkType[self.link].arms
        self.bind(on_touch_down=self.on_touch)
        self.register_event_type('on_change')

    def on_change(self, *args):
        pass

    def on_touch(self, tile, touch):
        # noinspection SpellCheckingInspection
        """Function called on mouse clicks

        :param TileWidget tile: :class:`Tile` Tile instance
        :param kivy.input.motionevent.MotionEvent touch: Motion event
        """
        del tile  # unused parameter
        if not self.collide_point(*touch.pos):
            return
        if touch.button == 'left':
            if self.locked:
                return
            if self.angle != self.orientation:
                Animation.cancel_all(self)
            self.orientation += 90
            animation = Animation(angle=self.orientation, duration=0.1)
            animation.start(self)
            self.dispatch('on_change')
            # animation.bind(on_complete=lambda a, w: self.dispatch('on_change'))
        elif touch.button == 'right':
            self.locked = not self.locked

    def has_arm(self, angle):
        """True if tile (in current orientation) has an arm (half-edge) at `angle`

        :param int angle: angle to check
        """
        corrected_angle = (angle - self.orientation) % 360
        index = corrected_angle // 90
        return self._arms[index]


class SourceWidget(TileWidget):
    """Widget representing the source tile"""
    pass


class DrainWidget(TileWidget):
    """Widget representing a drain tile"""
    pass


class WallWidget(Widget):
    """ Widget representing a wall

    :ivar kivy.properties.NumericProperty angle: rotational angle (0 or 90, i.e. vertical or horizontal)
    """
    angle = NumericProperty(0)

    def __init__(self, wall, **kwargs):
        self.pos = wall.position.x * tilesize, wall.position.y * tilesize
        self.size = tilesize, tilesize
        if wall.orientation == Wall.Orientation.horizontal:
            self.angle = 90
            self.y -= tilesize // 2
        else:
            self.x -= tilesize // 2
        super().__init__(**kwargs)


class NetGame(Widget):
    """Main widget

    :ivar kivy.properties.ObjectProperty main_window: reference to main widget (without background)
    :ivar kivy.properties.ObjectProperty grid: reference to the game board widget (`RelativeLayout`)
    :ivar kivy.properties.ObjectProperty timer: reference to the timer label
    :ivar kivy.properties.OptionProperty state: game state (possible states are waiting', 'running', 'paused' and
        'solved')
    :ivar kivy.properties.NumericProperty moves: number of moves played
    :ivar kivy.properties.NumericProperty expected_moves: the expected (close to minimal) number of moves required to
        solve the puzzle

    :ivar builder.Puzzle puzzle: the puzzle currently displayed
    :ivar int columns: number of columns of the game board
    :ivar int rows: number of rows of the game board
    :ivar grid.Grid board: the game board, a :class:`grid.Grid` of :class:`TileWidget` objects
    """
    main_window = ObjectProperty()
    grid = ObjectProperty()
    timer = ObjectProperty()
    state = OptionProperty('waiting', options=['waiting', 'running', 'paused', 'solved'])
    moves = NumericProperty(0)
    expected_moves = NumericProperty(10)

    def __init__(self, puzzle, **kwargs):
        """Create a new widget displaying the given puzzle. Adjusts window size."""
        super(NetGame, self).__init__(**kwargs)
        self.puzzle = puzzle
        self.columns = puzzle.grid.columns
        self.rows = puzzle.grid.rows
        self.grid.width = self.columns * tilesize
        self.grid.height = self.rows * tilesize
        self.expected_moves = self.puzzle.expected_moves
        self.board = None
        self._last_changed = None  # last changed tile
        self.ids['pause_button'].bind(on_press=self.on_pause)
        # Set window size to at least size of game dialog
        Window.size = (max(self.main_window.width, 300), max(self.main_window.height, 350))
        self._setup_board()
        self._setup_walls()
        self.check_power()

    def _setup_board(self):
        self.board = Grid(self.columns, self.rows)  # for storing widgets
        self.grid.clear_widgets()  # RelativeLayout
        for x, y in itertools.product(range(self.columns), range(self.rows)):
            if self.puzzle.grid[x, y].entity == EntityType.source:
                t = SourceWidget(self.puzzle.grid[x, y], pos=(x * tilesize, y * tilesize))
            elif self.puzzle.grid[x, y].entity == EntityType.drain:
                t = DrainWidget(self.puzzle.grid[x, y], pos=(x * tilesize, y * tilesize))
            else:
                t = TileWidget(self.puzzle.grid[x, y], pos=(x * tilesize, y * tilesize))
            t.bind(on_change=self.on_tile_change)
            self.board[x, y] = t
            self.grid.add_widget(t)

    def _setup_walls(self):
        for w in self.puzzle.walls:
            self.grid.add_widget(WallWidget(w))
            # Double the walls on the board's borders
            if w.position.x == 0 and w.orientation == Wall.Orientation.vertical:
                w2 = Wall(Vector2d(w.position.x + self.columns, w.position.y), w.orientation)
                # noinspection PyTypeChecker
                self.grid.add_widget(WallWidget(w2))
            if w.position.y == 0 and w.orientation == Wall.Orientation.horizontal:
                w2 = Wall(Vector2d(w.position.x, w.position.y + self.rows), w.orientation)
                # noinspection PyTypeChecker
                self.grid.add_widget(WallWidget(w2))

    def on_pause(self, instance):
        """Handle pressing the pause button"""
        del instance  # unused parameter
        self.state = 'paused'
        self.timer.stop()

    def proceed(self):
        """Unpause the game"""
        if self._last_changed is None:
            self.state = 'waiting'
        else:
            self.state = 'running'
            self.timer.start()

    def reset(self):
        """Reset the puzzle to its original state"""
        # Unlock all tiles and set their rotational angle back to the original state
        for x, y in itertools.product(range(self.columns), range(self.rows)):
            self.board[x, y].powered = False
            self.board[x, y].locked = False
            self.board[x, y].angle = self.puzzle.grid[x, y].orientation.angle
            self.board[x, y].orientation = self.puzzle.grid[x, y].orientation.angle
        self.check_power()
        self.moves = 0
        self.timer.stop()
        self.timer.reset()
        self._last_changed = None
        self.state = 'waiting'

    def on_tile_change(self, tile):
        """Slot called when a tile is rotated"""
        if self.state == 'waiting':
            self.timer.start()
            self.state = 'running'
        if self._last_changed is not tile:
            self._last_changed = tile
            self.moves += 1
        self.check_power()
        solved = self._check_solved()
        if solved:
            self.timer.stop()
            self.state = 'solved'

    def check_power(self):
        """Check which tile is connected to the power source"""
        power = Grid(self.columns, self.rows, False)
        work = {self.puzzle.source}
        while work:
            parent = work.pop()
            power[parent] = True
            for direction in Direction:
                proto_child = parent + direction.vector
                if not self.puzzle.wrap and not self.board.valid_index(proto_child):
                    continue
                child = Vector2d(proto_child.x % self.columns, proto_child.y % self.rows)
                # noinspection PyTypeChecker
                if (not power[child] and self._connected(parent, child, direction)
                        and not self._blocking_wall(parent, proto_child)):
                    work.add(child)
        for x, y in itertools.product(range(self.columns), range(self.rows)):
            self.board[x, y].powered = power[x, y]

    def _connected(self, parent, child, direction):
        """Check if both parent and child tile have arms in opposite directions"""
        parent_angle = direction.angle
        child_angle = (parent_angle + 180) % 360
        return self.board[parent].has_arm(parent_angle) and self.board[child].has_arm(child_angle)

    def _blocking_wall(self, parent, child):
        """Check if parent and child are separated by a wall"""
        orientation = Wall.Orientation.horizontal if parent.x == child.x else Wall.Orientation.vertical
        position = Vector2d(max(parent.x, child.x), max(parent.y, child.y))
        position = Vector2d(position.x % self.columns, position.y % self.rows)
        return Wall(position, orientation) in self.puzzle.walls

    def _check_solved(self):
        """Check if all tiles are connected to the power source"""
        return all(tile.powered for tile in self.board)

    def score(self) -> int:
        """Calculate the score"""
        if not self.state == 'solved':
            return 0
        weights = {
            LinkType.empty: 0,
            LinkType.dead_end: 4,
            LinkType.corner: 4,
            LinkType.straight: 2,
            LinkType.t_intersection: 4,
            LinkType.cross_intersection: 0
        }
        score = 0
        for x, y in itertools.product(range(self.columns), range(self.rows)):
            score += weights[self.puzzle.grid[x, y].link]
        score -= 2 * len(self.puzzle.walls)  # wall: -1 point for left and right square
        if not self.puzzle.wrap:  # implicit walls
            score -= self.puzzle.grid.columns + self.puzzle.grid.rows
        score *= self.puzzle.expected_moves / (self.puzzle.grid.columns * self.puzzle.grid.rows)
        score = score ** 2 / self.timer.seconds
        return round(score)


class Timer(Label):
    """ Label displaying the elapsed time like a stopwatch

    :ivar kivy.properties.BooleanProperty running: True if the clock is running
    """
    running = BooleanProperty(False)

    def __init__(self, **kwargs):
        super(Timer, self).__init__(**kwargs)
        self.text = "00:00"
        self.size = self.texture_size
        self._time = 0
        self._event = Clock.schedule_interval(self._update, 0.1)

    def _update(self, dt):
        if not self.running:
            return
        self._time += dt
        self._set_text()

    def start(self):
        """Start the timer (no reset)"""
        self.running = True

    def stop(self):
        """Stop the timer (no reset)"""
        self.running = False

    def reset(self):
        """Reset the timer to 0"""
        self._time = 0
        self._set_text()

    @property
    def seconds(self):
        """Seconds on the timer"""
        return self._time

    def _set_text(self):
        minutes = int(self._time // 60)
        seconds = int(self._time % 60)
        self.text = "{0:0=2d}:{1:0=2d}".format(minutes, seconds)


class OptionsDialog(Popup):
    """Dialog for choosing the game settings and starting a new game"""

    options = DictProperty()

    def __init__(self, config, **kwargs):
        super(OptionsDialog, self).__init__(**kwargs)
        size = config.getdefaultint('settings', 'size', '10')
        if 3 <= size <= 20:
            self.options['size'] = size
        self.ids['difficulty_spinner'].values = Difficulty.__members__.keys()
        difficulty = config.getdefault('settings', 'difficulty', 'medium')
        try:
            self.options['difficulty'] = Difficulty[difficulty].name
        except KeyError:
            pass
        wrap = config.getdefault('settings', 'wrap', 'False')
        if wrap.lower() in ('true', 'false'):
            self.options['wrap'] = True if wrap.lower() == 'true' else False
            
            
class PauseDialog(Popup):
    """Dialog displayed when the game is paused"""
    result = OptionProperty('continue', options=['new game', 'reset', 'continue'])


class ResultDialog(Popup):
    """Dialog displaying the game results and statistics"""
    def open(self, time, moves, score, *args, **kwargs):
        super(ResultDialog, self).open(*args, kwargs)
        self.ids['time'].text = time
        self.ids['moves'].text = moves
        self.ids['score'].text = score


class RootWidget(AnchorLayout):
    pass


class NetApp(App):
    """Main application class"""
    def __init__(self, **kwargs):
        super(NetApp, self).__init__(**kwargs)
        self.root_widget = None
        self.game = None
        self.options_dialog = None
        self.profiling = False
        self.profile = None
        self.result_queue = queue.Queue()

    def build(self):
        """Create widgets"""
        # self.icon = 'path/to/icon'
        self.options_dialog = OptionsDialog(self.config)
        self.options_dialog.bind(on_dismiss=self.on_options_dialog_dismiss)
        self.root_widget = RootWidget()
        return self.root_widget

    def build_config(self, config):
        """Set default values in config file"""
        o = Options()
        config.setdefaults('settings', {
            'size': o.columns,
            'difficulty': o.difficulty.name,
            'wrap': o.wrap
        })

    def on_start(self):
        """Called on start of application"""
        self.options_dialog.open()
        if self.profiling:
            self.profile = cProfile.Profile()
            self.profile.enable()

    def on_stop(self):
        """Called on end of application"""
        self.config.write()
        if self.profiling:
            self.profile.disable()
            self.profile.dump_stats('netwalk.profile')

    def on_game_state_changed(self, game, state):
        """Called :class:`NetGame` changes its state"""
        if state == 'paused':
            pause_dialog = PauseDialog()
            pause_dialog.bind(on_dismiss=self.on_pause_dialog_dismiss)
            pause_dialog.open()
        if state == 'solved':
            time = game.timer.text
            moves = str(game.moves) + "/" + str(game.expected_moves)
            score = str(game.score())
            result_dialog = ResultDialog()
            result_dialog.bind(on_dismiss=lambda dialog: self.options_dialog.open())
            result_dialog.open(time, moves, score)

    def on_options_dialog_dismiss(self, dialog):
        """Called on closing the options dialog. Starts a new game."""
        options = dialog.options
        self.config.setall('settings', options)
        if self.game:
            self.root_widget.remove_widget(self.game)
        options = Options(options.size, options.size, Difficulty[options.difficulty], options.wrap)
        threading.Thread(target=self.builder_thread, args=(options,)).start()
        return False  # confirm dismiss

    def builder_thread(self, options):
        builder = Builder(options)
        puzzle = builder.run()
        self.result_queue.put(puzzle)
        self.builder_finished()

    @mainthread
    def builder_finished(self):
        puzzle = self.result_queue.get_nowait()
        self.game = NetGame(puzzle)
        self.game.bind(state=self.on_game_state_changed)
        self.root_widget.add_widget(self.game)

    def on_pause_dialog_dismiss(self, dialog):
        """Called on closing the pause dialog"""
        if dialog.result == 'new game':
            self.options_dialog.open()
        elif dialog.result == 'reset':
            self.game.reset()
        elif dialog.result == 'continue':
            self.game.proceed()


if __name__ == '__main__':
    NetApp().run()
