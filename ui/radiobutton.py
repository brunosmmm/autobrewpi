from ui.checkbox import CheckBox
from ui.instr import DrawInstruction

class RadioButton(CheckBox):
    def __init__(self, **kwargs):
        if 'group' in kwargs:
            self.group = kwargs.pop('group')
        else:
            self.group = None

        super(RadioButton, self).__init__(**kwargs)

    def _get_drawing_instructions(self):

        drawing_list = [
            DrawInstruction('circle',
                            x=self.x+self.w/2,
                            y=self.y+self.h/2,
                            radius=self.w/2,
                            fill=False,
                            color=True
            )
        ]

        if self.state == 'pressed':
            drawing_list.append(DrawInstruction('circle',
                                                x=self.x+self.w/2,
                                                y=self.y+self.h/2,
                                                radius=self.w/2-3,
                                                fill=True,
                                                color=True))
        return drawing_list
