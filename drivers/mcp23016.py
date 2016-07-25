import smbus
from util.thread import StoppableThread
from collections import deque
import time

# pins: GP0 -> 0..7; GP1 -> 8..15
# TODO: support interrupt configuration & usage, add callbacks

class MCP23016(object):

    _MAXIMUM_RETRIES = 100
    _REGISTER_NAMES = {
        'GP0': 0x00,
        'GP1': 0x01,
        'OLAT0': 0x02,
        'OLAT1': 0x03,
        'IPOL0': 0x04,
        'IPOL1': 0x05,
        'IODIR0': 0x06,
        'IODIR1': 0x07,
        'INTCAP0': 0x08,
        'INTCAP1': 0x09,
        'IOCON0': 0x0A
    }

    def __init__(self, *args, **kwargs):
        if 'i2c_bus' in kwargs:
            self._busnum = kwargs.pop('i2c_bus')
        else:
            self._busnum = 0
        if 'address' in kwargs:
            self._addr = kwargs.pop('address')
        else:
            self._addr = 0x20
        if 'fast' in kwargs:
            fast = kwargs.pop('fast')
        else:
            fast = True
        super(MCP23016, self).__init__(*args, **kwargs)
        self._bus = smbus.SMBus(self._busnum)

        self._GP0VAL = 0x00
        self._GP1VAL = 0x00

        if fast:
            self._write_register('IOCON0', 0x01)

    def _read_register(self, reg_num):
        if isinstance(reg_num, str):
            reg_num = self._REGISTER_NAMES[reg_num]

        data = None
        retry_count = 0
        while data is None and retry_count < self._MAXIMUM_RETRIES:
            try:
                data = self._bus.read_byte_data(self._addr, reg_num)
            except IOError:
                time.sleep(0.01)
                retry_count += 1

        if data is None:
            raise IOError('error reading register')

        return data

    def _write_register(self, reg_num, value):
        if isinstance(reg_num, str):
            reg_num = self._REGISTER_NAMES[reg_num]

        retry_count = 0
        done = False
        while done is False and retry_count < self._MAXIMUM_RETRIES:
            try:
                self._bus.write_byte_data(self._addr, reg_num, value)
                done = True
            except IOError:
                time.sleep(0.01)
                retry_count += 1

        if done is False:
            raise IOError('error writing to register')

    def _set_input(self, pin_num):

        if pin_num > -1 and pin_num < 8:
            current_config = self._read_register('IODIR0')
            current_config |= (1<<pin_num)
            self._write_register('IODIR0', current_config)
        elif pin_num > 7 and pin_num < 16:
            current_config = self._read_register('IODIR1')
            current_config |= (1<<(pin_num-8))
            self._write_register('IODIR1', current_config)
        else:
            raise IOError('invalid pin number')

    def _set_output(self, pin_num):

        if pin_num > -1 and pin_num < 8:
            current_config = self._read_register('IODIR0')
            current_config &= ~(1<<pin_num)
            self._write_register('IODIR0', current_config)
        elif pin_num < 16:
            current_config = self._read_register('IODIR1')
            current_config &= ~(1<<(pin_num-8))
            self._write_register('IODIR1', current_config)
        else:
            raise IOError('invalid pin number')

    def set_direction(self, pin_num, direction):

        if direction == 'output':
            self._set_output(pin_num)
        elif direction == 'input':
            self._set_input(pin_num)
        else:
            raise ValueError('direction must be either "input" or "output"')

    def _read_pins(self):
        self._GP0VAL = self._read_register('GP0')
        self._GP1VAL = self._read_register('GP1')

    def read_pin(self, pin_num, refresh=False):
        if refresh is True:
            self._read_pins()

        if pin_num > -1 and pin_num < 8:
            if self._GP0VAL & (1<<pin_num):
                return True
            else:
                return False

        elif pin_num > 7 and pin_num < 16:
            if self._GP1VAL & (1<<(pin_num-8)):
                return True
            else:
                return False

        else:
            raise IOError('invalid pin number')

    def _byte_to_bool_list(self, byte):
        bool_list = []
        for i in range(0, 8):
            if byte & (1<<i):
                bool_list.append(True)
            else:
                bool_list.append(False)

        return bool_list

    def read_pins(self, refresh=False):

        if refresh is True:
            self._read_pins()

        bool_list = self._byte_to_bool_list(self._GP0VAL)
        bool_list.extend(self._byte_to_bool_list(self._GP1VAL))

        return bool_list


    def write_pin(self, pin_num, value):

        if pin_num > -1 and pin_num < 8:
            current_config = self._read_register('GP0')
            if value:
                current_config |= (1<<pin_num)
            else:
                current_config &= ~(1<<pin_num)
            self._write_register('GP0', current_config)
        elif pin_num > 7 and pin_num < 16:
            current_config = self._read_register('GP1')
            if value:
                current_config |= (1<<(pin_num-8))
            else:
                current_config &= ~(1<<(pin_num-8))
            self._write_register('GP1', current_config)
        else:
            raise IOError('invalid pin number')

    def write_pins(self, value_list):

        if len(value_list) != 16:
            raise IOError('invalid pin count in list')

        #update values
        self._read_pins()

        #values to be modified
        curr_gp0 = self._GP0VAL
        curr_gp1 = self._GP1VAL

        #new values (input)
        values_0 = value_list[:8]
        values_1 = value_list[8:]

        #gp0
        for i in range(0, 8):
            if values_0[i] is None:
                continue

            if values_0[i]:
                curr_gp0 |= (1<<i)
            else:
                curr_gp0 &= ~(1<<i)

        #gp1
        for i in range(0, 8):
            if values_1[i] is None:
                continue

            if values_1[i]:
                curr_gp1 |= (1<<i)
            else:
                curr_gp1 &= ~(1<<i)

        #set values
        self._write_register('GP0', curr_gp0)
        self._write_register('GP1', curr_gp1)


