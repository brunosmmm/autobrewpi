import re

_COORDINATE_REGEX = re.compile(r'(x|y)([0-9]+)?')

class DrawInstruction(object):
    def __init__(self, kind, **kwargs):
        self.kind = kind
        self.kwargs = kwargs

    def translate(self, x, y):
        """Translate draw coordinates using general regex
        """
        for kwarg_name, kwarg_val in self.kwargs.iteritems():
            m = re.match(_COORDINATE_REGEX, kwarg_name)

            if m != None:
                if m.group(1) == 'x':
                    self.kwargs[kwarg_name] = kwarg_val + x
                elif m.group(1) == 'y':
                    self.kwargs[kwarg_name] = kwarg_val + y


class DrawInstructionGroup(object):
    def __init__(self, draw_prio=0):
        self._prio = draw_prio
        self._instrlist = []

    def add_instruction(self, instr):
        self._instrlist.append(instr)

    def add_instructions(self, *args):
        self._instrlist.extend(args)

    def set_priority(self, priority):
        self._prio = priority

    def translate(self, x, y):

        for instr in self._instrlist:
            instr.translate(x, y)
