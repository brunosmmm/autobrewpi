from gadget.hbusjson import HbusClient
from util.thread import StoppableThread
from vspace import VSpaceDriver, VSpaceInput, VSpaceOutput, VSpaceParameter
import time
from collections import deque
import re

_GADGET_DRIVER_REGEX = re.compile(r'([a-zA-Z]+)([0-9]+)_([a-zA-Z0-9]+)')

class GadgetNotPresentError(Exception):
    pass

class GadgetVariableError(Exception):
    pass

class GadgetVariableRequest(object):
    def __init__(self, var_name, value):
        self._var = var_name
        self._value = value

class GadgetVariableProxy(object):
    def __init__(self, object_idx, can_read=False, can_write=False):
        self._idx = object_idx
        self._rd = can_read
        self._wr = can_write
        self._old = False

        self._value = None

    def set_value(self, value):
        if self._wr:
            self._value = value

    def get_value(self):
        if self._rd:
            return self._value

        return None

class VSpacePortDescriptor(object):
    def __init__(self, direction, port_id, linked_instance, instance_port_name):
        self._dir = direction
        self._pid = port_id
        self._inst = linked_instance
        self._inst_pname = instance_port_name

        self._connection_list = set()

    def connect_port(self, connect_to):
        if self._dir == 'input':
            if len(self._connection_list) > 0:
                raise IOError('cannot connect two ports to an input')

            if connect_to._dir == 'input':
                raise IOError('cannot connect input to input')

        elif self._dir == 'output':
            if connect_to._dir == 'output':
                raise IOError('cannot connect output to output')

        else:
            raise IOError('unknown error!')

        #add to list
        self._connection_list.add(connect_to._pid)

    def disconnect_port(self, connected_to):
        if connected_to._pid in self._connection_list:
            self._connection_list.remove(connected_to._pid)

            connected_to.disconnect_port(self)

    def get_connected_to(self):
        return list(self._connection_list)

    def get_linked_instance_name(self):
        return self._inst

    def get_linked_port_name(self):
        return self._inst_pname

