from abpi.vspace import VSpaceDriver, VSpaceOutput


class ConstantValue(VSpaceDriver):

    _outputs = {
        'ConstOut': VSpaceOutput('GENERIC')
        }

    def __init__(self, const_val, **kwargs):
        super(ConstantValue, self).__init__(**kwargs)

        self._const_val = const_val
        self._output_set = False

    def cycle(self):
        # cycle only really runs once
        if self._output_set is False:
            self.set_output_value('ConstOut', self._const_val)
            self._output_set = True
