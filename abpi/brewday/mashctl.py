from abpi.vspace import VSpaceOutput, VSpaceInput, rpccallable
from abpi.brewday.controller import BrewdayController, _test_type
import logging
from datetime import datetime, timedelta
import os.path

SYS_CONFIG_DIR = '/etc/autobrew/brewday'


class MashController(BrewdayController):

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
        'PumpCtl': VSpaceOutput('BOOLEAN'),
        'MashLock': VSpaceOutput('BOOLEAN')
    }

    def __init__(self, **kwargs):
        if os.path.isfile('config/brewday/mashconfig.json'):
            kwargs['config_file'] = 'config/brewday/mashconfig.json'
        elif os.path.isfile(os.path.join(SYS_CONFIG_DIR, 'mashconfig.json')):
            kwargs['config_file'] = os.path.join(SYS_CONFIG_DIR,
                                                 'mashconfig.json')
        else:
            raise IOError('cannot find mash configuration file')
        super(MashController, self).__init__(**kwargs)

        self.logger = logging.getLogger('AutoBrew.mashctl')

        self._state = 'idle'
        self._mash_stage = -1
        self._pause_transfer = False
        self._state_start_timer = None
        self._state_timer_duration = None
        self._pause_all = False
        self._saved_state = None
        self._pump_state = False

    def post_init(self):
        # self.connect_ports()
        pass

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
        super(MashController, self).update_local_variable(variable_name,
                                                          new_value)

        if variable_name == 'ManualPump':
            if (self._pump_on or self.__ManualPump) != self.__PumpCtl:
                self.__PumpCtl = self._pump_on or self.__ManualPump

        if self.__GPanic:
            # pause
            self.pause_all()
        else:
            self.unpause_all()

    @rpccallable
    def get_state(self):
        return self._state

    def stop_mash(self):
        self.enter_idle()

    def reset(self):
        self._mash_stage = -1
        self.enter_idle()

    @rpccallable
    def get_hlt_temp(self):
        return self.__HLTTemp

    @rpccallable
    def get_mlt_temp(self):
        return self.__MLTTemp

    @rpccallable
    def get_mash_steps(self):
        return self._config['mash_stages']

    @rpccallable
    def get_hyst_level(self):
        return self._config['hystctl']['level']

    @rpccallable
    def set_hyst_level(self, value):
        _test_type(float, value)
        self._config['hystctl']['level'] = value

        if self.__HLTCtlEnable:
            self.__HLTCtlEnable = False
            self.__HLTCtlHystLevel = value
            self.__HLTCtlEnable = True
        else:
            self.__HLTCtlHystLevel = value


    def default_configuration(self):
        self.set_output_value('HLTCtlSetPoint', 0)
        self.set_output_value('HLTCtlHystLevel',
                              float(self._config['hystctl']['level']))
        self.set_output_value('HLTCtlHystType',
                              self._config['hystctl']['type'])

    def enter_idle(self):
        self.log_info('entering idle state')
        self._pump_on = False
        self.set_output_value('HLTCtlEnable', False)
        self._state = 'idle'

    def enter_preheat(self):
        target_temp = float(self._config['mash_stages'][self._mash_stage]['target_temp'])
        self.log_info('entering preheat state')
        self.__HLTCtlEnable = False
        self.__HLTCtlSetPoint = target_temp
        self.__HLTCtlEnable = True
        self._state = 'preheat'

    def next_stage(self):
        if self._mash_stage < len(self._config['mash_stages']) - 1:
            self._mash_stage += 1
            stage_type = self._config['mash_stages'][self._mash_stage]['type']

            if stage_type == 'water_in':
                self.enter_idle()
            elif stage_type == 'preheat':
                self.enter_preheat()
            elif stage_type == 'conversion':
                self.enter_mash()
            elif stage_type == 'mashout':
                self.enter_mashout()
            elif stage_type in ('fly_sparge', 'batch_sparge', 'sparge'):
                self.enter_sparge_wait()
            elif stage_type == 'water_transfer':
                self.enter_transfer()
            elif stage_type == 'add_items':
                self._state = 'add_items'
            else:
                self.log_err('illegal mash step: "{}"'
                             ', aborting'.format(stage_type))
                self.reset()
        else:
            # finished
            self.reset()

    def get_next_stage_data(self):
        if self._mash_stage < len(self._config['mash_stages']) - 1:
            return self._config['mash_stages'][self._mash_stage + 1]
        else:
            return None

    def get_current_stage_data(self):
        if self._mash_stage > -1:
            return self._config['mash_stages'][self._mash_stage]
        else:
            return None

    def set_mash_stages(self, stage_data):
        self._config['mash_stages'] = stage_data

    def enter_transfer(self):
        self.logger.debug('entering transfer state')
        if self._config['mash_stages'][self._mash_stage]['use_pump']:
            self._pump_on = True
        self._state = 'transfer_hlt_mlt'

    def pause_transfer(self):
        self._pause_transfer = True
        self._pump_on = False

    def unpause_transfer(self):
        self._pause_transfer = False
        if self._config['mash_stages'][self._mash_stage]['use_pump']:
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

    def enter_mash(self):
        mash_target = self._config['mash_stages'][self._mash_stage]['target_temp']
        mash_duration = self._config['mash_stages'][self._mash_stage]['time']
        self.log_info('Starting recirculating mash')
        self._state_start_timer = datetime.now()
        self._state_timer_duration = timedelta(minutes=int(mash_duration))
        # update setpoint
        self.__HLTCtlEnable = False
        self.__HLTCtlSetPoint = float(mash_target)
        self.__HLTCtlEnable = True
        if self._config['mash_stages'][self._mash_stage]['use_pump']:
            self._pump_on = True
        self._state = 'mash'

    def enter_mashout(self):
        mashout_dur = self._config['mash_stages'][self._mash_stage]['time']
        mashout_target = self._config['mash_stages'][self._mash_stage]['target_temp']
        self.log_info('Starting mashout now')
        self._state_start_timer = datetime.now()
        self._state_timer_duration = timedelta(minutes=int(mashout_dur))
        # update setpoint
        self.__HLTCtlEnable = False
        self.__HLTCtlSetPoint = float(mashout_target)
        self.__HLTCtlEnable = True
        if self._config['mash_stages'][self._mash_stage]['use_pump']:
            self._pump_on = True
        self._state = 'mashout'

    def enter_sparge_wait(self):
        self.log_info('Entering sparge wait state')
        # disable heating element
        self.__HLTCtlEnable = False
        self._pump_on = False
        self._state = 'sparge_wait'

    def enter_sparge(self):
        sparge_dur = self._config['mash_stages'][self._mash_stage]['time']
        target_temp = self._config['mash_stages'][self._mash_stage]['target_temp']
        self.log_info('Starting sparge phase')
        if self._config['mash_stages'][self._mash_stage]['use_pump']:
            self._pump_on = True
        self.__HLTCtlEnable = False
        self.__HLTCtlSetPoint = float(target_temp)
        self.__HLTCtlEnable = True
        self._state_start_timer = datetime.now()
        self._state_timer_duration = timedelta(minutes=int(sparge_dur))
        self._state = 'sparge'

    @staticmethod
    def _to_seconds(minutes, seconds):
        return minutes*60 + seconds

    def get_timer_end(self):
        if self._state in ('mash', 'mashout', 'sparge'):
            return self._state_start_timer + self._state_timer_duration

        return None

    def shutdown(self):
        self.enter_idle()

    def cycle(self):

        if self._state in ('idle', 'inactive'):
            pass
        elif self._state == 'preheat':
            mash_target = self._config['mash_stages'][self._mash_stage]['target_temp']
            if self._target_reached(float(mash_target),
                                    self.__HLTTemp,
                                    self._config['misc']['temp_error']):
                self.log_info('Preheat done')
                self._state = 'preheat_done'
        elif self._state == 'preheat_done':
            # wait
            pass
        elif self._state == 'transfer_hlt_mlt':
            pass
        elif self._state == 'add_items':
            pass
        elif self._state == 'mash':
            if self._state_start_timer + self._state_timer_duration <\
               datetime.now():
                # timer reached
                self.log_info('Mash stage finished')
                self._pump_on = False
                self.next_stage()
        elif self._state == 'mashout':
            if self._state_start_timer + self._state_timer_duration <\
               datetime.now():
                self.log_info('Mashout finished')
                self.next_stage()
        elif self._state == 'sparge_wait':
                pass
        elif self._state == 'sparge':
            if self._state_start_timer + self._state_timer_duration <\
               datetime.now():
                self.log_info('Sparge finished')
                self.next_stage()
        elif self._state == 'paused':
            if self._state_start_timer is not None:
                pass
        else:
            self._state = 'idle'
