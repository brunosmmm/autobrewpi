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
                          h=self.h - self._foot_btn_height - self._mashctltitle.h - 1)


        #add stuff
        self.add_element(self._mashctltitle)
        self.add_element(self._footb_l)
        self.add_element(self._footb_ml)
        self.add_element(self._footb_mr)
        self.add_element(self._footb_r)
        self.add_element(self._state_label)
        self.add_element(self._box_l)

        #track manual mode
        self._manual = False

        #local state tracking
        self._state = 'idle'

        #find mash controller instance
        self.ctl_inst = self._varspace.find_driver_by_classname('MashController')[0]

    def _screen_added(self, **kwargs):
        super(ABMashScreen, self)._screen_added(**kwargs)
        #enter idle
        self._enter_idle()

    def _enter_active(self):
        #change layout
        self._footb_r.set_text('Parar')
        self._state = 'active'

    def _enter_idle(self):
        self._footb_r.set_text('Sair')
        self._state_label.set_text('Ocioso')
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
