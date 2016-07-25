from util.thread import StoppableThread
import time

class Keypad(StoppableThread):
    def __init__(self, col_num, row_num, get_cols, set_rows, cycle_interval=0.02):
        super(Keypad, self).__init__()

        self._interval = cycle_interval
        self._coln = col_num
        self._rown = row_num
        self._getcols = get_cols
        self._setrows = set_rows

        #allow only one key pressed at a time
        self._active_key = None

        #scanning
        self._active_row = 0

        #callbacks
        self._presscb = None
        self._releasecb = None

        #state
        self._rowstates = []
        for i in range(0, row_num):
            self._rowstates.append(None)

    def get_active_key(self):
        return self._active_key

    def register_keypress_cb(self, callback):
        self._presscb = callback

    def register_keyrelease_cb(self, callback):
        self._releasecb = callback

    def _key_detected(self, row, col):
        if self._active_key is None:
            self._active_key = [row, col]
            if self._presscb is not None:
                self._presscb([row, col])
        else:
            #key already pressed, so ignore
            pass

    def run(self):

        while True:

            if self.is_stopped():
                exit(0)

            #set some row to an active state
            if self._setrows is not None:
                self._setrows(self._active_row)

            #read columns
            time.sleep(0.1) # wait

            col_state = None
            if self._getcols:
                col_state = self._getcols()

            if col_state is not None:
                #key detected
                self._key_detected(self._active_row, col_state)

            #save row state
            self._rowstates[self._active_row] = col_state

            #trigger a release if necessary
            trigger_release = True
            if self._active_row == 0:
                if self._active_key is not None:
                    for state in self._rowstates:
                        if state is not None:
                            trigger_release = False
                else:
                    trigger_release = False
            else:
                trigger_release = False

            if trigger_release:
                if self._releasecb is not None:
                    self._releasecb(self._active_key)
                self._active_key = None

            #next row
            self._active_row += 1
            if self._active_row == self._rown:
                self._active_row = 0

            time.sleep(self._interval)
