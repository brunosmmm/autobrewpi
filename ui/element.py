
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
        self.x = kwargs.pop('x')
        self.y = kwargs.pop('y')
        super(UIElement, self).__init__(*args, **kwargs)

    def _get_drawing_instructions(self):
        return []
