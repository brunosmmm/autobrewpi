
IO_VARIABLE_TYPES = [
    'POWER_LEVEL',
    'TEMPERATURE',
    'PRESSURE',
    'GENERIC',
    'BOOLEAN',
    'BYTE'
]

def _check_variable_dtype(self, wanted_type, value):
    error = False

    if wanted_type == 'BOOLEAN':
        if not isinstance(bool, value):
            error = True
    elif wanted_type == 'BYTE':
        if not isinstance(int, value):
            error = True
    # todo: check others

    if error:
        raise TypeError('invalid python type for variable type {}'.format(wanted_type))

class VSpacePort(object):
    def __init__(self, dtype, global_id=None):
        self._dtype = dtype
        self._global_id = global_id
        self._parent = None

    def set_parent(self, parent_object):
        self._parent = parent_object

    def set_global_port_id(self, port_id):
        self._global_id = port_id

    def get_global_port_id(self):
        return self._global_id

class VSpaceInput(VSpacePort):
    def __init__(self, dtype, initial_value = None):
        super(VSpaceInput, self).__init__(dtype)
        self._value = initial_value
        self._value_changed = False

    def set_value(self, value):

        _check_variable_dtype(self._dtype, value)

        if value != self._value:
            self._value_changed = True
        self._value = value

    def get_value(self):
        #clear flags
        self._value_changed = False
        return self._value

    def value_changed(self):
        #also clear flags
        self._value_changed = False
        return self._value_changed

class VSpaceParameter(VSpaceInput):
    def __init__(self, var_type, initial_value = None):
        super(VSpaceParameter, self).__init__(var_type, initial_value)

class VSpaceOutput(VSpacePort):
    def __init__(self, dtype, initial_value = None):
        super(VSpaceOutput, self).__init__(dtype)
        #ideally this differs from an input in the way
        #the values are updated and propagated
        self._stored_value = initial_value

    def set_value(self, value):

        _check_variable_dtype(self._dtype, value)

        self._stored_value = value

    def get_stored_value(self):
        return self._stored_value

class VSpaceDriver(object):

    _AVAILABLE_FLAGS = ('inputs_changed')

    _inputs = {}
    _outputs = {}

    def __init__(self):
        self._gvarspace = None
        self._instance_name = None

        #link ports to driver
        for port_name, port_object in self._inputs.iteritems():
            port_object.set_parent(self)
        for port_name, port_object in self._outputs.iteritems():
            port_object.set_parent(self)

        #flags
        self._flags = set()

    def _set_flag(self, flag):
        if flag in self._AVAILABLE_FLAGS:
            self._flags.add(flag)

    def _clear_flag(self, flag):
        if flag in self._AVAILABLE_FLAGS and flag in self._flags:
            self._flags.remove(flag)

    def get_available_var_by_type(self):
        pass

    #todo rename this, maybe _input_value_change
    def update_local_variable(self, variable_name, new_value):
        """Update an input. This is called by the gadget variable space manager
        """
        self._inputs[variable_name].set_value(new_value)
        #mark changes
        self._set_flag('inputs_changed')

    def _output_value_change(self, variable_name, new_value):
        """Update an output. This is called by the driver code to signal an update
        """
        self._outputs[variable_name].set_value(new_value)
        #trigger change
        self._gvarspace.trigger_output_change(self._instance_name, variable_name, new_value)

    def get_input_value(self, variable_name):
        return self._inputs[variable_name].get_value()

    def get_input_changed(self, variable_name):
        return self._inputs[variable_name].value_changed()

    def set_output_value(self, variable_name, value):
        self._output_value_change(variable_name, value)

    def get_instance_name(self):
        return self._instance_name

    def get_flags(self):
        """Reads flags; will get cleared
        """
        flags = self._flags
        self._flags.clear()
        return flags

    def cycle(self):
        pass
