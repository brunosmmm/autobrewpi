from vspace import VSpaceDriver, VSpaceInput, VSpaceOutput, VSpaceParameter

class HystController(VSpaceDriver):

    _inputs = {
        'SetPoint' : VSpaceParameter('TEMPERATURE'),
        'HystLevel': VSpaceParameter('TEMPERATURE'),
        'HystType': VSpaceParameter('GENERIC'),
        'CurrTemp': VSpaceInput('TEMPERATURE'),
        'Enabled': VSpaceInput('BOOLEAN')
    }

    _outputs = {
        'CtlOut': VSpaceOutput('BOOLEAN')
    }

    def __init__(self, **kwargs):
        super(HystController, self).__init__(**kwargs)

        self._current_state = 'idle'
        self._deadzone = False

    def _element_on(self):
        if self.__CtlOut is False:
            self.__CtlOut = True

    def _element_off(self):
        if self.__CtlOut:
            self.__CtlOut = False

    def update_local_variable(self, variable_name, new_value):
        """Asynchronously control state
        """
        super(HystController, self).update_local_variable(variable_name, new_value)

        if variable_name == 'Enabled':
            if new_value:
                if self._current_state == 'idle':
                    self._current_state = 'control'
            else:
                self._current_state = 'idle'
                self._element_off()
                self._deadzone = False

    def parameters_locked(self):
        """Lock parameters when in an active state
        """
        if self._current_state != 'idle':
            return True

        return False


    def cycle(self):

        if self._current_state == 'idle':
            return

        if self.get_input_value('HystType') == 'down':
            output_enable_condition = True if self.__CurrTemp < self.__SetPoint else False
            output_restart_condition = True if self.__CurrTemp < (self.__SetPoint - self.__HystLevel) else False
        elif self.get_input_value('HystType') == 'up':
            output_enable_condition = True if self.__CurrTemp < (self.__SetPoint + self.__HystLevel) else False
            output_restart_condition = True if self.__CurrTemp < self.__SetPoint else False
        elif self.get_input_value('HystType') == 'updown':
            output_enable_condition = True if self.__CurrTemp < (self.__SetPoint + self.__HystLevel) else False
            output_restart_condition = True if self.__CurrTemp < (self.__SetPoint - self.__HystLevel) else False
        else:
            return

        if self._current_state == 'control':
            if output_enable_condition:
                if self._deadzone is False:
                    self._element_on()
                else:
                    if output_restart_condition:
                        self._element_on()
                        self._deadzone = False
            else:
                if self._deadzone:
                    if output_restart_condition:
                        self._element_on()
                        self._deadzone = False
                else:
                    self._element_off()
                    self._deadzone = True

        else:
            #unknown ??
            self._current_state = 'idle'
