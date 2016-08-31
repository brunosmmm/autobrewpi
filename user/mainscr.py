from ui.screen import Screen
from ui.button import Button
from ui.label import Label


class ABMainScreen(Screen):

    _foot_btn_height = 10

    def __init__(self, **kwargs):
        super(ABMainScreen, self).__init__(x=0, y=0, w=240, h=64, **kwargs)

        # AutoBrew
        ab_name = Label(text='AutoBrew', font='16x26', x=10, y=10)
        # ab_img = Image(path='user/beer.png', x=190, y=2)

        # lower buttons
        self._footb_l = Button(text='',
                               font='8x8',
                               x=0,
                               y=self.h-self._foot_btn_height-1,
                               w=self.w/4-1,
                               h=self._foot_btn_height)
        self._footb_ml = Button(text='',
                                font='8x8',
                                x=self.w/4,
                                y=self.h-self._foot_btn_height-1,
                                w=self.w/4-1,
                                h=self._foot_btn_height)
        self._footb_mr = Button(text='',
                                font='8x8',
                                x=self.w/2,
                                y=self.h-self._foot_btn_height-1,
                                w=self.w/4-1,
                                h=self._foot_btn_height)
        self._footb_r = Button(text='MashCtl',
                               font='8x8',
                               x=3*self.w/4,
                               y=self.h-self._foot_btn_height-1,
                               w=self.w/4-1,
                               h=self._foot_btn_height)

        # self.add_element(ab_img)
        self.add_element(ab_name)
        self.add_element(self._footb_l)
        self.add_element(self._footb_ml)
        self.add_element(self._footb_mr)
        self.add_element(self._footb_r)

    def _input_event(self, evt):
        if evt['event'] == 'switches.press':
            if evt['data'] == '3':
                self._parent.activate_screen('mash')
