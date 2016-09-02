from ui.label import Label, _composite_label_text
from ui.menu import MenuItem
from datetime import datetime
from user.controllerscr import ABCtlScreen


class ABBoilScreen(ABCtlScreen):

    _foot_btn_height = 10

    def __init__(self, **kwargs):
        kwargs['title'] = 'Boil Ctl'
        super(ABBoilScreen, self).__init__(**kwargs)

        # labels
        self._state_label = Label(text='STATE',
                                  font='5x12',
                                  y=2,
                                  x=2)

        self._timer_label = Label(text='TIMER',
                                  font='5x12',
                                  **self._state_label.southwest)

        self.ctl_inst = self._varspace.find_driver_by_classname('BoilController')[0]

        # configure menu
        def get_fn(inst, method):
            return self._varspace.get_driver_method(inst, method)

        def _cfgitems():
            yield MenuItem('boildur',
                           'Duracao Fervura',
                           value_getter=get_fn(self.ctl_inst,
                                               'get_boil_duration'),
                           value_setter=get_fn(self.ctl_inst,
                                               'set_boil_duration'),
                           value_type=int,
                           item_action='edit')

        # add elements
        self._statframe.add_element(self._state_label)
        self._statframe.add_element(self._timer_label)

        self._screen_state = 'idle'
        self._waiting_stop = False

    def _start_boil(self):
        self._footb_ml.set_text('Pausa')
        self._footb_r.set_text('Parar')
        self._varspace.call_driver_method(self.ctl_inst,
                                          'start_boil')
        self._screen_state = 'boil_started'

    def _stop_boil(self):
        self._idle()
        self._varspace.call_driver_method(self.ctl_inst,
                                          'stop_boil')

    def _confirm_stop(self):
        self._waiting_stop = True
        self._show_msg_modal('Realmente parar?\nPressione CONFIRMA')

    def _idle(self):
        self._footb_ml.set_text('Inicia')
        self._footb_r.set_text('Sair')
        self._screen_state = 'idle'

    def _screen_activated(self, **kwargs):
        super(ABBoilScreen, self)._screen_activated(**kwargs)

        self._idle()
        self._varspace.call_driver_method(self.ctl_inst, 'activate')

    def _screen_deactivated(self, **kwargs):
        super(ABBoilScreen, self)._screen_deactivated(**kwargs)
        self._varspace.call_driver_method(self.ctl_inst, 'deactivate')

    def update_screen(self):
        super(ABBoilScreen, self).update_screen()

        bk_temp = self._varspace.call_driver_method(self.ctl_inst,
                                                    'get_bk_temp')

        state = self._varspace.call_driver_method(self.ctl_inst,
                                                  'get_state')

        if state == 'boil':

            self._state_label.set_text(_composite_label_text('Estado',
                                                             'fervendo',
                                                             23))

            timer_end = self._varspace.call_driver_method(self.ctl_inst,
                                                          'get_timer_end')
            timer_time = timer_end - datetime.now()
            if timer_time.total_seconds() > 0:
                self._timer_label.set_text(_composite_label_text('Timer',
                                                                 str(timer_time).split('.')[0],
                                                                 23))
        else:

            if state == 'preheat':
                self._state_label.set_text(_composite_label_text('Estado',
                                                                 'aquecendo',
                                                                 23))
            else:
                self._state_label.set_text(_composite_label_text('Estado',
                                                                 'ocioso',
                                                                 23))

            self._timer_label.set_text(_composite_label_text('Timer',
                                                             'Nenhum',
                                                             23))

    def _confirm_press(self):
        super(ABBoilScreen, self)._confirm_press()

        if self._waiting_stop:
            self._stop_boil()
            self._waiting_stop = False

    def _cancel_press(self):
        super(ABBoilScreen, self)._cancel_press()

        self._waiting_stop = False

    def _input_event(self, evt):

        super(ABBoilScreen, self)._input_event(evt)

        if evt['event'] == 'switches.press':
            if evt['data'] == '3':
                if self._screen_state == 'idle' and\
                   self._current_frame == 'stat':
                    self._parent.activate_screen('main')
                elif self._screen_state != 'idle' and\
                     self._waiting_stop is False:
                    self._confirm_stop()

            elif evt['data'] == '1':
                if self._screen_state == 'idle' and\
                   self._current_frame == 'stat':
                    self._start_boil()
