from vspace import VSpaceDriver, VSpaceInput, VSpaceOutput
import numpy
from scipy import interpolate
import json
import os


class Pt100Table(VSpaceDriver):

    _inputs = {
        'Resistance': VSpaceInput('FLOAT')
    }

    _outputs = {
        'Temperature': VSpaceOutput('TEMPERATURE', 0.0)
    }

    def __init__(self, **kwargs):
        super(Pt100Table, self).__init__(**kwargs)

        try:
            with open('config/drivers/pt100.json', 'r') as f:
                config = json.load(f)

            self._table = numpy.unique(numpy.loadtxt(os.path.join(os.getcwd(),
                                                                  'data',
                                                                  'drivers',
                                                                  config['value_file']),
                                                     delimiter=',').flatten())
            self._start_temp = float(config['begins_at'])
        except IOError as e:
            raise
            self.log_err('could not load configuration or data file: {}'.format(e.message))
            self._table = None
            self._start_temp = None

    def update_local_variable(self, *args, **kwargs):
        super(Pt100Table, self).update_local_variable(*args, **kwargs)

        if self._table is None:
            return

        try:
            original_xs = numpy.arange(self._start_temp, self._start_temp+len(self._table))
            interp_data = interpolate.interp1d(self._table, original_xs)
            #new_xs = numpy.arange(self._start_temp, self._start_temp+len(self._table), 0.01)
            curr_res = self.__Resistance

            self.__Temperature = numpy.around(interp_data(curr_res), 2)
        except Exception as e:
            self.log_err('could not calculate temperature: {}'.format(e.message))
