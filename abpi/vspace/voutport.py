from abpi.vspace import VSpaceDriver, VSpaceOutput, rpccallable


class VirtualOutput(VSpaceDriver):

    _outputs = {'Output': VSpaceOutput('GENERIC')}

    def __init__(self, output_default_value=None, **kwargs):
        super(VirtualOutput, self).__init__(**kwargs)
        self._default_val = output_default_value

    def post_init(self):
        super(VirtualOutput, self).post_init()

        self.__Output = self._default_val

    @rpccallable
    def set_value(self, value):
        self.__Output = value
