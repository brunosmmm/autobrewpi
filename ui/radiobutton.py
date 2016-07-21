from ui.checkbox import CheckBox
from ui.instr import DrawInstruction, DrawInstructionGroup

class RadioButton(CheckBox):
    def __init__(self, **kwargs):
        if 'group' in kwargs:
            self.group = kwargs.pop('group')
        else:
            self.group = None

        super(RadioButton, self).__init__(**kwargs)

    def _get_drawing_instructions(self):
        dwg = DrawInstructionGroup(self.draw_prio)
        dwg.add_instructions(
            DrawInstruction('circle',
                            x=self.x+self.w/2,
                            y=self.y+self.h/2,
                            radius=self.w/2,
                            fill=False,
                            color=True
            )
        )

        if self.state == 'pressed':
            dwg.add_instructions(
                DrawInstruction('circle',
                                x=self.x+self.w/2,
                                y=self.y+self.h/2,
                                radius=self.w/2-3,
                                fill=True,
                                color=True)
                )
        return [dwg]
