from ui.element import UIElement
from ui.instr import DrawInstruction, DrawInstructionGroup
from PIL import Image as PImage

class Image(UIElement):
    def __init__(self, *args, **kwargs):
        if 'path' in kwargs:
            self._path = kwargs.pop('path')
        super(Image, self).__init__(*args, **kwargs)

        self._image = PImage.open(self._path)

    def _get_drawing_instructions(self):
        dwg = DrawInstructionGroup(self.draw_prio)
        dwg.add_instructions(
            DrawInstruction('bitmap',
                            x=self.x,
                            y=self.y,
                            data=self._image)
        )

        return [dwg]
