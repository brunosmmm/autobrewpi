from abpi.ui.screen import Screen
from abpi.ui.button import Button
from abpi.ui.label import Label, _composite_label_text
from abpi.ui.modal import Modal
from abpi.ui.frame import Frame
from abpi.ui.menu import Menu


class ABCtlScreen(Screen):

    _foot_btn_height = 10

    def __init__(self, **kwargs):
        if 'varspace' in kwargs:
            self._varspace = kwargs.pop('varspace')
        else:
            self._varspace = None

        if 'label_1s' in kwargs:
            self._label_1s = kwargs.pop('label_1s')
        else:
            self._label_1s = ''

        if 'label_2s' in kwargs:
            self._label_2s = kwargs.pop('label_2s')
        else:
            self._label_2s = 'Inicia'

        if 'label_3s' in kwargs:
            self._label_3s = kwargs.pop('label_3s')
        else:
            self._label_3s = 'Config'

        if 'label_4s' in kwargs:
            self._label_4s = kwargs.pop('label_4s')
        else:
            self._label_4s = 'Sair'

        if 'label_1c' in kwargs:
            self._label_1c = kwargs.pop('label_1c')
        else:
            self._label_1c = ''

        if 'label_2c' in kwargs:
            self._label_2c = kwargs.pop('label_2c')
        else:
            self._label_2c = 'Edita'

        if 'label_3c' in kwargs:
            self._label_3c = kwargs.pop('label_3c')
        else:
            self._label_3c = 'Status'

        if 'label_4c' in kwargs:
            self._label_4c = kwargs.pop('label_4c')
        else:
            self._label_4c = 'Sair'

        self._title_text = kwargs.pop('title')
        super(ABCtlScreen, self).__init__(x=0, y=0, w=240, h=64, **kwargs)

        # upper 'title'
        self._title = Button(text=_composite_label_text(self._title_text,
                                                        ' ',
                                                        29),
                             font='8x8',
                             x=0,
                             y=0,
                             w=239,
                             h=10)

        # lower buttons
        self._footb_l = Button(text=self._label_1s,
                               font='8x8',
                               x=0, y=self.h-self._foot_btn_height-1,
                               w=self.w/4-1,
                               h=self._foot_btn_height)
        self._footb_ml = Button(text=self._label_2s,
                                font='8x8',
                                x=self.w/4,
                                y=self.h-self._foot_btn_height-1,
                                w=self.w/4-1,
                                h=self._foot_btn_height)
        self._footb_mr = Button(text=self._label_3s,
                                font='8x8',
                                x=self.w/2,
                                y=self.h-self._foot_btn_height-1,
                                w=self.w/4-1,
                                h=self._foot_btn_height)
        self._footb_r = Button(text=self._label_4s,
                               font='8x8',
                               x=3*self.w/4,
                               y=self.h-self._foot_btn_height-1,
                               w=self.w/4-1,
                               h=self._foot_btn_height)

        self._statframe = Frame(x=0,
                                y=self._title.y+self._title.h+1,
                                w=self.w-1,
                                h=(self.h -
                                   self._foot_btn_height -
                                   self._title.h - 3))

        self._configframe = Frame(x=0,
                                  y=(self._title.y +
                                     self._title.h+1),
                                  w=self.w-1,
                                  h=(self.h -
                                     self._foot_btn_height -
                                     self._title.h - 3))

        # message modal
        self._msg_modal = Modal(y=10,
                                x=10,
                                w=self.w-20,
                                h=self.h-20)
        self._modal_label_1 = Label(text='',
                                    font='5x12',
                                    x=self._msg_modal.x+2,
                                    y=self._msg_modal.y+2)
        self._modal_label_2 = Label(text='',
                                    font='5x12',
                                    x=self._msg_modal.x+2,
                                    y=self._msg_modal.y+16)
        self._modal_label_3 = Label(text='',
                                    font='5x12',
                                    x=self._msg_modal.x+2,
                                    y=self._msg_modal.y+30)

        self._msg_modal.add_element(self._modal_label_1)
        self._msg_modal.add_element(self._modal_label_2)
        self._msg_modal.add_element(self._modal_label_3)

        # add stuff
        self.add_element(self._statframe)
        self.add_element(self._configframe)

        self.add_element(self._title)
        self.add_element(self._footb_l)
        self.add_element(self._footb_ml)
        self.add_element(self._footb_mr)
        self.add_element(self._footb_r)

        self.add_element(self._msg_modal)

        # configuration menu
        self._cfgmenu = Menu(x=0,
                             y=self._title.y+self._title.h+3,
                             w=self.w-1,
                             h=(self.h -
                                self._foot_btn_height -
                                self._title.h - 5),
                             selector_radius=5,
                             font='5x12',
                             cols=2,
                             value_format='[{}]')

        self.add_element(self._cfgmenu)

        # track manual mode
        self._manual = False
        self._manual_changed = True

        # local state tracking
        self._modal_showing = False
        self._panic_saved_state = None

        # recurrent call
        self._upd_call_id = None

        # configuration / stat
        self._current_frame = 'stat'

    def _show_stats(self):
        self._cfgmenu.hide()
        self._statframe.show()
        self._footb_ml.set_text(self._label_2s)
        self._footb_mr.set_text(self._label_3s)
        self._current_frame = 'stat'

    def _show_config(self):
        self._statframe.hide()
        self._cfgmenu.show()
        self._update_config()
        self._footb_ml.set_text(self._label_2c)
        self._footb_mr.set_text(self._label_3c)
        self._current_frame = 'config'

    def _update_config(self):
        self._cfgmenu.update_values()

    def _screen_added(self, **kwargs):
        super(ABCtlScreen, self)._screen_added(**kwargs)
        # update NOW
        self._cfgmenu.select_first()
        self.update_screen()

    def _confirm_press(self):
        if self._modal_showing:
            self._hide_msg_modal()

    def _cancel_press(self):
        if self._modal_showing:
            self._hide_msg_modal()

    def _show_msg_modal(self, message):
        lines = message.split('\n')

        while len(lines) < 3:
            lines.append('')

        if len(lines) > 3:
            # self.log_err('exceeded number of lines in message, truncating')
            lines = lines[0:3]

        # allocate lines
        self._modal_label_1.set_text(lines[0])
        self._modal_label_2.set_text(lines[1])
        self._modal_label_3.set_text(lines[2])
        self._modal_showing = True
        self._msg_modal.show()

    def _hide_msg_modal(self):
        self._modal_showing = False
        self._msg_modal.hide()

    def _input_event(self, evt):
        if evt['event'] == 'switches.press':

            if self._modal_showing:
                if evt['data'] == '5':
                    self._confirm_press()
                    return
                elif evt['data'] != '4':
                    self._cancel_press()
                    return

            if evt['data'] == '3':
                if self._current_frame == 'config' and\
                   self._cfgmenu.is_editing():
                    self._cfgmenu.cancel_edit()
                # else:
                #    self._parent.activate_screen('main')

            if evt['data'] == '2':
                if self._current_frame == 'stat':
                    self._show_config()
                else:
                    self._cfgmenu.cancel_edit()
                    self._show_stats()

            if evt['data'] == '1':
                if self._current_frame == 'stat':
                    pass
                else:
                    self._cfgmenu.item_click()

        elif evt['event'] == 'mode.change':
            self._manual_changed = True
            if evt['data'] == 'manual':
                self._manual = True
            elif evt['data'] == 'normal':
                self._manual = False

        elif evt['event'] == 'encoder.cw':
            if self._current_frame == 'config':
                self._cfgmenu.select_next()
        elif evt['event'] == 'encoder.ccw':
            if self._current_frame == 'config':
                self._cfgmenu.select_prev()

        elif evt['event'] == 'keypad.press':
            if self._current_frame == 'config':
                if evt['data'] == '*':
                    self._cfgmenu.delete_value()
                    return

                try:
                    numeric_value = int(evt['data'])
                except TypeError:
                    return
                self._cfgmenu.insert_value(numeric_value)

    def _screen_activated(self, **kwargs):
        super(ABCtlScreen, self)._screen_activated(**kwargs)

        # install recurrent call
        self._upd_call_id = self._parent.add_recurrent_call(self.update_screen, 1)

        # show default view
        self._show_stats()

    def _screen_deactivated(self, **kwargs):
        super(ABCtlScreen, self)._screen_deactivated(**kwargs)

        # remove recurrent call
        if self._upd_call_id is not None:
            self._parent.remove_recurrent_call(self._upd_call_id)
            self._upd_call_id = None

    def update_screen(self):
        # update to current values
        main_title = self._title_text
        if self._current_frame == 'config':
            main_title += ' - CONFIG'
        if self._manual:
            self._title.set_text(_composite_label_text(main_title,
                                                       'MANUAL',
                                                       29))
        else:
            self._title.set_text(_composite_label_text(main_title,
                                                       ' ',
                                                       29))
