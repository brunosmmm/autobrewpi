
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
        self.x = kwargs.pop('x')
        self.y = kwargs.pop('y')
        super(UIElement, self).__init__(*args, **kwargs)

        self._parent = None

    def _needs_redrawing(self):
        if self._parent is not None:
            self._parent._needs_redrawing()

    def _draw_proxy(self):
        if self.visible:
            return self._get_drawing_instructions()
        else:
            return []

    def _get_drawing_instructions(self):
        return []