
class DrawInstruction(object):
    def __init__(self, kind, **kwargs):
        self.kind = kind
        self.kwargs = kwargs
