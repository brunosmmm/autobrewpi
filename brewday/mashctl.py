from vspace import VSpaceDriver, VSpaceOutput, VSpaceInput, rpccallable
import json
import re
import logging
from datetime import datetime, timedelta

_PORT_REGEX = re.compile(r'([a-zA-Z0-9_]+)\.([a-zA-Z0-9_]+)')

class MashController(VSpaceDriver):

    _inputs = {
        'HLTTemp': VSpaceInput('TEMPERATURE'),
        'MLTTemp': VSpaceInput('TEMPERATURE'),
        'ManualPump': VSpaceInput('BOOLEAN'),
        'GPanic': VSpaceInput('BOOLEAN')
    }

    _outputs = {
        'HLTCtlEnable': VSpaceOutput('BOOLEAN'),
        'HLTCtlSetPoint': VSpaceOutput('TEMPERATURE'),
        'HLTCtlHystLevel': VSpaceOutput('TEMPERATURE'),
        'HLTCtlHystType': VSpaceOutput('GENERIC'),
        'PumpCtl': VSpaceOutput('BOOLEAN')
    }

    def __init__(self, **kwargs):
        super(MashController, self).__init__(**kwargs)

        self.logger = logging.getLogger('AutoBrew.mashctl')

        self._state = 'idle'
        self._pause_transfer = False
        self._state_start_timer = None
        self._state_timer_duration = None
        self._pause_all = False
        self._saved_state = None
        self._pump_state = False

        #load persistent data
        try:
            with open('brewday/mashconfig.json', 'r') as f:
                self._mash_config = json.load(f)
        except IOError:
            raise

    def post_init(self):
        #make connections if configuration present
        for port_name, connect_to in self._mash_config['connections'].iteritems():
            if connect_to is None:
                continue

            #parse connection port
            m = re.match(_PORT_REGEX, connect_to)

            if m is None:
                self.log_warn('invalid port name in mashctl configuration: {}'.format(port_name))
                continue

            if port_name in self._inputs:
                #find port
                try:
                    connect_to_id = self._gvarspace.find_port_id(m.group(1), m.group(2), 'output')
                except ValueError:
                    self.log_warn('could not find port {} or instance {}'.format(m.group(2), m.group(1)))
                    continue
                self._gvarspace.connect_pspace_ports(connect_to_id, self._inputs[port_name].get_global_port_id())

            elif port_name in self._outputs:
                #find port
                try:
                    connect_to_id = self._gvarspace.find_port_id(m.group(1), m.group(2), 'input')
                except ValueError:
                    self.log_warn('could not find port {} or instance {}'.format(m.group(2), m.group(1)))
                    continue
                self._gvarspace.connect_pspace_ports(self._outputs[port_name].get_global_port_id(), connect_to_id)
            else:
                self.log_warn('unknown mashctl port: {}'.format(port_name))
                continue

        self.default_configuration()
        self.enter_idle()

    @property
    def _pump_on(self):
        return self._pump_state

    @_pump_on.setter
    def _pump_on(self, value):
        if value or self.__ManualPump:
            self.__PumpCtl = True
            self._pump_state = True
        else:
            self.__PumpCtl = False
            self._pump_state = False

    def update_local_variable(self, variable_name, new_value):
        super(MashController, self).update_local_variable(variable_name, new_value)

        if variable_name == 'ManualPump':
            if (self._pump_on or self.__ManualPump) != self.__PumpCtl:
                self.__PumpCtl = self._pump_on or self.__ManualPump

        if self.__GPanic:
            #pause
            self.pause_all()
        else:
            self.unpause_all()

    @rpccallable
    def get_state(self):
        return self._state

    def start_mash(self):
        self.enter_preheat()

    def reset(self):
        self.enter_idle()

    @rpccallable
    def get_hlt_temp(self):
        return self.__HLTTemp

    @rpccallable
    def get_mlt_temp(self):
        return self.__MLTTemp

    @rpccallable
    def get_mash_sp(self):
        return self._mash_config['mash_states']['mash']['temp']

    @rpccallable
    def get_mashout_sp(self):
        return self._mash_config['mash_states']['mashout']['temp']

    @rpccallable
    def get_hyst_level(self):
        return self._mash_config['hystctl']['level']

    @rpccallable
    def get_mash_duration(self):
        return self._mash_config['mash_states']['mash']['duration']

    @rpccallable
    def get_mashout_duration(self):
        return self._mash_config['mash_states']['mashout']['duration']

    @rpccallable
    def get_sparge_duration(self):
        return self._mash_config['mash_states']['sparge']['duration']

    @rpccallable
    def set_mash_sp(self, value):
        pass

    @rpccallable
    def set_mashout_sp(self, value):
        pass

    @rpccallable
    def set_hyst_level(self, value):
        pass

    @rpccallable
    def set_mash_duration(self, value):
        pass

    @rpccallable
    def set_mashout_duration(self, value):
        pass

    @rpccallable
    def set_sparge_duration(self, value):
        pass

    def default_configuration(self):
        self.set_output_value('HLTCtlSetPoint', 0)
        self.set_output_value('HLTCtlHystLevel', float(self._mash_config['hystctl']['level']))
        self.set_output_value('HLTCtlHystType', self._mash_config['hystctl']['type'])

    def enter_idle(self):
        self.logger.debug('entering idle state')
        self.set_output_value('PumpCtl', False)
        self.set_output_value('HLTCtlEnable', False)
        self._state = 'idle'

    def enter_preheat(self):
        self.logger.debug('entering preheat state')
        self.set_output_value('HLTCtlSetPoint', float(self._mash_config['mash_states']['mash']['temp']))
        self.set_output_value('HLTCtlEnable', True)
        self._state = 'preheat'

    def enter_transfer(self):
        self.logger.debug('entering transfer state')
        if self._mash_config['misc']['transfer_use_pump']:
            self.set_output_value('PumpCtl', True)
        self._state = 'transfer_hlt_mlt'

    def pause_transfer(self):
        self._pause_transfer = True
        self._pump_on = False

    def unpause_transfer(self):
        self._pause_transfer = False
        self._pump_on = True

    def pause_all(self):
        self._saved_state = {'pump': self.__PumpCtl,
                             'state': self._state}
        self._pump_on = False
        self._state = 'paused'
        self._pause_all = True

    def unpause_all(self):
        if self._pause_all is False:
            return

        if self._saved_state is not None:
            self._pump_on = self._saved_state['pump']
            self._state = self._saved_state['state']

        self._saved_state = None
        self._pause_all = False

    def enter_addgrains(self):
        self.logger.debug('entering add_grains state')
        self.set_output_value('PumpCtl', False)
        self._state = 'add_grains'

    def enter_mash(self):
        self.log_info('Starting recirculating mash')
        self._state_start_timer = datetime.now()
        self._state_timer_duration = timedelta(minutes=int(self._mash_config['mash_states']['mash']['duration']))
        self._pump_on = True
        self._state = 'mash'

    def enter_mashout(self):
        self.log_info('Starting mashout now')
        self._state_start_timer = datetime.now()
        self._state_timer_duration = timedelta(minutes=int(self._mash_config['mash_states']['mashout']['duration']))
        #update setpoint
        self.__HLTCtlEnable = False
        self.__HLTCtlSetPoint = float(self._mash_config['mash_states']['mashout']['temp'])
        self.__HLTCtlEnable = True
        self._pump_on = True
        self._state = 'mashout'

    def enter_sparge_wait(self):
        self.logger.debug('entering sparge_wait state')
        #disable heating element
        self.__HLTCtlEnable = False
        self._pump_on = False
        self._state = 'sparge_wait'

    def enter_sparge(self):
        self.log_info('Starting sparge phase')
        self._pump_on = True
        self._state_start_timer = datetime.now()
        self._state_timer_duration = timedelta(minutes=int(self._mash_config['mash_states']['sparge']['duration']))
        self._state = 'sparge'

    def _target_reached(self, target_temp, current_temp):
        if abs(target_temp - current_temp) <= float(self._mash_config['misc']['temp_error']):
            return True
        return False

    @staticmethod
    def _to_seconds(minutes, seconds):
        return minutes*60 + seconds

    def get_timer_end(self):
        if self._state in ('mash', 'mashout', 'sparge'):
            return self._state_start_timer + self._state_timer_duration

        return None

    def cycle(self):

        if self._state == 'idle':
            pass
        elif self._state == 'preheat':
            if self._target_reached(float(self._mash_config['mash_states']['mash']['temp']), self.__HLTTemp):
                self.log_info('Preheat done')
                self._state = 'preheat_done'
        elif self._state == 'preheat_done':
            #wait
            pass
        elif self._state == 'transfer_hlt_mlt':
            pass
        elif self._state == 'add_grains':
            #wait
            pass
        elif self._state == 'mash':
            if self._state_start_timer + self._state_timer_duration < datetime.now():
                #timer reached
                self.log_info('Mash finished')
                self.enter_mashout()
        elif self._state == 'mashout':
            if self._state_start_timer + self._state_timer_duration < datetime.now():
                self.log_info('Mashout finished')
                self.enter_sparge_wait()
        elif self._state == 'sparge_wait':
                pass
        elif self._state == 'sparge':
            if self._state_start_timer + self._state_timer_duration < datetime.now():
                self.log_info('Mash completed')
                self.enter_idle()
        elif self._state == 'paused':
            if self._state_start_timer is not None:
                pass
        else:
            self._state = 'idle'

    def save_configuration(self):

        try:
            with open('brewday/mashconfig.json', 'w') as f:
                json.dump(self._mash_config, f)
        except IOError:
            raise