class GadgetVariableSpace(StoppableThread):

    _initialized = False

    def __init__(self, gadget_uid, scan_interval=2.0):

        super(GadgetVariableSpace, self).__init__()

        self._hcli = HbusClient()
        self._guid = gadget_uid
        self._scan_interval = scan_interval
        self._write_queue = deque()

        #scan server
        active_slaves = self._hcli.get_active_slave_list()

        if gadget_uid not in active_slaves:
            raise GadgetNotPresentError('easybrewgadget is not available')

        #detect address
        gadget_info = self._hcli.get_slave_info(self._guid)
        self._gaddr = gadget_info['currentaddress']

        #connection matrix
        self._gadget_output_allocation = {}
        self._process_space_port_matrix = {}
        self._global_port_counter = 0

        #variable space
        self._varspace = {}

        #parse
        self._parse_objects()
        self._scan_values()

        #drivers
        self._drivers = {}

        self._initialized = True

    def _parse_objects(self):
        obj_list = self._hcli.get_slave_object_list(self._guid)

        obj_idx = 1
        for obj in obj_list:
            obj_name = obj['description']
            permissions = obj['permissions']
            can_read = True if permissions & 0x01 else False
            can_write = True if permissions & 0x02 else False

            self._varspace[obj_name] = GadgetVariableProxy(obj_idx, can_read, can_write)
            if (can_write):
                self._gadget_output_allocation[obj_name] = None

            obj_idx += 1

    def get_variable_names(self):
        return self._varspace.keys()

    def _scan_values(self):

        for var in self._varspace.values():
            if var._rd:
                try:
                    value = self._hcli.read_slave_object(self._gaddr, var._idx)
                    var._value = value
                    if var._old:
                        var._old = False
                except Exception:
                    #could not read
                    var._old = True

            time.sleep(0.1)

    def __setattr__(self, name, value):
        if self._initialized:
            if name in self._varspace.keys():
                self._write_queue.appendleft(GadgetVariableRequest(name, value))
                return
        super(GadgetVariableSpace, self).__setattr__(name, value)

    def __getattr__(self, name):
        if self._initialized:
            if name in self._varspace.keys():
                return self._varspace[name].get_value()
        return super(GadgetVariableSpace, self).__getattr__(name)

    def register_driver(self, driver_class, instance_name):

        if instance_name in self._drivers:
            raise ValueError('instance name already allocated')

        driver_object = driver_class()
        driver_object._gvarspace = self
        driver_object._instance_name = instance_name

        self._process_driver_ports(driver_object)

        self._drivers[instance_name] = driver_object

    def _process_driver_ports(self, driver_object):
        for inp_name, inp_obj in driver_object._inputs.iteritems():
            port_id = self._new_port_added()
            port = VSpacePortDescriptor('input',
                                        port_id,
                                        driver_object.get_instance_name(),
                                        inp_name)
            inp_obj.set_global_port_id(port_id)

            self._process_space_port_matrix[port_id] = port

        for out_name, out_obj in driver_object._outputs.iteritems():
            port_id = self._new_port_added()
            port = VSpacePortDescriptor('output',
                                        port_id,
                                        driver_object.get_instance_name(),
                                        out_name)
            out_obj.set_global_port_id(port_id)

            self._process_space_port_matrix[port_id] = port

    def _new_port_added(self):
        current_id = self._global_port_counter
        self._global_port_counter += 1
        return current_id

    def connect_pspace_ports(self, port_from, port_to):
        if port_from not in self._process_space_port_matrix:
            raise IOError('invalid port: {}'.format(port_from))

        if port_to not in self._process_space_port_matrix:
            raise IOError('invalid port: {}'.format(port_to))

        #try to connect
        self._process_space_port_matrix[port_from].connect_port(self._process_space_port_matrix[port_to])

    def disconnect_pspace_ports(self, port_from, port_to):
        if port_from not in self._process_space_port_matrix:
            raise IOError('invalid port: {}'.format(port_from))

        if port_to not in self._process_space_port_matrix:
            raise IOError('invalid port: {}'.format(port_to))

        self._process_space_port_matrix[port_from].disconnect_port(self._process_space_port_matrix[port_to])

    def get_available_var_by_type(self, var_type):
        pass

    def trigger_output_change(self, instance_name, output_variable, new_value):
        if instance_name not in self._drivers:
            raise KeyError('invalid instance_name: {}'.format(instance_name))

        if output_variable not in self._drivers[instance_name]._outputs:
            raise KeyError('invalid output name: {}'.format(output_variable))

        #todo avoid deadlocks (more like infinite loop) here

        #get connection list and update
        port_global_id = self._drivers[instance_name]._outputs[output_variable].get_global_port_id()
        for connected_to in self._process_space_port_matrix[port_global_id].get_connected_to():
            #propagate
            port_descriptor = self._process_space_port_matrix[connected_to]
            self._drivers[port_descriptor.get_linked_instance_name()]._inputs[port_descriptor.get_linked_port_name()].set_value(new_value)

    def run(self):

        while True:
            if self.is_stopped():
                exit(0)

            #set values if pending
            while len(self._write_queue) > 0:
                req = self._write_queue.pop()
                if self._varspace[req._var]._wr:
                    try:
                        self._hcli.write_slave_object(self._gaddr,
                                                      self._varspace[req._var]._idx,
                                                      req._value)
                        #update value in proxy
                        self._varspace[req._var].set_value(req._value)
                    except Exception:
                        #could not set value
                        raise GadgetVariableError('could not set variable value')

            #execute driver cycles
            for driver in self._drivers.values():
                try:
                    driver.cycle()
                except Exception:
                    raise

            #scan values continuously
            self._scan_values()

            #wait
            time.sleep(self._scan_interval)
