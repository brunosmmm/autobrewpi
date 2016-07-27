from gadget.hbusjson import HbusClient
from util.thread import StoppableThread
from vspace import VSpaceDriver, VSpaceInput, VSpaceOutput, VSpaceParameter
import time
from collections import deque
import re
import logging

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
        self._input_port = None
        self._output_port = None

    def set_value(self, value):
        if self._wr:
            self._value = value

    def get_value(self):
        if self._rd:
            return self._value

        return None

    def can_read(self):
        return self._rd

    def can_write(self):
        return self._wr

    def set_output_port_id(self, pid):
        self._output_port = pid

    def set_input_port_id(self, pid):
        self._input_port = pid

    def get_output_port_id(self):
        return self._output_port

    def get_input_port_id(self):
        return self._input_port


class VSpacePortDescriptor(object):
    def __init__(self, direction, port_id, linked_instance, instance_port_name):
        self._dir = direction
        self._pid = port_id
        self._inst = linked_instance
        self._inst_pname = instance_port_name
        self._gvarspace = None

        self._connection_list = set()

    def connect_port(self, connect_to, dont_recurse=False):
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

        #connect other to this (only do it once!!)
        if dont_recurse is False:
            connect_to.connect_port(self, dont_recurse=True)

    def disconnect_port(self, connected_to, dont_recurse=False):
        if connected_to._pid in self._connection_list:
            self._connection_list.remove(connected_to._pid)

            if dont_recurse is False:
                connected_to.disconnect_port(self, dont_recurse=True)

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

        self.logger = logging.getLogger('AutoBrew.GVarSpace')

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
        self._gadget_space_port_matrix = {}
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
            #create port aliases
            if (can_write):
                port_id = self._new_port_added()
                port = VSpacePortDescriptor('input',
                                            port_id,
                                            'gadget',
                                            obj_name)
                self._gadget_space_port_matrix[port_id] = port
                self._varspace[obj_name].set_input_port_id(port_id)
            if (can_read):
                port_id = self._new_port_added()
                port = VSpacePortDescriptor('output',
                                            port_id,
                                            'gadget',
                                            obj_name)
                self._gadget_space_port_matrix[port_id] = port
                self._varspace[obj_name].set_output_port_id(port_id)

            obj_idx += 1

    def get_variable_names(self):
        return self._varspace.keys()

    def _scan_values(self):

        for var_name, var in self._varspace.iteritems():
            if var._rd:
                try:
                    value = self._hcli.read_slave_object(self._gaddr, var._idx)
                    if var._value != value:
                        #trigger systemwide changes
                        self.logger.debug('detected a change of value in '
                                          'gadget variable "{}", propagating...'.format(var_name))
                        if var.get_output_port_id() is not None:
                            self._propagate_value(var.get_output_port_id(), value)

                    var._value = value
                    if var._old:
                        var._old = False
                except Exception:
                    #could not read
                    self.logger.debug('failed to read variable "{}"'.format(var_name))
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
        return super(GadgetVariableSpace, self).__getattribute__(name)

    def register_driver(self, driver_class, instance_name, **kwargs):

        if instance_name in self._drivers:
            raise ValueError('instance name already allocated')

        driver_object = driver_class(**kwargs)
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
            #check if it is a gadget space variable
            if port_from not in self._gadget_space_port_matrix:
                raise IOError('invalid port: {}'.format(port_from))

        if port_to not in self._process_space_port_matrix:
            if port_to not in self._gadget_space_port_matrix:
                raise IOError('invalid port: {}'.format(port_to))

        if port_from in self._process_space_port_matrix:
            space_from = self._process_space_port_matrix
        else:
            space_from = self._gadget_space_port_matrix

        if port_to in self._process_space_port_matrix:
            space_to = self._process_space_port_matrix
        else:
            space_to = self._gadget_space_port_matrix

        space_from[port_from].connect_port(space_to[port_to])

    def disconnect_pspace_ports(self, port_from, port_to):
        if port_from not in self._process_space_port_matrix:
            if port_from not in self._gadget_space_port_matrix:
                raise IOError('invalid port: {}'.format(port_from))

        if port_to not in self._process_space_port_matrix:
            if port_to not in self._gadget_space_port_matrix:
                raise IOError('invalid port: {}'.format(port_to))

        if port_from in self._process_space_port_matrix:
            space_from = self._process_space_port_matrix
        else:
            space_from = self._gadget_space_port_matrix

        if port_to in self._process_space_port_matrix:
            space_to = self._process_space_port_matrix
        else:
            space_to = self._gadget_space_port_matrix

        space_from[port_from].disconnect_port(space_to[port_to])

    def get_driver_ports(self, instance_name):
        inputs = {}
        outputs = {}

        if instance_name == 'gadget':
            space = self._gadget_space_port_matrix
        else:
            space = self._process_space_port_matrix

        for port_id, port_object in space.iteritems():
            if port_object.get_linked_instance_name() == instance_name:
                if port_object._dir == 'input':
                    inputs[port_id] = port_object
                elif port_object._dir == 'output':
                    outputs[port_id] = port_object

        return {'inputs': inputs, 'outputs': outputs}

    def find_port_id(self, instance_name, port_name, port_direction):
        if instance_name == 'gadget':
            if port_direction == 'input':
                return self._varspace[port_name].get_input_port_id()
            elif port_direction == 'output':
                return self._varspace[port_name].get_output_port_id()
            else:
                raise ValueError('invalid port name: {}'.format(port_name))
        elif instance_name in self._drivers:
            if port_direction == 'input':
                return self._drivers[instance_name]._inputs[port_name].get_global_port_id()
            elif port_direction == 'output':
                return self._drivers[instance_name]._outputs[port_name].get_global_port_id()
            else:
                raise ValueError('invalid port name: {}'.format(port_name))
        else:
            raise ValueError('invalid instance: {}'.format(instance_name))


    def get_available_var_by_type(self, var_type):
        pass

    def trigger_output_change(self, instance_name, output_variable, new_value):
        if instance_name not in self._drivers:
            raise KeyError('invalid instance_name: {}'.format(instance_name))

        if output_variable not in self._drivers[instance_name]._outputs:
            raise KeyError('invalid output name: {}'.format(output_variable))

        self.logger.debug('instance "{}" registered a change'
                          ' in output "{}", propagating...'.format(instance_name, output_variable))

        #todo avoid deadlocks (more like infinite loop) here

        #get connection list and update
        port_global_id = self._drivers[instance_name]._outputs[output_variable].get_global_port_id()
        self._propagate_value(port_global_id, new_value)

    def _propagate_value(self, port_global_id, new_value):
        if port_global_id in self._process_space_port_matrix:
            space = self._process_space_port_matrix
        elif port_global_id in self._gadget_space_port_matrix:
            space = self._gadget_space_port_matrix
        else:
            raise IOError('invalid port id: {}'.format(global_port_id))

        for connected_to in space[port_global_id].get_connected_to():
            #propagate
            if connected_to in self._process_space_port_matrix:
                self.logger.debug('propagating value through '
                                  'process space port {}'.format(connected_to))
                port_descriptor = self._process_space_port_matrix[connected_to]
                self._drivers[port_descriptor.get_linked_instance_name()]._inputs[port_descriptor.get_linked_port_name()].set_value(new_value)
            elif connected_to in self._gadget_space_port_matrix:
                #gadget variable, set
                self.logger.debug('propagating value through '
                                  'gadget space port {}'.format(connected_to))
                port_descriptor = self._gadget_space_port_matrix[connected_to]
                self.__setattr__(port_descriptor.get_linked_port_name(), new_value)

    def _debug_dump_port_list(self):
        print 'Port list dump'
        print 'Process Space:'
        for port_id, port_object in self._process_space_port_matrix.iteritems():
            print '{}: {}.{} ({}), connects to: {}'.format(port_id,
                                                           port_object.get_linked_instance_name(),
                                                           port_object.get_linked_port_name(),
                                                           port_object._dir,
                                                           port_object._connection_list)
        print 'Gadget Space:'
        for port_id, port_object in self._gadget_space_port_matrix.iteritems():
            print '{}: {}.{} ({}), connects to: {}'.format(port_id,
                                                           port_object.get_linked_instance_name(),
                                                           port_object.get_linked_port_name(),
                                                           port_object._dir,
                                                           port_object._connection_list)

    def run(self):

        while True:
            if self.is_stopped():
                exit(0)

            #scan values continuously
            self._scan_values()

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

            #wait
            time.sleep(self._scan_interval)
