from ui.behaviors import ButtonBehavior
from ui.instr import DrawInstruction, DrawInstructionGroup
from ui.element import UIElement

class CheckBox(UIElement, ButtonBehavior):
    def __init__(self, **kwargs):
        super(CheckBox, self).__init__(**kwargs)

    def set_state(self, state):
        if self.state != state:
            super(CheckBox, self).set_state(state)
            self._needs_redrawing()

    def _get_drawing_instructions(self):

        #build drawing instructions
        dwg = DrawInstructionGroup(self.draw_prio)
        dwg.add_instructions(
            DrawInstruction('rect',
                            x1=self.x,
                            y1=self.y,
                            x2=self.x+self.w,
                            y2=self.y+self.h,
                            color=True,
                            fill=False)
        )

        if self.state == 'pressed':
            dwg.add_instructions(
                DrawInstruction('line',
                                x1=self.x,
                                y1=self.y,
                                x2=self.x+self.w,
                                y2=self.y+self.w,
                                color=True),
                DrawInstruction('line',
                                x1=self.x+self.w,
                                x2=self.x,
                                y1=self.y,
                                y2=self.y+self.h,
                                color=True)
                )

        return [dwg]
