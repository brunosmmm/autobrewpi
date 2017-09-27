from abpi.vspace import VSpaceDriver, VSpaceInput
import numpy
from datetime import datetime


class DataLogger(VSpaceDriver):

    _inputs = {
        'DataInput1': VSpaceInput('GENERIC'),
        'DataInput2': VSpaceInput('GENERIC'),
        'DataInput3': VSpaceInput('GENERIC'),
        'DataInput4': VSpaceInput('GENERIC'),
        'DataInput5': VSpaceInput('GENERIC'),
        'DataInput6': VSpaceInput('GENERIC'),
        'DataInput7': VSpaceInput('GENERIC'),
        'DataInput8': VSpaceInput('GENERIC')
    }

    def __init__(self, **kwargs):
        super(DataLogger, self).__init__(**kwargs)

        self._datasets = {}

    def port_connected(self, port_id, connected_to_id):
        super(DataLogger, self).port_connected(port_id, connected_to_id)

        port_info = self._gvarspace.get_port_info(connected_to_id)
        self._datasets[self._gvarspace.get_port_info(port_id)['portname']] = {
            'ydata': numpy.zeros([1, ]),
            'xdata': numpy.zeros([1, ], dtype='datetime64'),
            'source': '{}.{}'.format(port_info['instname'],
                                     port_info['portname'])
        }

        self.log_info('now logging value of '
                      '"{}.{}"'.format(port_info['instname'],
                                       port_info['portname']))

    def update_local_variable(self, variable_name, new_value):
        super(DataLogger, self).update_local_variable(variable_name, new_value)

        numpy.append(self._datasets[variable_name]['ydata'], new_value)
        numpy.append(self._datasets[variable_name]['xdata'],
                     numpy.datetime64(datetime.now()))
