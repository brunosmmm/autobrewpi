from ui.screen import Screen
from ui.button import Button

class ABMainScreen(Screen):

    _foot_btn_height = 10

    def __init__(self, **kwargs):
        super(ABMainScreen, self).__init__(x=0, y=0, w=240, h=64, **kwargs)

        #lower buttons
        self._footb_l = Button(text='1', font='8x8', x=0, y=self.h-self._foot_btn_height-1, w=self.w/4-1, h=self._foot_btn_height)
        self._footb_ml = Button(text='2', font='8x8', x=self.w/4, y=self.h-self._foot_btn_height-1, w=self.w/4-1, h=self._foot_btn_height)
        self._footb_mr = Button(text='3', font='8x8', x=self.w/2, y=self.h-self._foot_btn_height-1, w=self.w/4-1, h=self._foot_btn_height)
        self._footb_r = Button(text='4', font='8x8', x=3*self.w/4, y=self.h-self._foot_btn_height-1, w=self.w/4-1, h=self._foot_btn_height)

        self.add_element(self._footb_l)
        self.add_element(self._footb_ml)
        self.add_element(self._footb_mr)
        self.add_element(self._footb_r)

    def _input_event(self, evt):
        if evt['event'] == 'keypad.press':
            if evt['data'] == '1':
                self._footb_l.set_state('pressed')
            elif evt['data'] == '2':
                self._footb_ml.set_state('pressed')
            elif evt['data'] == '3':
                self._footb_mr.set_state('pressed')
            elif evt['data'] == '4':
                self._footb_r.set_state('pressed')
        elif evt['event'] == 'keypad.release':
            if evt['data'] == '1':
                self._footb_l.set_state('normal')
            elif evt['data'] == '2':
                self._footb_ml.set_state('normal')
            elif evt['data'] == '3':
                self._footb_mr.set_state('normal')
            elif evt['data'] == '4':
                self._footb_r.set_state('normal')
