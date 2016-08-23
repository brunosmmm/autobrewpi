from ui.element import UIElement, Coordinate
from ui.instr import DrawInstruction, DrawInstructionGroup
import re

_FONT_NAME_REGEX = re.compile(r'([0-9]+)x([0-9]+)')

class DisableLabelSizeMixin(object):
    def __init__(self, **kwargs):
        super(DisableLabelSizeMixin, self).__init__(**kwargs)
        self._w = None
        self._h = None

    @property
    def w(self):
        return self._w

    @w.setter
    def w(self, value):
        self._w = value

    @property
    def h(self):
        return self._h
    @h.setter
    def h(self, value):
        self._h = value

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

        #try to guess font size
        m = re.match(_FONT_NAME_REGEX, self.font)
        if m != None:
            self._font_w = int(m.group(1))
            self._font_h = int(m.group(2))
        else:
            self._font_w = None
            self._font_h = None

        if 'font_w' in kwargs:
            self._font_w = kwargs.pop('font_w')
        if 'font_h' in kwargs:
            self._font_h = kwargs.pop('font_h')

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

    #label anchors are calculated differently because the width/height are dynamic
    #depending on the size of the text

    @property
    def w(self):
        if self._font_w is None:
            return None

        return len(self.text)*self._font_w

    @w.setter
    def w(self, value):
        pass

    @property
    def h(self):
        if self._font_w is None:
            return None

        return self._font_h

    @h.setter
    def h(self, value):
        pass
