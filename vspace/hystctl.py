from vspace import VSpaceDriver, VSpaceInput, VSpaceOutput, VSpaceParameter

class HystController(VSpaceDriver):

    _inputs = {
        'SetPoint' : VSpaceParameter('TEMPERATURE'),
        'HystLevel': VSpaceParameter('TEMPERATURE'),
        'HystType': VSpaceParameter('GENERIC'),
        'CurrTemp': VSpaceInput('TEMPERATURE')
    }

    _outputs = {
        'CtlOut': VSpaceOutput('BOOLEAN')
    }

    def __init__(self):
        super(HystController, self).__init__()

        self._current_state = 'idle'

    def cycle(self):

        if self._current_state == 'idle':
            pass
