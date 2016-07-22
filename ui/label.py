from ui.element import UIElement
from ui.instr import DrawInstruction, DrawInstructionGroup

class Label(UIElement):

    _LABEL_H_JUSTIFICATION =('right', 'left', 'center')

    def __init__(self, *args, **kwargs):
        self.text = kwargs.pop('text')
        self.font = kwargs.pop('font')
        if 'hjust' in kwargs:
            self.hjust = kwargs.pop('hjust')
        else:
            self.hjust = 'right'
        if 'vjust' in kwargs:
            self.vjust = kwargs.pop('vjust')
        else:
            self.vjust = 'top'
        super(Label, self).__init__(*args, **kwargs)

    def get_text(self):
        return self.text

    def set_text(self, text):
        self.text = text
        self._needs_redrawing()

    def _get_drawing_instructions(self):
        dwg = DrawInstructionGroup(self.draw_prio)
        dwg.add_instructions(
            DrawInstruction('text',
                            x=self.x,
                            y=self.y,
                            font_name=self.font,
                            msg=self.text,
                            hjust=self.hjust,
                            vjust=self.vjust,
                            color=True)
            )

        return [dwg]
