from ui.element import UIElement
from ui.instr import DrawInstruction, DrawInstructionGroup

class Box(UIElement):
    def __init__(self, **kwargs):
        super(Box, self).__init__(**kwargs)

    def _get_drawing_instructions(self):

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

        return [dwg]
