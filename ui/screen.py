from ui.element import UIElement

class Screen(UIElement):
    def __init__(self, **kwargs):
        super(Screen, self).__init__(**kwargs)
        self._children = []

        #property set by ScreenBuffer
        self._screen_id = None

    def add_element(self, element):
        element._parent = self
        self._children.append(element)

    def remove_element(self, element):
        element._parent = None
        self._children.remove(element)

    def _needs_redrawing(self):
        self._parent.screen_needs_redrawing(self._screen_id)

    def _get_drawing_instructions(self):

        instr_list = []

        for child in self._children:
            instr_list.extend(child._draw_proxy())

        return instr_list