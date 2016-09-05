from ui.frame import Frame
from ui.element import Coordinate
from ui.instr import DrawInstructionGroup


class ViewPort(Frame):
    def __init__(self, **kwargs):
        self.virtual_w = kwargs.pop('virtual_w')
        self.virtual_h = kwargs.pop('virtual_h')
        super(ViewPort, self).__init__(**kwargs)

        self._origin = Coordinate(0, 0)

    def set_origin(self, coordinate):
        self._origin = coordinate
        self._needs_redrawing()

    def _get_drawing_instructions(self):

        child_instr = super(ViewPort, self)._get_drawing_instructions()

        child_instruction_list = []
        for group in child_instr:
            visible_child_list = DrawInstructionGroup(group._prio)
            for child in group._instrlist:
                visible = False
                if child.kwargs['x'] >= self._origin.x and\
                   child.kwargs['x'] <= self._origin.x+self.w:
                    distance = self._origin.x
                    child.translate(-distance, 0)
                    visible = True
                if child.kwargs['y'] >= self._origin.y and\
                   child.kwargs['y'] <= self._origin.y+self.h:
                    distance = self._origin.y
                    child.translate(0, -distance)
                    visible = True

                if visible:
                    visible_child_list.add_instruction(child)

            child_instruction_list.append(visible_child_list)
        return child_instruction_list
