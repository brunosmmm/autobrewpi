from vspace import VSpaceDriver
import re
import json

_PORT_REGEX = re.compile(r'([a-zA-Z0-9_]+)\.([a-zA-Z0-9_]+)')


class BrewdayController(VSpaceDriver):

    _inputs = {}
    _outputs = {}

    def __init__(self, **kwargs):
        if 'config_file' in kwargs:
            config_file = kwargs.pop('config_file')
        else:
            config_file = None
        super(BrewdayController, self).__init__(**kwargs)

        if config_file is not None:
            try:
                with open(config_file, 'r') as f:
                    self._config = json.load(f)
            except IOError:
                raise
        else:
            self._config = {}

        self._state = 'inactive'

    def disconnect_ports(self):
        for port_name, port_object in self._inputs.iteritems():
            if port_object.get_connected():
                port_id = port_object.get_global_port_id()

                # discover what is connected to this port
                connects_to = self._gvarspace.get_port_info(port_id)['connected_to']
                for connected_port in connects_to:
                    self._gvarspace.disconnect_pspace_ports(port_id,
                                                            connected_port)
        for port_name, port_object in self._outputs.iteritems():
            if port_object.get_connected():
                port_id = port_object.get_global_port_id()

                # discover what is connected to this port
                connects_to = self._gvarspace.get_port_info(port_id)['connected_to']
                for connected_port in connects_to:
                    self._gvarspace.disconnect_pspace_ports(port_id,
                                                            connected_port)

    def connect_ports(self):
        # make connections if configuration present
        for (port_name,
             connect_to) in self._config['connections'].iteritems():
            if connect_to is None:
                continue

            # parse connection port
            m = re.match(_PORT_REGEX, connect_to)

            if m is None:
                self.log_warn('invalid port name in'
                              ' configuration: {}'.format(port_name))
                continue

            if port_name in self._inputs:
                # find port
                try:
                    connect_to_id = self._gvarspace.find_port_id(m.group(1),
                                                                 m.group(2),
                                                                 'output')
                except ValueError:
                    self.log_warn('could not find port {}'
                                  ' or instance {}'.format(m.group(2),
                                                           m.group(1)))
                    continue
                this_port_id = self._inputs[port_name].get_global_port_id()
                self._gvarspace.connect_pspace_ports(connect_to_id,
                                                     this_port_id)

            elif port_name in self._outputs:
                # find port
                try:
                    connect_to_id = self._gvarspace.find_port_id(m.group(1),
                                                                 m.group(2),
                                                                 'input')
                except ValueError:
                    self.log_warn('could not find port {}'
                                  ' or instance {}'.format(m.group(2),
                                                           m.group(1)))
                    continue
                this_port_id = self._outputs[port_name].get_global_port_id()
                self._gvarspace.connect_pspace_ports(this_port_id,
                                                     connect_to_id)
            else:
                self.log_warn('unknown port: {}'.format(port_name))
                continue

    def activate(self):
        self.connect_ports()
        self.default_configuration()
        self.enter_idle()

    def deactivate(self):
        self.disconnect_ports()
        self._state = 'inactive'

    def enter_idle(self):
        self._state = 'idle'

    def default_configuration(self):
        pass
