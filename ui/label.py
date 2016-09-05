from ui.element import UIElement
from ui.instr import DrawInstruction, DrawInstructionGroup
import re

_FONT_NAME_REGEX = re.compile(r'([0-9]+)x([0-9]+)')


def ValueCaptionError(Exception):
    pass


def _composite_label_text(label, value, max_len):
    label_fill = max_len - len(value)

    if label_fill - len(label) < 0:
        raise IOError('text is too long')

    ret = '{label: <{fill_len}}'.format(label=label, fill_len=label_fill)+value
    return ret


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

    _LABEL_H_JUSTIFICATION = ('right', 'left', 'center')

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
        if 'invert' in kwargs:
            self._invert = kwargs.pop('invert')
        else:
            self._invert = False

        # try to guess font size
        m = re.match(_FONT_NAME_REGEX, self.font)
        if m is not None:
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

    @staticmethod
    def guess_font_size(font_name):
        m = re.match(_FONT_NAME_REGEX, font_name)
        if m is not None:
            return {'w': int(m.group(1)),
                    'h': int(m.group(2))}

        return None

    def get_text(self):
        return self.text

    def set_text(self, text):
        self.text = text
        self._needs_redrawing()

    def set_inverted(self):
        self._invert = True
        self._needs_redrawing()

    def set_normal(self):
        self._invert = False
        self._needs_redrawing()

    def _get_drawing_instructions(self):
        dwg = DrawInstructionGroup(self.draw_prio)
        if self._invert:
            dwg.add_instructions(
                DrawInstruction('rect',
                                x1=self.x,
                                x2=self.x+self.w,
                                y1=self.y,
                                y2=self.y+self.h,
                                color=True,
                                fill=True)
            )
        dwg.add_instructions(
            DrawInstruction('text',
                            x=self.x,
                            y=self.y,
                            font_name=self.font,
                            msg=self.text,
                            hjust=self.hjust,
                            vjust=self.vjust,
                            color=(not self._invert))
            )

        return [dwg]

    # label anchors are calculated differently
    # because the width/height are dynamic
    # depending on the size of the text

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

    @property
    def font_w(self):
        return self._font_w

    @font_w.setter
    def font_w(self, value):
        pass

    @property
    def font_h(self):
        return self._font_h

    @font_h.setter
    def font_h(self, value):
        pass


class ValueCaption(Label):
    def __init__(self, **kwargs):
        if 'maximum_length' in kwargs:
            self._max_len = kwargs.pop('maximum_length')
            self._max_w = None
        elif 'maximum_width' in kwargs:
            self._max_w = kwargs.pop('maximum_width')
            self._max_len = None
        else:
            raise KeyError('maximum_length OR maximum_width must be present')
        if 'value' in kwargs:
            self._value = kwargs.pop('value')
        else:
            self._value = ''
        if 'caption' in kwargs:
            self._caption = kwargs.pop('caption')
        else:
            self._caption = ''
        kwargs['text'] = ''
        super(ValueCaption, self).__init__(**kwargs)
        self._update_text()

    def _update_text(self):
        if self._max_len is not None:
            max_len = self._max_len
        elif self._max_w is not None:
            max_len = self._max_w/self.font_w
        else:
            raise ValueCaptionError('maximum length is unknown')

        self.set_text(_composite_label_text(self._caption,
                                            self._value,
                                            max_len))

    def set_value(self, value):
        self._value = str(value)
        self._update_text()

    def set_caption(self, caption):
        self._caption = str(caption)
        self._update_text
