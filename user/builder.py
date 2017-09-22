import importlib
import json
from collections import OrderedDict


class SystemBuilder(object):
    def __init__(self, config_file, gadget_vspace):

        self._gvspace = gadget_vspace

        try:
            with open(config_file, 'r') as f:
                config_contents = json.load(f, object_pairs_hook=OrderedDict)
        except IOError:
            raise IOError('could not open configuration file')

        # parse configuration

        # load drivers
        for (instance_name,
             driver_type) in config_contents['driver_instances'].items():
            try:
                # try to load class
                driver_class = config_contents['driver_classes'][driver_type]
                m = importlib.import_module(driver_class)
                c = getattr(m, driver_type)
                self._gvspace.register_driver(c, instance_name)
            except Exception:
                raise

        # make hardwired connections
        for connection in config_contents['required_connections']:
            port_from = self._gvspace.find_port_id(connection['port_from']['instance_name'],
                                                   connection['port_from']['port_name'],
                                                   connection['port_from']['port_direction'])
            port_to = self._gvspace.find_port_id(connection['port_to']['instance_name'],
                                                 connection['port_to']['port_name'],
                                                 connection['port_to']['port_direction'])
            self._gvspace.connect_pspace_ports(port_from, port_to)
