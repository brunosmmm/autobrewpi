from input.keypad import Keypad

class NumKeyWrapper(Keypad):

    _KEYMAP = {
        0 : {
            0 : '1',
            1 : '2',
            2 : '3'
        },
        1 : {
            0 : '4',
            1 : '5',
            2 : '6'
        },
        2 : {
            0 : '7',
            1 : '8',
            2 : '9'
        },
        3 : {
            0 : '*',
            1 : '0',
            2 : '#'
        }
    }

    def __init__(self, col_pins, row_pins, mcp_object):

        if len(col_pins) != 3 or len(row_pins) != 4:
            raise IOError('invalid pin count')

        super(NumKeyWrapper, self).__init__(col_num=3,
                                            row_num=4,
                                            get_cols=self._get_col_state,
                                            set_rows=self._set_row_state)

        self._colpins = col_pins
        self._rowpins = row_pins
        self._ioexp = mcp_object

        #configure pins
        for pin in col_pins:
            self._ioexp.set_direction(pin, 'input')

        for pin in row_pins:
            self._ioexp.set_direction(pin, 'output')

        self.register_keypress_cb(self._keypress)
        self.register_keyrelease_cb(self._keyrelease)

    def _get_col_state(self):
        #easier to get all pins
        pin_states = self._ioexp.read_pins()

        for pin in self._colpins:
            if pin_states[pin]:
                return self._colpins.index(pin)

        return None

    def _set_row_state(self, active_row):

        pin_states = []

        #for i in range(0, 16):
        #    if i not in self._rowpins:
        #        pin_states.append(None)
        #        continue
        #
        #    if i == active_row:
        #        pin_states.append(True)
        #    else:
        #        pin_states.append(False)
        for i in range(0, 16):
            pin_states.append(None)

        for i in range(0, len(self._rowpins)):
            if i == active_row:
                pin_states[self._rowpins[i]] = True
            else:
                pin_states[self._rowpins[i]] = False

        self._ioexp.write_pins(pin_states)

    def _keypress(self, key):
        print 'key press: {}'.format(self._KEYMAP[key[0]][key[1]])

    def _keyrelease(self, key):
        print 'key release: {}'.format(self._KEYMAP[key[0]][key[1]])
