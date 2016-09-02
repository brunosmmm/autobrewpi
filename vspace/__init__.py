import copy

IO_VARIABLE_TYPES = [
    'POWER_LEVEL',
    'TEMPERATURE',
    'PRESSURE',
    'GENERIC',
    'BOOLEAN',
    'BYTE',
    'INTEGER',
    'FLOAT'
]


class ParameterLockedError(Exception):
    pass


class CallNotAllowedError(Exception):
    pass


def _check_variable_dtype(wanted_type, value):
    error = False

    if wanted_type == 'BOOLEAN':
        if not isinstance(value, bool):
            error = True
    elif wanted_type == 'BYTE':
        if not isinstance(value, int):
            # try to convert
            try:
                int(value, 2)
                return
            except:
                error = True

            try:
                int(value, 16)
                return
            except:
                error = True

            try:
                int(value)
                return
            except:
                error = True
    # todo: check others

    if error:
        raise TypeError('invalid python type'
                        ' for variable type {}'.format(wanted_type))


def _autoconvert_variable_value(wanted_type, value):
    val = value
    if wanted_type in ('BYTE', 'INTEGER'):
        try:
            val = int(value)
            return val
        except:
            pass
        try:
            val = int(value, 2)
            return val
        except:
            pass
        try:
            val = int(value, 16)
            return val
        except:
            pass
    elif wanted_type in ('FLOAT', 'TEMPERATURE'):
        try:
            val = float(value)
            return val
        except:
            pass

    return val


class VSpacePort(object):
    def __init__(self, dtype, tags=[], global_id=None):
        self._dtype = dtype
        self._global_id = global_id
        self._parent = None
        self._tags = set(tags)
        self._connected = False

    def set_parent(self, parent_object):
        self._parent = parent_object

    def set_global_port_id(self, port_id):
        self._global_id = port_id

    def get_global_port_id(self):
        return self._global_id

    def get_tags(self):
        return list(self._tags)

    def add_tag(self, tag):
        self._tags.add(tag)

    def remove_tag(self, tag):
        self._tags.remove(tag)

    def get_connected(self):
        return self._connected

    def set_connected(self):
        self._connected = True

    def set_disconected(self):
        self._connected = False


class VSpaceInput(VSpacePort):
    def __init__(self, dtype, initial_value=None):
        super(VSpaceInput, self).__init__(dtype)
        self._value = initial_value
        self._value_changed = False

    def set_value(self, value):

        _check_variable_dtype(self._dtype, value)
        val = _autoconvert_variable_value(self._dtype, value)

        if val != self._value:
            self._value_changed = True
        self._value = val

    def get_value(self):
        # clear flags
        self._value_changed = False
        return self._value

    def value_changed(self):
        # also clear flags
        self._value_changed = False
        return self._value_changed


class VSpaceParameter(VSpaceInput):
    def __init__(self, var_type, initial_value=None):
        super(VSpaceParameter, self).__init__(var_type, initial_value)

    def set_value(self, value):

        if self._parent is not None:
            if self._parent.parameters_locked():
                raise ParameterLockedError('parameter is locked by driver')
        else:
            raise ParameterLockedError('cannot determine'
                                       ' parameter lock state!')

        super(VSpaceParameter, self).set_value(value)


class VSpaceOutput(VSpacePort):
    def __init__(self, dtype, initial_value=None):
        super(VSpaceOutput, self).__init__(dtype)
        # ideally this differs from an input in the way
        # the values are updated and propagated
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

    def __init__(self, **kwargs):
        if 'gvarspace' in kwargs:
            self._gvarspace = kwargs['gvarspace']
        else:
            self._gvarspace = None
        self._instance_name = None

        # make a copy of the input/output declaration
        # to isolate different instances
        input_copy = copy.deepcopy(self._inputs)
        output_copy = copy.deepcopy(self._outputs)

        self._inputs = input_copy
        self._outputs = output_copy

        # link ports to driver
        for port_name, port_object in self._inputs.iteritems():
            port_object.set_parent(self)
        for port_name, port_object in self._outputs.iteritems():
            port_object.set_parent(self)

        # flags
        self._flags = set()

    def get_variable_value(self, var_name):
        return self.__getattr__('__'+var_name)

    def extern_method_call(self, call_src, method_name, **kwargs):
        method = self.__getattr__(method_name)
        if call_src == 'local':
            return method(**kwargs)

        try:
            if call_src == 'rpc':
                if method.rpc_call:
                    return method(**kwargs)
        except AttributeError:
            raise CallNotAllowedError('method can not be called externally')

    def __getattr__(self, attr_name):
        # check if theres such an input
        try:
            var_name = attr_name.split('__')[1]
            if var_name in self._inputs:
                return self.get_input_value(var_name)

            # check for outputs
            if var_name in self._outputs:
                return self.get_output_stored_value(var_name)
        except IndexError:
            pass

        return super(VSpaceDriver, self).__getattribute__(attr_name)

    def __setattr__(self, attr_name, value):
        try:
            var_name = attr_name.split('__')[1]
            if var_name in self._outputs:
                self.set_output_value(var_name, value)
                return
        except IndexError:
            pass

        super(VSpaceDriver, self).__setattr__(attr_name, value)

    def _set_flag(self, flag):
        if flag in self._AVAILABLE_FLAGS:
            self._flags.add(flag)

    def _clear_flag(self, flag):
        if flag in self._AVAILABLE_FLAGS and flag in self._flags:
            self._flags.remove(flag)

    def get_available_var_by_type(self):
        pass

    # todo rename this, maybe _input_value_change
    def update_local_variable(self, variable_name, new_value):
        """Update an input. This is called by the gadget variable space manager
        """
        self._inputs[variable_name].set_value(new_value)
        # mark changes
        self._set_flag('inputs_changed')

    def _output_value_change(self, variable_name, new_value):
        """Update an output. This is called by the driver code to signal an update
        """
        self._outputs[variable_name].set_value(new_value)
        # trigger change
        self._gvarspace.trigger_output_change(self._instance_name,
                                              variable_name,
                                              new_value)

    def get_input_value(self, variable_name):
        return self._inputs[variable_name].get_value()

    def get_output_stored_value(self, variable_name):
        return self._outputs[variable_name].get_stored_value()

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

    def parameters_locked(self):
        """Returns if parameters are locked
        """
        return False

    def post_init(self):
        pass

    def cycle(self):
        pass

    def port_connected(self, port_id, connected_to_id):
        for port_name, port_obj in self._inputs.iteritems():
            if port_obj.get_global_port_id() == port_id:
                port_obj.set_connected()
                return

        for port_name, port_obj in self._outputs.iteritems():
            if port_obj.get_global_port_id() == port_id:
                port_obj.set_connected()

    def port_disconnected(self, port_id):
        for port_name, port_obj in self._inputs.iteritems():
            if port_obj.get_global_port_id() == port_id:
                port_obj.set_disconnected()
                return

        for port_name, port_obj in self._outputs.iteritems():
            if port_obj.get_global_port_id() == port_id:
                port_obj.set_disconnected()

    def log_warn(self, msg):
        if self._gvarspace is not None:
            self._gvarspace.driver_log(self._instance_name, 'WARN', msg)

    def log_err(self, msg):
        if self._gvarspace is not None:
            self._gvarspace.driver_log(self._instance_name, 'ERR', msg)

    def log_info(self, msg):
        if self._gvarspace is not None:
            self._gvarspace.driver_log(self._instance_name, 'INFO', msg)

    def shutdown(self):
        pass


# helpers
def rpccallable(func):

    func.rpc_call = True

    return func
