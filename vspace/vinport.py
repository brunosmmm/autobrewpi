from vspace import VSpaceDriver, VSpaceInput, rpccallable

class VirtualInput(VSpaceDriver):

    _inputs = {'Input': VSpaceInput('GENERIC')}

    def __init__(self, **kwargs):
        super(VirtualInput, self).__init__(**kwargs)

    @rpccallable
    def get_value(self):
        return self.__Input
