from ui.label import Label, _composite_label_text
from ui.box import Box
from ui.menu import MenuItem
from datetime import datetime
from user.controllerscr import ABCtlScreen


class ABMashScreen(ABCtlScreen):

    def __init__(self, **kwargs):
        kwargs['title'] = 'Mash Ctl'
        self._recipemgr = kwargs.pop('recipemgr')
        super(ABMashScreen, self).__init__(**kwargs)

        self._box_l = Box(x=0,
                          y=0,
                          w=self.w/2 - 1,
                          h=(self.h -
                             self._foot_btn_height -
                             self._title.h - 3))
        self._box_r = Box(x=self.w/2,
                          y=0,
                          w=self.w/2 - 1,
                          h=(self.h -
                             self._foot_btn_height -
                             self._title.h - 3))

        self._state_label = Label(text='STATE', font='5x12',
                                  y=2,
                                  x=2)
        self._phase_label = Label(text='PHASE', font='5x12',
                                  y=14,
                                  x=2)
        self._timer_label = Label(text='TIMER', font='5x12',
                                  y=26,
                                  x=2)

        # in box R, show current values
        self._hlt_temp_label = Label(text='HLT_TEMP', font='5x12',
                                     y=2,
                                     x=self.w/2 + 2)
        self._mlt_temp_label = Label(text='MLT_TEMP', font='5x12',
                                     y=14,
                                     x=self.w/2 + 2)

        self._statframe.add_element(self._box_l)
        self._statframe.add_element(self._box_r)
        self._statframe.add_element(self._state_label)
        self._statframe.add_element(self._phase_label)
        self._statframe.add_element(self._timer_label)
        self._statframe.add_element(self._hlt_temp_label)
        self._statframe.add_element(self._mlt_temp_label)

        def get_fn(inst, method):
            return self._varspace.get_driver_method(inst, method)

        def _cfgitems():
            yield MenuItem('mashtemp',
                           'Temp Mash',
                           value_getter=get_fn('MashCtl',
                                               'get_mash_sp'),
                           value_setter=get_fn('MashCtl',
                                               'set_mash_sp'),
                           value_type=float,
                           fixp_size=1,
                           item_action='edit')
            yield MenuItem('mashouttemp',
                           'Temp Mashout',
                           value_getter=get_fn('MashCtl',
                                               'get_mashout_sp'),
                           value_setter=get_fn('MashCtl',
                                               'set_mashout_sp'),
                           value_type=float,
                           fixp_size=1,
                           item_action='edit')
            yield MenuItem('hystlevel',
                           'Niv Histerese',
                           value_getter=get_fn('MashCtl',
                                               'get_hyst_level'),
                           value_setter=get_fn('MashCtl',
                                               'set_hyst_level'),
                           value_type=float,
                           fixp_size=1,
                           item_action='edit')
            yield MenuItem('mashdur',
                           'Dur Mash',
                           value_getter=get_fn('MashCtl',
                                               'get_mash_duration'),
                           value_setter=get_fn('MashCtl',
                                               'set_mash_duration'),
                           value_type=int,
                           item_action='edit')
            yield MenuItem('mashoutdur',
                           'Dur Mashout',
                           value_getter=get_fn('MashCtl',
                                               'get_mashout_duration'),
                           value_setter=get_fn('MashCtl',
                                               'set_mashout_duration'),
                           value_type=int,
                           item_action='edit')
            yield MenuItem('spargedur',
                           'Dur Sparge',
                           value_getter=get_fn('MashCtl',
                                               'get_sparge_duration'),
                           value_setter=get_fn('MashCtl',
                                               'set_sparge_duration'),
                           value_type=int,
                           item_action='edit')
        self._cfgmenu.add_items(_cfgitems())

        # local state tracking
        self._state = 'idle'
        self._mash_phase = None
        self._modal_showing = False
        self._panic_saved_state = None

        # find mash controller instance
        self.ctl_inst = self._varspace.find_driver_by_classname('MashController')[0]

        # recurrent call
        self._upd_call_id = None

        # configuration / stat
        self._current_frame = 'stat'
        self._waiting_stop = False

    def _screen_added(self, **kwargs):
        super(ABMashScreen, self)._screen_added(**kwargs)
        # enter idle
        self._enter_idle()

    def _enter_active(self):
        # change layout
        self._footb_r.set_text('Parar')
        self._footb_ml.set_text('Pausa')
        self._state_label.set_text(_composite_label_text('Estado',
                                                         'ativo',
                                                         23))
        if self._state == 'idle':
            self._phase_label.set_text(_composite_label_text('Fase Mash',
                                                             'preaquecendo',
                                                             23))
        self._state = 'active'

    def _enter_idle(self):
        self._footb_r.set_text('Sair')
        self._footb_ml.set_text('Inicia')
        self._state_label.set_text(_composite_label_text('Estado',
                                                         'ocioso',
                                                         23))
        self._phase_label.set_text(_composite_label_text('Fase Mash',
                                                         'parado',
                                                         23))
        self._timer_label.set_text(_composite_label_text('Timer',
                                                         'Nenhum',
                                                         23))
        self._state = 'idle'

    def _enter_paused(self):
        self._footb_ml.set_text('Retoma')
        self._state_label.set_text(_composite_label_text('Estado',
                                                         'pausa',
                                                         23))
        self._state = 'paused'

    def _enter_panic(self):
        if self._state == 'panic':
            return
        self._footb_ml.set_text('Retoma')
        self._state_label.set_text(_composite_label_text('Estado',
                                                         'panico',
                                                         23))
        self._panic_saved_state = self._state
        self._state = 'panic'

    def _confirm_stop(self):
        self._waiting_stop = True
        self._show_msg_modal('Realmente parar?\nPressione CONFIRMA')

    def _confirm_press(self):
        if self._modal_showing:
            self._hide_msg_modal()

            if self._waiting_stop:
                self._mash_stop()
                self._waiting_stop = False
                return

            if self._mash_phase == 'check_water':
                # next
                self._enter_active()
                self._varspace.call_driver_method(self.ctl_inst, 'start_mash')
                self._mash_phase = 'preheat'
            elif self._mash_phase == 'preheat_done':
                self._addgrains()
            elif self._mash_phase == 'addgrains':
                self._main_mash()
            elif self._mash_phase == 'presparge':
                self._sparge()

    def _cancel_press(self):
        if self._modal_showing:
            if self._waiting_stop:
                self._waiting_stop = False
            if self._mash_phase == 'check_water':
                pass
            self._hide_msg_modal()

    def _mash_start(self):
        self._varspace.call_driver_method(self.ctl_inst, 'reset')
        self._mash_phase = 'check_water'
        self._show_msg_modal('Encha o HLT com agua agora\n'
                             'Pressione CONFIRMA para continuar')

    def _mash_stop(self):
        self._varspace.call_driver_method(self.ctl_inst,
                                          'stop_mash')
        self._enter_idle()

    def _mash_done(self):
        self._mash_phase = 'mashout'
        self._phase_label.set_text(_composite_label_text('Fase Mash',
                                                         'mashout',
                                                         23))

    def _mashout_done(self):
        self._mash_phase = 'presparge'
        self._phase_label.set_text(_composite_label_text('Fase Mash',
                                                         'pre-sparge',
                                                         23))
        self._timer_label.set_text(_composite_label_text('Timer',
                                                         'Nenhum',
                                                         23))
        self._show_msg_modal('Aguardando para iniciar Sparge\n'
                             'Pressione CONFIRMA para continuar')

    def _sparge(self):
        self._mash_phase = 'sparge'
        self._phase_label.set_text(_composite_label_text('Fase Mash',
                                                         'sparge',
                                                         23))
        self._varspace.call_driver_method(self.ctl_inst, 'enter_sparge')

    def _sparge_done(self):
        self._mash_phase = None
        self._enter_idle()
        self._show_msg_modal('Fim do mash\n'
                             'Pressione CONFIRMA para continuar')

    def _mash_pause_unpause(self):
        if self._state == 'paused':
            self._enter_active()
            self._varspace.call_driver_method(self.ctl_inst,
                                              'unpause_transfer')
        elif self._state == 'active':
            self._varspace.call_driver_method(self.ctl_inst,
                                              'pause_transfer')
            self._enter_paused()

    def _preheat_done(self):
        self._mash_phase = 'preheat_done'
        self._varspace.call_driver_method(self.ctl_inst,
                                          'enter_transfer')
        self._show_msg_modal('Temperatura atingida\n'
                             'Transfira agua quente ao MLT agora\n'
                             'Pressione CONFIRMA para continuar')

    def _addgrains(self):
        self._mash_phase = 'addgrains'
        self._phase_label.set_text(_composite_label_text('Fase Mash',
                                                         'ad. graos',
                                                         23))
        self._varspace.call_driver_method(self.ctl_inst, 'enter_addgrains')
        self._show_msg_modal('Adicione agora os graos\n'
                             'Pressione CONFIRMA para continuar')

    def _main_mash(self):
        self._mash_phase = 'mashing'
        self._phase_label.set_text(_composite_label_text('Fase Mash',
                                                         'mash/recirc',
                                                         23))
        self._varspace.call_driver_method(self.ctl_inst, 'enter_mash')
        timer_end = self._varspace.call_driver_method(self.ctl_inst,
                                                      'get_timer_end')
        self._timer_label.set_text(_composite_label_text('Timer',
                                                         str(timer_end -
                                                             datetime.now()).split('.')[0],
                                                         23))

    def _input_event(self, evt):
        super(ABMashScreen, self)._input_event(evt)
        if evt['event'] == 'switches.press':

            if evt['data'] == '3':
                if self._state == 'idle':
                    if self._current_frame == 'config' and\
                       self._cfgmenu.is_editing():
                        pass
                    else:
                        self._parent.activate_screen('main')
                else:
                    self._confirm_stop()

            if evt['data'] == '1':
                if self._current_frame == 'stat':
                    if self._state == 'idle':
                        self._mash_start()
                    elif self._state == 'active':
                        self._mash_pause_unpause()
                    elif self._state == 'panic':
                        self._varspace.call_driver_method('GWatch',
                                                          'lift_panic')

    def _screen_activated(self, **kwargs):
        super(ABMashScreen, self)._screen_activated(**kwargs)

        # activate mash controller
        self._varspace.call_driver_method('MashCtl', 'activate')

    def _screen_deactivated(self, **kwargs):
        super(ABMashScreen, self)._screen_deactivated(**kwargs)

        # deactivate mash controller
        self._varspace.call_driver_method('MashCtl', 'deactivate')

    def update_screen(self):
        # update to current values
        if self._manual:
            if self._varspace.call_driver_method('PumpSwitch', 'get_value'):
                self._varspace.call_driver_method('ManualPumpCtl',
                                                  'set_value',
                                                  value=True)
            else:
                self._varspace.call_driver_method('ManualPumpCtl',
                                                  'set_value',
                                                  value=False)
        else:
            self._varspace.call_driver_method('ManualPumpCtl',
                                              'set_value',
                                              value=False)
        # self._manual_changed = False

        hlt_temp = self._varspace.call_driver_method(self.ctl_inst,
                                                     'get_hlt_temp')
        mlt_temp = self._varspace.call_driver_method(self.ctl_inst,
                                                     'get_mlt_temp')
        state = self._varspace.call_driver_method(self.ctl_inst, 'get_state')
        panic = self._varspace.call_driver_method('GWatch', 'is_panic')
        self._hlt_temp_label.set_text(_composite_label_text('HLT Temp',
                                                            '{} C'.format(hlt_temp)
                                                            ,23))
        self._mlt_temp_label.set_text(_composite_label_text('MLT Temp',
                                                            '{} C'.format(mlt_temp)
                                                            ,23))

        if panic:
            self._enter_panic()
            return
        else:
            if self._panic_saved_state == 'active':
                self._enter_active()
            elif self._panic_saved_state == 'idle':
                self._enter_idle()
            self._panic_saved_state = None

        # check state
        if self._mash_phase == 'preheat':
            if state == 'preheat_done':
                self._preheat_done()
        elif self._mash_phase == 'mashing':
            if state == 'mashout':
                self._mash_done()
        elif self._mash_phase == 'mashout':
            if state == 'sparge_wait':
                self._mashout_done()
        elif self._mash_phase == 'sparge':
            if state == 'idle':
                self._sparge_done()

        if self._mash_phase in ('mashing', 'mashout', 'sparge'):
            timer_end = self._varspace.call_driver_method(self.ctl_inst,
                                                          'get_timer_end')
            timer_time = timer_end - datetime.now()
            if timer_time.total_seconds() > 0:
                self._timer_label.set_text(_composite_label_text('Timer',
                                                                 str(timer_time).split('.')[0],
                                                                 23))
