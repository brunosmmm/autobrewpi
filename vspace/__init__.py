
IO_VARIABLE_TYPES = [
    'POWER_LEVEL',
    'TEMPERATURE',
    'PRESSURE',
    'GENERIC',
    'BOOLEAN'
]

class VSpaceParameter(object):
    def __init__(self, var_type, initial_value = None):
        self._dtype = var_type
        self._value = initial_value

class VSpaceInput(object):
    def __init__(self, var_type, initial_value = None):
        self._dtype = var_type
        self._value = initial_value

class VSpaceOutput(object):
    def __init__(self, var_type):
        self._dtype = var_type

class VSpaceDriver(object):
    def __init__(self):
        self._gvarspace = None
        self._inputs = {}
        self._outputs = {}

    def get_available_var_by_type(self):
        pass

    def update_local_variable(self, variable_name, new_value):
        self._inputs[variable_name]._value = new_value

    def cycle(self):
        pass
