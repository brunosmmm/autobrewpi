from ui.screen import Screen
from ui.instr import DrawInstruction, DrawInstructionGroup

class Frame(Screen):
    def __init__(self, **kwargs):
        super(Frame, self).__init__(**kwargs)

        self.visible = False

    def show(self):
        self.visible = True
        self._needs_redrawing()

    def hide(self):
        self.visible = False
        self._needs_redrawing()

    def _get_drawing_instructions(self):

        #draw children!
        dwg = DrawInstructionGroup(self.draw_prio)

        #note: use relative positioning
        child_instr = super(Frame, self)._get_drawing_instructions()
        for child in child_instr:
            child.translate(self.x,
                            self.y)

        return child_instr

    def _needs_redrawing(self):
        if self._parent is not None:
            self._parent._needs_redrawing()
