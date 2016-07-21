
class DrawInstruction(object):
    def __init__(self, kind, **kwargs):
        self.kind = kind
        self.kwargs = kwargs

class DrawInstructionGroup(object):
    def __init__(self, draw_prio=1000):
        self._prio = draw_prio
        self._instrlist = []

    def add_instruction(self, instr):
        self._instrlist.append(instr)

    def add_instructions(self, *args):
        self._instrlist.extend(args)
