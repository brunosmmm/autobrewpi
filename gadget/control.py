from gadget.hbusjson import HbusClient
from util.thread import StoppableThread
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

        #variable space
        self._varspace = {}

        #parse
        self._parse_objects()
        self._scan_values()

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

            time.sleep(0.01)

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

            #scan values continuously
            self._scan_values()

            #wait
            time.sleep(self._scan_interval)