class MCP23016Auto(MCP23016, StoppableThread):
    def __init__(self, *args, **kwargs):
        if 'cycle_interval' in kwargs:
            self._interval = kwargs.pop('cycle_interval')
        else:
            self._interval = 0.01
        super(MCP23016Auto, self).__init__(*args, **kwargs)

        self._io_queue = deque()
        self._outdated = False

    def read_pins(self):
        return super(MCP23016Auto, self).read_pins(refresh=False)

    def read_pin(self, pin_num):
        return super(MCP23016Auto, self).read_pin(pin_num, refresh=False)

    def get_flags(self):
        return {'outdated': self._outdated}

    def read_pin_async(self, pin_num, callback=None):
        self._io_queue.appendleft({
            'request_kind': 'read_async',
            'params': {
                'pin_num' : pin_num,
                'callback': callback
            }
        })

    def run(self):
        while True:

            if self.is_stopped():
                exit(0)

            #refresh state
            while len(self._io_queue) > 0:
                req = self._io_queue.pop()

                try:
                    if req['request_kind'] == 'set_direction':
                        super(MCP23016Auto, self).set_direction(req['params']['pin_num'], req['params']['direction'])
                    elif req['request_kind'] == 'set_value':
                        super(MCP23016Auto, self).write_pin(req['params']['pin_num', req['params']['value']])
                    elif req['request_kind'] == 'read_async':
                        value = super(MCP23016Auto, self).read_pin(req['params']['pin_num'], refresh=True)
                        if req['params']['callback'] is not None:
                            req['params']['callback'](value)

                    elif req['request_kind'] == 'set_values':
                        super(MCP23016Auto, self).write_pins(req['params']['values'])
                except (IOError, ValueError):
                    pass

            #always read to refresh values
            try:
                self._read_pins()
                self._outdated = False
            except (IOError, ValueError):
                self._outdated = True

            time.sleep(self._interval)

    def _check_pin_num(self, pin_num):
        if pin_num > -1 and pin_num < 16:
            return

        raise IOError('invalid pin number')

    def set_direction(self, pin_num, direction):

        if direction not in ('output', 'input'):
            raise ValueError('direction must be either "input" or "output"')

        self._check_pin_num(pin_num)

        self._io_queue.appendleft({
            'request_kind': 'set_direction',
            'params': {
                'direction': direction,
                'pin_num': pin_num
            }
        })

    def write_pin(self, pin_num, value):

        self._check_pin_num(pin_num)

        self._io_queue.appendleft({
            'request_kind': 'set_value',
            'params': {
                'value': value,
                'pin_num': pin_num
            }
        })

    def write_pins(self, value_list):

        self._io_queue.appendleft({
            'request_kind': 'set_values',
            'params': {
                'values': value_list
            }
        })
