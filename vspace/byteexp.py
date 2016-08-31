from vspace import VSpaceDriver, VSpaceInput, VSpaceOutput, rpccallable


class ByteExp(VSpaceDriver):

    _inputs = {
        'ByteIn': VSpaceInput('BYTE')
    }

    _outputs = {
        'Bit0': VSpaceOutput('BOOLEAN'),
        'Bit1': VSpaceOutput('BOOLEAN'),
        'Bit2': VSpaceOutput('BOOLEAN'),
        'Bit3': VSpaceOutput('BOOLEAN'),
        'Bit4': VSpaceOutput('BOOLEAN'),
        'Bit5': VSpaceOutput('BOOLEAN'),
        'Bit6': VSpaceOutput('BOOLEAN'),
        'Bit7': VSpaceOutput('BOOLEAN')
    }

    def __init__(self, **kwargs):
        super(ByteExp, self).__init__(**kwargs)

    @rpccallable
    def get_current_state(self):
        return self.__ByteIn

    def update_local_variable(self, *args, **kwargs):
        super(ByteExp, self).update_local_variable(*args, **kwargs)

        # update outputs immediately
        for i in range(0, 8):
            if self.get_input_value('ByteIn') & (1 << i):
                self.set_output_value('Bit{}'.format(i), True)
            else:
                self.set_output_value('Bit{}'.format(i), False)

        # clear flags
        self.get_flags()
