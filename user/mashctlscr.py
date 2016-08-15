from ui.screen import Screen
from ui.button import Button
from ui.label import Label
from ui.box import Box

class ABMashScreen(Screen):

    _foot_btn_height = 10

    def __init__(self, **kwargs):
        if 'varspace' in kwargs:
            self._varspace = kwargs.pop('varspace')
        else:
            self._varspace = None
        super(ABMashScreen, self).__init__(x=0, y=0, w=240, h=64, **kwargs)

        #upper 'title'
        self._mashctltitle = Button(text='Mash Ctl',
                                    font='8x8',
                                    x=0,
                                    y=0,
                                    w=239,
                                    h=10)

        #lower buttons
        self._footb_l = Button(text='', font='8x8', x=0, y=self.h-self._foot_btn_height-1, w=self.w/4-1, h=self._foot_btn_height)
        self._footb_ml = Button(text='Inicia', font='8x8', x=self.w/4, y=self.h-self._foot_btn_height-1, w=self.w/4-1, h=self._foot_btn_height)
        self._footb_mr = Button(text='Config', font='8x8', x=self.w/2, y=self.h-self._foot_btn_height-1, w=self.w/4-1, h=self._foot_btn_height)
        self._footb_r = Button(text='Sair', font='8x8', x=3*self.w/4, y=self.h-self._foot_btn_height-1, w=self.w/4-1, h=self._foot_btn_height)

        self._state_label = Label(text='STATE', font='5x12',
                                  y=self._mashctltitle.y+self._mashctltitle.h+3,
                                  x=2)

        self._box_l = Box(x=0,
                          y=self._mashctltitle.y+self._mashctltitle.h+1,
                          w=self.w/2 - 1,
                          h=self.h - self._foot_btn_height - self._mashctltitle.h - 3)
        self._box_r = Box(x=self.w/2,
                          y=self._mashctltitle.y+self._mashctltitle.h+1,
                          w=self.w/2 - 1,
                          h=self.h - self._foot_btn_height - self._mashctltitle.h - 3)

        #in box R, show current values
        self._hlt_temp_label = Label(text='HLT_TEMP', font='5x12',
                                     y=self._mashctltitle.y+self._mashctltitle.h+3,
                                     x=self.w/2 + 2)
        self._mlt_temp_label = Label(text='MLT_TEMP', font='5x12',
                                     y=self._mashctltitle.y+self._mashctltitle.h+17,
                                     x=self.w/2 + 2)

        #add stuff
        self.add_element(self._mashctltitle)
        self.add_element(self._footb_l)
        self.add_element(self._footb_ml)
        self.add_element(self._footb_mr)
        self.add_element(self._footb_r)
        self.add_element(self._state_label)
        self.add_element(self._box_l)
        self.add_element(self._box_r)

        self.add_element(self._hlt_temp_label)
        self.add_element(self._mlt_temp_label)

        #track manual mode
        self._manual = False

        #local state tracking
        self._state = 'idle'

        #find mash controller instance
        self.ctl_inst = self._varspace.find_driver_by_classname('MashController')[0]

        #recurrent call
        self._upd_call_id = None

    @staticmethod
    def _composite_label_text(label, value, max_len):
        label_fill = max_len - len(value)

        if label_fill - len(label) < 0:
            raise IOError('text is too long')

        ret = '{label: <{fill_len}}'.format(label=label, fill_len=label_fill)+value
        return ret

    def _screen_added(self, **kwargs):
        super(ABMashScreen, self)._screen_added(**kwargs)
        #enter idle
        self._enter_idle()
        #update NOW
        self.update_screen()

    def _enter_active(self):
        #change layout
        self._footb_r.set_text('Parar')
        self._state_label.set_text(self._composite_label_text('Estado', 'ativo', 23))
        self._state = 'active'

    def _enter_idle(self):
        self._footb_r.set_text('Sair')
        self._state_label.set_text(self._composite_label_text('Estado', 'ocioso', 23))
        self._state = 'idle'

    def _input_event(self, evt):
        if evt['event'] == 'switches.release':
            if evt['data'] == '3':
                if self._state == 'idle':
                    self._parent.activate_screen('main')

        elif evt['event'] == 'mode.change':
            if evt['data'] == 'manual':
                self._manual = True
            elif evt['data'] == 'normal':
                self._manual = False

    def _screen_activated(self, **kwargs):
        super(ABMashScreen, self)._screen_activated(**kwargs)

        #install recurrent call
        self._upd_call_id = self._parent.add_recurrent_call(self.update_screen, 1)

    def _screen_deactivated(self, **kwargs):
        super(ABMashScreen, self)._screen_deactivated(**kwargs)

        #remove recurrent call
        if self._upd_call_id is not None:
            self._parent.remove_recurrent_call(self._upd_call_id)
            self._upd_call_id = None

    def update_screen(self):
        #update to current values
        hlt_temp = self._varspace.call_driver_method(self.ctl_inst, 'get_hlt_temp')
        mlt_temp = self._varspace.call_driver_method(self.ctl_inst, 'get_mlt_temp')
        self._hlt_temp_label.set_text(self._composite_label_text('HLT Temp',
                                                                 '{} C'.format(hlt_temp)
                                                                 ,23))
        self._mlt_temp_label.set_text(self._composite_label_text('MLT Temp',
                                                                 '{} C'.format(mlt_temp)
                                                                 ,23))
