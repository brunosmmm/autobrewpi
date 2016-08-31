from vspace import VSpaceDriver, VSpaceOutput, VSpaceInput, rpccallable


class GadgetWatcher(VSpaceDriver):

    _GADGET_FLAG_PANIC = 0x80
    _GADGET_FLAG_STOP = 0x40
    _GADGET_FLAG_PWDN = 0x20

    _GADGET_CMD_PANIC = 0x03
    _GADGET_CMD_STOP = 0x02
    _GADGET_CMD_LIFT_PANIC = 0x01
    _GADGET_CMD_CPUOFF = 0x04
    _GADGET_CMD_CPUON = 0x05

    _inputs = {
        'GadgetState': VSpaceInput('BYTE')
    }

    _outputs = {
        'GadgetControl': VSpaceOutput('GENERIC'),
        'GadgetPanic': VSpaceOutput('BOOLEAN', False)
    }

    def __init__(self, **kwargs):
        super(GadgetWatcher, self).__init__(**kwargs)

        self._waiting_first_update = True

    @rpccallable
    def is_panic(self):
        return self.__GadgetPanic

    def lift_panic(self):
        self.__GadgetControl = self._GADGET_CMD_LIFT_PANIC

    def post_init(self):

        state_port = self._gvarspace.find_port_id('gadget',
                                                  'Gadget_STATE',
                                                  'output')

        control_port = self._gvarspace.find_port_id('gadget',
                                                    'Gadget_CTL',
                                                    'input')

        self._gvarspace.connect_pspace_ports(control_port,
                                             self._outputs['GadgetControl'].get_global_port_id())

        # connect ports
        self._gvarspace.connect_pspace_ports(state_port,
                                             self._inputs['GadgetState'].get_global_port_id())

    def update_local_variable(self, *args, **kwargs):
        super(GadgetWatcher, self).update_local_variable(*args, **kwargs)

        # parse state
        if self._waiting_first_update:
            # reset gadget state on first read
            self.log_info('first update')
            state = self.get_input_value('GadgetState')
            self.log_info('state is: {}'.format(hex(state)))
            if state & self._GADGET_FLAG_PANIC:
                self.set_output_value('GadgetControl',
                                      self._GADGET_CMD_LIFT_PANIC)
            else:
                self.set_output_value('GadgetControl', self._GADGET_CMD_CPUON)
            self._waiting_first_update = False

        state = self.get_input_value('GadgetState')
        if state & self._GADGET_FLAG_PWDN:
            # power down requested
            pass
        if state & self._GADGET_FLAG_PANIC:
            self.__GadgetPanic = True
        else:
            self.__GadgetPanic = False
