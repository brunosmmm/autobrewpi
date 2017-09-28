from abpi.vspace import VSpaceOutput, VSpaceInput, rpccallable
from abpi.brewday.controller import BrewdayController, _test_type
from datetime import datetime, timedelta
import os.path

SYS_CONFIG_DIR = '/etc/autobrew/brewday'


class BoilController(BrewdayController):

    _inputs = {
        'BKTemp': VSpaceInput('TEMPERATURE'),
        'GPanic': VSpaceInput('BOOLEAN')
    }

    _outputs = {
        'BKCtlEnable': VSpaceOutput('BOOLEAN'),
        'BKCtlSetPoint': VSpaceOutput('TEMPERATURE'),
        'BoilLock': VSpaceOutput('BOOLEAN')
    }

    def __init__(self, **kwargs):
        if os.path.isfile('config/brewday/boilconfig.json'):
            kwargs['config_file'] = 'config/brewday/boilconfig.json'
        elif os.path.isfile(os.path.join(SYS_CONFIG_DIR, 'boilconfig.json')):
            kwargs['config_file'] = os.path.join(SYS_CONFIG_DIR,
                                                 'boilconfig.json')
        else:
            raise IOError('cannot find boil configuration file')
        super(BoilController, self).__init__(**kwargs)

        self._boil_start_timer = None
        self._boil_timer_duration = None

    @rpccallable
    def get_state(self):
        return self._state

    def start_boil(self):
        self.enter_preheat()

    def stop_boil(self):
        self.enter_idle()

    def reset(self):
        self.enter_idle()

    @rpccallable
    def get_bk_temp(self):
        return self.__BKTemp

    @rpccallable
    def get_boil_duration(self):
        return self._config['boil_duration']

    def get_timer_end(self):
        if self._state == 'boil':
            return self._boil_start_timer + self._boil_timer_duration
        else:
            return None

    @rpccallable
    def set_boil_duration(self, value):
        _test_type(int, value)
        self._config['boil_duration'] = value

    def default_configuration(self):
        self.__BKCtlSetPoint = 0

    def enter_idle(self):
        self.log_info('entering idle state')
        self._state = 'idle'
        self.__BKCtlEnable = False

    def enter_preheat(self):
        # use a high setpoint to ensure boil
        self.__BKCtlSetPoint = 120
        self.__BKCtlEnable = True
        self.log_info('starting boil')
        self._state = 'preheat'

    def enter_boil(self):
        boil_duration = self._config['boil_duration']
        self._boil_start_timer = datetime.now()
        self._boil_timer_duration = timedelta(minutes=int(boil_duration))
        self._state = 'boil'

    def shutdown(self):
        self.enter_idle()

    def cycle(self):

        if self._state in ('idle', 'inactive'):
            pass
        elif self._state == 'preheat':
            boil_thresh = self._config['boil_thresh']
            if self._target_reached(float(boil_thresh),
                                    self.__BKTemp,
                                    2.0):
                self.log_info('boil threshold reached')
                self.enter_boil()
        elif self._state == 'boil':
            if self._boil_start_timer + self._boil_timer_duration <\
               datetime.now():
                # stop boil
                self.log_info('boil done')
                self.enter_idle()
        else:
            self._state = 'idle'
