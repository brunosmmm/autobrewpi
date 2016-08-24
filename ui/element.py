from ui.instr import DrawInstructionGroup
from collections import Mapping

class ElementArgumentError(Exception):
    pass

class Coordinate(Mapping):
    def __init__(self, x, y):
        super(Coordinate, self).__init__()
        self.x = x
        self.y = y

    def __iter__(self):
        yield 'x'
        yield 'y'

    def __len__(self):
        return 2

    def __getitem__(self, item):
        return self.__getattribute__(item)

    def __add__(self, other):
        if isinstance(other, Coordinate):
            return Coordinate(self.x + other.x, self.y + other.y)
        elif isinstance(other, tuple) or isinstance(other, list):
            return Coordinate(self.x + other[0], self.y + other[1])
        elif isinstance(other, dict):
            return Coordinate(self.x + other['x'], self.y + other['y'])

    def __radd__(self, other):
        return self + other

class UIElement(object):
    def __init__(self, *args, **kwargs):
        if 'w' in kwargs:
            self.w = kwargs.pop('w')
        else:
            self.w = None
        if 'h' in kwargs:
            self.h = kwargs.pop('h')
        else:
            self.h = None
        if 'visible' in kwargs:
            self.visible = kwargs.pop('visible')
        else:
            self.visible = True
        if 'draw_prio' in kwargs:
            self.draw_prio = kwargs.pop('draw_prio')
        else:
            self.draw_prio = 0
        if 'id' in kwargs:
            self.uid = kwargs.pop('id')
        else:
            self.uid = None
        self.x = kwargs.pop('x')
        self.y = kwargs.pop('y')

        #super is object, so check for stray kwargs
        if len(kwargs) > 0:
            raise ElementArgumentError('unknown arguments: {}'.format(','.join(kwargs.keys())))
        super(UIElement, self).__init__(*args, **kwargs)

        self._parent = None

    def _needs_redrawing(self):
        if self._parent is not None:
            self._parent._needs_redrawing()

    def _draw_proxy(self):
        if self.visible:
            return self._get_drawing_instructions()
        else:
            return [DrawInstructionGroup()]

    def _get_drawing_instructions(self):
        return [DrawInstructionGroup()]

    def event(self, event):
        pass

    def log_info(self, msg):
        if self._parent is not None:
            self._parent.log_info(msg)

    def log_warn(self, msg):
        if self._parent is not None:
            self._parent.log_warn(msg)

    def log_err(self, msg):
        if self._parent is not None:
            self._parent.log_err(msg)

    @property
    def west(self):
        return Coordinate(self.x, self.y + self.h/2)

    @property
    def east(self):
        return Coordinate(self.x + self.w, self.y + self.h/2)

    @property
    def north(self):
        return Coordinate(self.x + self.w/2, self.y)

    @property
    def south(self):
        return Coordinate(self.x + self.w/2, self.y + self.h)

    @property
    def northwest(self):
        return Coordinate(self.x, self.y)

    @property
    def northeast(self):
        return Coordinate(self.x + self.w, self.y)

    @property
    def southeast(self):
        return Coordinate(self.x + self.w, self.y + self.h)

    @property
    def southwest(self):
        return Coordinate(self.x, self.y + self.h)
