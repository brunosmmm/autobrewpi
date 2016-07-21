from ui.element import UIElement
from ui.behaviors import ButtonBehavior
from ui.label import Label
from ui.instr import DrawInstruction, DrawInstructionGroup

class Button(Label, ButtonBehavior):
    def __init__(self, **kwargs):
        super(Button, self).__init__(**kwargs)

    def set_state(self, state):
        if self.state != state:
            super(Button, self).set_state(state)
            self._needs_redrawing()

    def _get_drawing_instructions(self):

        dwg = DrawInstructionGroup(self.draw_prio)
        dwg.add_instructions(
            DrawInstruction('rect',
                            x1=self.x,
                            y1=self.y,
                            x2=self.x+self.w,
                            y2=self.y+self.h,
                            color=True,
                            fill=(self.state == 'pressed')),
            DrawInstruction('text',
                            x=self.x+self.w/2+1,
                            y=self.y+self.h/2+1,
                            font_name=self.font,
                            msg=self.text,
                            hjust='center',
                            vjust='center',
                            color=(self.state == 'normal'))
        )

        return [dwg]
