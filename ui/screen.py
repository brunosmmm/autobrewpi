from ui.element import UIElement

class Screen(UIElement):
    def __init__(self, **kwargs):
        super(Screen, self).__init__(**kwargs)
        self._children = []
        self.uids = {}

        #property set by ScreenBuffer
        self._screen_id = None

    def add_element(self, element):
        element._parent = self
        self._children.append(element)

        #this will cost some more references, but do it for now
        if element.uid is not None:
            self.uids[element.uid] = element

    def add_elements(self, args):
        for element in args(self):
            self.add_element(element)

        #for element in self._children:
        #    print element._parent

    def find_child(self, child_uid):
        if child_id is None:
            return None

        for child in self._children:
            if child.uid == child_uid:
                return child

        return None

    def remove_element(self, element):
        element._parent = None
        self._children.remove(element)

    def _needs_redrawing(self):
        if self._parent is not None:
            self._parent.screen_needs_redrawing(self._screen_id)

    def _get_drawing_instructions(self):

        group_list = []

        for child in self._children:
            group_list.extend(child._draw_proxy())

        return group_list

    def _input_event(self, evt):
        pass

    def _screen_added(self, **kwargs):
        pass

    def _screen_activated(self, **kwargs):
        pass

    def _screen_deactivated(self, **kwargs):
        pass

    def __getattr__(self, attr_name):

        if attr_name in self.uids:
            return self.uids[attr_name]

        return self.__getattribute__(attr_name)
