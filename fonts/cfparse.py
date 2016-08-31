import re
from array import array
from fontarr import FontArray


class CFontParser(object):

    def __init__(self, lines, data_size=8):

        self._lines = lines
        self.font_map = {}
        self.font_w = None
        self.font_h = None
        self.parsed = False
        self.data_size = data_size

    def _find_MSB(self, value, data_size=8):

        msb = 0
        for i in range(0, data_size):
            if value & (1 << i):
                msb = i

        return msb

    def _list_chunks(self, l, size):
        for i in xrange(0, len(l), size):
            yield l[i:i+size]

    def parse(self):

        self.font_map = {}
        c_counter = 0
        self.font_w = None
        self.font_h = None
        for line in self._lines:

            # ignore empty lines
            if len(line.strip()) == 0:
                continue

            m = re.match(r'\{([0-9A-Fa-f,\sx]+)\}.*', line)

            if m is None:
                raise IOError('invalid line: {}'.format(line))

            bytelist = m.group(1).split(',')

            # combine bytes to create true representation
            valuelist = []
            for chunk in self._list_chunks(bytelist, self.data_size/8):
                val = 0
                for i in range(0, len(chunk)):
                    # endianness??
                    val += int(chunk[i].strip(), 16) << i*8

                valuelist.append(val)

            # check font width
            if self.font_h is None:
                self.font_h = len(bytelist) / (self.data_size/8)
            else:
                if len(bytelist) / (self.data_size/8) != self.font_h:
                    raise IOError('invalid line length: {}; '
                                  'detected length is {}'.format(len(bytelist),
                                                                 self.font_h))

            # check font height
            for value in valuelist:
                if self.font_w is None:
                    self.font_w = self._find_MSB(value, self.data_size) + 1
                else:
                    self.font_w = max(self.font_w,
                                      self._find_MSB(value,
                                                     self.data_size) + 1)

            self.font_map[c_counter] = valuelist

            c_counter += 1

        self.parsed = True

    def get_font_array(self):

        if self.parsed is False:
            self.parse()

        font_data = [array('L', x) for x in self.font_map.values()]

        return FontArray(font_data, self.font_w, self.font_h)
