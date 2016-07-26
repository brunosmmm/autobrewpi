from vspace import VSpaceDriver, VSpaceInput, VSpaceOutput, VSpaceParameter

class ByteComp(VSpaceDriver):

    _inputs = {
        'Bit0': VSpaceInput('BOOLEAN'),
        'Bit1': VSpaceInput('BOOLEAN'),
        'Bit2': VSpaceInput('BOOLEAN'),
        'Bit3': VSpaceInput('BOOLEAN'),
        'Bit4': VSpaceInput('BOOLEAN'),
        'Bit5': VSpaceInput('BOOLEAN'),
        'Bit6': VSpaceInput('BOOLEAN'),
        'Bit7': VSpaceInput('BOOLEAN')
    }

    _outputs = {
        'ByteOut': VSpaceOutput('BYTE')
    }

    def __init__(self):
        super(ByteComp, self).__init__()

    def update_local_variable(self, *args, **kwargs):
        super(ByteComp, self).update_local_variable(*args, **kwargs)

        output_value = 0x00
        for i in range(0, 8):
            if self.get_input_value('Bit{}'.format(i)):
                output_value |= (1<<i)

        self.set_output_value('ByteOut', output_value)

        #clear flags
        self.get_flags()
