from gadget.hbusjson import HbusClient
from util.thread import StoppableThread
from gadget.vspacerpc import VSpaceRPCController
import time
from datetime import datetime, timedelta
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
        self._read_pending = False
        self._write_pending = True

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
    def __init__(self, direction, port_id, linked_instance,
                 instance_port_name):
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

        # add to list
        self._connection_list.add(connect_to._pid)

        # connect other to this (only do it once!!)
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

    def get_direction(self):
        return self._dir


class GadgetVariableSpace(StoppableThread):

    _initialized = False

    def __init__(self, gadget_uid, scan_interval=1.0):

        super(GadgetVariableSpace, self).__init__()

        self.logger = logging.getLogger('AutoBrew.GVarSpace')

        self._hcli = HbusClient()
        self._guid = gadget_uid
        self._scan_interval = scan_interval
        self._write_queue = deque()

        self._hcli.start()
        # initial server scan, wait for master to be available
        master_state = self._hcli.get_master_state()
        while master_state != 5:
            time.sleep(5)
            master_state = self._hcli.get_master_state()

        tries = 0
        while (tries < 20):
            self._hcli.check_slaves()
            time.sleep(2)
            active_slaves = self._hcli.get_active_slave_list()

            if gadget_uid not in active_slaves:
                tries += 1
                continue

            break

        if tries == 20:
            raise GadgetNotPresentError('easybrewgadget is not available')

        # detect address
        gadget_info = self._hcli.get_slave_info(self._guid)
        self._gaddr = gadget_info['currentaddress']

        # connection matrix
        self._gadget_space_port_matrix = {}
        self._process_space_port_matrix = {}
        self._global_port_counter = 0

        # variable space
        self._varspace = {}

        # parse
        self._parse_objects()
        self._scan_values()

        # drivers
        self._drivers = {}

        # timers
        self._last_scan = datetime.now()

        # RPC server
        self._rpcsrv = VSpaceRPCController(self.rpc_request)
        self._rpcsrv.start()

        self._initialized = True

    def stop(self):
        self._rpcsrv.stop()
        self._rpcsrv.join()
        super(GadgetVariableSpace, self).stop()

    def _parse_objects(self):
        obj_list = self._hcli.get_slave_object_list(self._guid)

        obj_idx = 1
        for obj in obj_list:
            obj_name = obj['description']
            permissions = obj['permissions']
            can_read = True if permissions & 0x01 else False
            can_write = True if permissions & 0x02 else False

            self._varspace[obj_name] = GadgetVariableProxy(obj_idx,
                                                           can_read,
                                                           can_write)
            # create port aliases
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

    def send_gadget_command(self, command):
        self.__Gadget_CTL = int(command)

    def get_variable_names(self):
        return self._varspace.keys()

    def _hbus_read_cb(self, data, user_data):
        # got data!
        var = self._varspace[user_data]
        if var._value != data:
            # trigger systemwide changes
            self.logger.debug('detected a change of value in '
                              'gadget variable "{}"'
                              ', propagating...'.format(user_data))
            self.logger.debug('was: {}, is: {}'.format(var._value, data))
            if var.get_output_port_id() is not None:
                # propagate
                self._propagate_value(var.get_output_port_id(), data)
        var._value = data
        if var._old:
            var._old = False
        if var._read_pending:
            var._read_pending = False

    def _gadget_state_read_cb(self, data, user_data):
        self._hbus_read_cb(data, user_data)
        if int(data) & 0x08:
            # tracked value change detected, read new values
            change_flags = int(data) >> 8
            read_list = []
            for i in range(0, 16):
                if change_flags & (1 << i):
                    read_list.append(i+1)
            self._scan_values(read_list)

    def _scan_variable(self, var_name, rd_callback):
        var = self._varspace[var_name]
        if var._rd:
            try:
                if var._read_pending:
                    return
                self._hcli.read_slave_object(self._gaddr,
                                             var._idx,
                                             False,
                                             rd_callback,
                                             var_name)
                var._read_pending = True
            except Exception as e:
                self.logger.debug('failed to read variable'
                                  ' "{}": {}'.format(var_name, e.message))
                var._old = True

    def _scan_values(self, obj_idx_list=None):
        for var_name, var in self._varspace.iteritems():
            if obj_idx_list is None or var._idx in obj_idx_list:
                self._scan_variable(var_name, self._hbus_read_cb)

    def __setattr__(self, name, value):
        if self._initialized:
            if name in self._varspace.keys():
                self._write_queue.appendleft(GadgetVariableRequest(name,
                                                                   value))
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

        self.logger.debug('registering instance {} with {} inputs and {} outputs'.format(instance_name,
                                                                                         len(driver_class._inputs),
                                                                                         len(driver_class._outputs)))
        kwargs['gvarspace'] = self
        driver_object = driver_class(**kwargs)
        #driver_object._gvarspace = self
        driver_object._instance_name = instance_name

        self._process_driver_ports(driver_object)
        self.logger.debug('driver object: {}'.format(driver_object))

        self._drivers[instance_name] = driver_object

        #call post-initialization hook
        driver_object.post_init()

    def _process_driver_ports(self, driver_object):
        self.logger.debug('processing driver ports')
        self.logger.debug('Inputs:')
        for inp_name, inp_obj in driver_object._inputs.iteritems():
            self.logger.debug('input_name: {}'.format(inp_name))
            #W T F
            port_id = self._new_port_added()
            self.logger.debug('assigning port number {} to port {}.{}'.format(port_id,
                                                                              driver_object.get_instance_name(),
                                                                              inp_name))
            port = VSpacePortDescriptor('input',
                                        port_id,
                                        driver_object.get_instance_name(),
                                        inp_name)
            inp_obj.set_global_port_id(port_id)

            self._process_space_port_matrix[port_id] = port

        self.logger.debug('Outputs:')
        for out_name, out_obj in driver_object._outputs.iteritems():
            self.logger.debug('output_name: {}'.format(out_name))
            port_id = self._new_port_added()
            self.logger.debug('assigning port number {} to port {}.{}'.format(port_id,
                                                                              driver_object.get_instance_name(),
                                                                              out_name))
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
        self.logger.debug('connecting port {} to port {}'.format(port_from, port_to))
        if port_from not in self._process_space_port_matrix:
            #check if it is a gadget space variable
            if port_from not in self._gadget_space_port_matrix:
                raise IOError('invalid port: {}'.format(port_from))

        if port_to not in self._process_space_port_matrix:
            if port_to not in self._gadget_space_port_matrix:
                raise IOError('invalid port: {}'.format(port_to))

        if port_from in self._process_space_port_matrix:
            space_from = self._process_space_port_matrix
            self.logger.debug('port {}: {}.{}'.format(port_from,
                                                      space_from[port_from].get_linked_instance_name(),
                                                      space_from[port_from].get_linked_port_name()))
        else:
            space_from = self._gadget_space_port_matrix

        if port_to in self._process_space_port_matrix:
            space_to = self._process_space_port_matrix
            self.logger.debug('port {}: {}.{}'.format(port_to,
                                                      space_to[port_to].get_linked_instance_name(),
                                                      space_to[port_to].get_linked_port_name()))
        else:
            space_to = self._gadget_space_port_matrix

        space_from[port_from].connect_port(space_to[port_to])

        #generate connection event
        if space_from == self._process_space_port_matrix:
            self._drivers[space_from[port_from].get_linked_instance_name()].port_connected(port_from, port_to)
        if space_to == self._process_space_port_matrix:
            self._drivers[space_to[port_to].get_linked_instance_name()].port_connected(port_to, port_from)

        #make sure which is input and which is output
        input_port = None
        output_port = None
        if space_from[port_from].get_direction() == 'input':
            input_port = space_from[port_from]
        elif space_from[port_from].get_direction() == 'output':
            output_port = space_from[port_from]

        if space_to[port_to].get_direction() == 'input':
            input_port = space_to[port_to]
        elif space_to[port_to].get_direction() == 'output':
            output_port = space_to[port_to]

        #force update
        if output_port is not None:
            if output_port.get_linked_instance_name() == 'gadget':
                value = self._varspace[output_port.get_linked_port_name()].get_value()
            else:
                value = self._drivers[output_port.get_linked_instance_name()]._outputs[output_port.get_linked_port_name()].get_stored_value()

            if input_port is not None:
                if value is not None:
                    if input_port.get_linked_instance_name() == 'gadget':
                        self._varspace[input_port.get_linked_port_name()].set_value(value)
                    else:
                        self._drivers[input_port.get_linked_instance_name()].update_local_variable(input_port.get_linked_port_name(), value)


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

    def is_port_connected(self, port_id):
        if port_id in self._gadget_space_port_matrix:
            return len(self._gadget_space_port_matrix[port_id].get_connected_to()) > 0
        elif port_id in self._process_space_port_matrix[port_id]:
            return len(self._process_space_port_matrix[port_id].get_connected_to()) > 0

        raise KeyError('invalid port id: {}'.format(port_id))

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
                self._drivers[port_descriptor.get_linked_instance_name()].update_local_variable(port_descriptor.get_linked_port_name(), new_value)
            elif connected_to in self._gadget_space_port_matrix:
                #gadget variable, set
                self.logger.debug('propagating value through '
                                  'gadget space port {}'.format(connected_to))
                port_descriptor = self._gadget_space_port_matrix[connected_to]
                self.__setattr__(port_descriptor.get_linked_port_name(), new_value)

    def get_connection_matrix(self):
        ret = {'gadget': {},
               'process': {}}

        for port_id, port_object in self._process_space_port_matrix.iteritems():
            ret['process'][port_id] = port_object._connection_list
        for port_id, port_object in self._gadget_space_port_matrix.iteritems():
            ret['gadget'][port_id] = port_object._connection_list

        return ret

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

    def find_driver_by_classname(self, classname):
        instance_list = []
        for instance_name, instance_object in self._drivers.iteritems():
            if instance_object.__class__.__name__ == classname:
                instance_list.append(instance_name)

        return instance_list

    def get_port_info(self, port_id):
        if port_id in self._gadget_space_port_matrix:
            pspace = self._gadget_space_port_matrix
        elif port_id in self._process_space_port_matrix:
            pspace = self._process_space_port_matrix
        else:
            raise KeyError('invalid port id: {}'.format(port_id))

        return {'direction' : pspace[port_id].get_direction(),
                'instname': pspace[port_id].get_linked_instance_name(),
                'portname': pspace[port_id].get_linked_port_name(),
                'connected_to': pspace[port_id].get_connected_to()}

    def get_driver_method(self, instance_name, method_name):
        if instance_name in self._drivers:
            return self._drivers[instance_name].__getattr__(method_name)
        raise KeyError('Invalid instance name: {}'.format(instance_name))

    def call_driver_method(self, instance_name, method_name, **kwargs):
        return self._call_driver_method('local', instance_name, method_name, **kwargs)

    def _call_driver_method(self, source, instance_name, method_name, **kwargs):
        if instance_name in self._drivers:
            return self._drivers[instance_name].extern_method_call(source, method_name, **kwargs)
        else:
            raise KeyError('Invalid instance name: {}'.format(instance_name))

    def driver_log(self, instance_name, log_level, message):
        if log_level == 'ERR':
            self.logger.error('{}: {}'.format(instance_name, message))
        elif log_level == 'WARN':
            self.logger.warning('{}: {}'.format(instance_name, message))
        elif log_level == 'INFO':
            self.logger.info('{}: {}'.format(instance_name, message))

    def rpc_request(self, request, *args, **kwargs):
        if request == 'portlist':
            return {'gadget': self._gadget_space_port_matrix.keys(),
                    'process': self._process_space_port_matrix.keys()}
        if request == 'findport':
            try:
                return self.find_port_id(**kwargs)
            except ValueError:
                return None
        if request == 'portinfo':
            try:
                return self.get_port_info(**kwargs)
            except KeyError:
                return None
        if request == 'matrix':
            return self.get_connection_matrix()
        if request == 'getval':
            return self.get_current_value(**kwargs)
        if request == 'call':
            return self._call_driver_method('rpc', *args, **kwargs)

    def get_current_value(self, port_id):

        if port_id in self._gadget_space_port_matrix:
            var_name = self._gadget_space_port_matrix[port_id].get_linked_port_name()
            return self._varspace[var_name].get_value()
        elif port_id in self._process_space_port_matrix:
            inst_name = self._process_space_port_matrix[port_id].get_linked_instance_name()
            var_name = self._process_space_port_matrix[port_id].get_linked_port_name()

            try:
                return self._drivers[inst_name].get_variable_value(var_name)
            except AttributeError:
                self.logger.warning('get_current_value: no such port: {}.{}'.format(inst_name, var_name))
                return None

    def run(self):

        while True:
            if self.is_stopped():
                self._hcli.stop()
                exit(0)

            #scan only state and determine if an update is needed
            if datetime.now() > self._last_scan + timedelta(seconds=self._scan_interval):
                self._last_scan = datetime.now()
                self._scan_variable('Gadget_STATE', self._gadget_state_read_cb)

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
            time.sleep(0.01)
            #time.sleep(self._scan_interval)
