from vspace import VSpaceDriver, VSpaceOutput, VSpaceInput
import json
import re
import logging

_PORT_REGEX = re.compile(r'([a-zA-Z0-9]+)\.([a-zA-Z0-9]+)')

class MashController(VSpaceDriver):

    _inputs = {
        'HLTTemp': VSpaceInput('TEMPERATURE'),
        'MLTTemp': VSpaceInput('TEMPERATURE')
    }

    _outputs = {
        'HLTCtlEnable': VSpaceOutput('BOOLEAN'),
        'HLTCtlSetPoint': VSpaceOutput('TEMPERATURE'),
        'HLTCtlHystLevel': VSpaceOutput('TEMPERATURE'),
        'HLTCtlHystType': VSpaceOutput('GENERIC')
    }

    def __init__(self, **kwargs):
        super(MashController, self).__init__(**kwargs)

        self.logger = logging.getLogger('AutoBrew.mashctl')

        #load persistent data
        try:
            with open('brewday/mashconfig.json', 'r') as f:
                self._mash_config = json.load(f)
        except IOError:
            raise

        #make connections if configuration present
        for port_name, connect_to in self._mash_config['connections'].iteritems():
            if connect_to is None:
                continue

            #parse connection port
            m = re.match(_PORT_REGEX, port_name)

            if m is None:
                self.logger.warning('invalid port name in mashctl configuration: {}'.format(port_name))
                continue

            if port_name in self._inputs:
                #find port
                try:
                    connect_to_id = self._gvarspace.find_port_id(m.group(1), m.group(2), 'output')
                except ValueError:
                    self.logger.warning('could not find port {} or instance {}'.format(m.group(2), m.group(1)))
                    continue
                self._gvarspace.connect_pspace_ports(connect_to_id, self._inputs[port_name].get_global_port_id())

            elif port_name in self._outputs:
                #find port
                try:
                    connect_to_id = self._gvarspace.find_port_id(m.group(1), m.group(2), 'input')
                except ValueError:
                    self.logger.warning('could not find port {} or instance {}'.format(m.group(2), m.group(1)))
                    continue
                self._gvarspace.connect_pspace_ports(self._inputs[port_name].get_global_port_id(), connect_to_id)
            else:
                self.logger.warning('unknown mashctl port: {}'.format(port_name))
                continue

    def cycle(self):
        pass

    def save_configuration(self):

        try:
            with open('brewday/mashconfig.json', 'w') as f:
                json.dump(self._mash_config, f)
        except IOError:
            raise
