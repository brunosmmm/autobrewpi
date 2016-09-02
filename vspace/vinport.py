from vspace import VSpaceDriver, VSpaceInput, rpccallable


class VirtualInput(VSpaceDriver):

    _inputs = {'Input': VSpaceInput('GENERIC')}

    def __init__(self, **kwargs):
        super(VirtualInput, self).__init__(**kwargs)

    @rpccallable
    def get_value(self):
        return self.__Input

    def set_value(self, value):
        """If disconnected, allows to set value
        """
        if self._inputs['Input'].get_connected() is False:
            self._inputs['Input'].set_value(value)

    @rpccallable
    def is_connected(self):
        return self._inputs['Input'].get_connected()
