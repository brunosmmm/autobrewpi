from ui.screen import Screen
from ui.button import Button
from ui.label import Label, ValueCaption
from ui.box import Box
from ui.modal import Modal
from ui.frame import Frame
from ui.radiobutton import RadioGroup, RadioButton
from ui.menu import Menu, MenuItem
from datetime import datetime

class ABMashScreen(Screen):

    _foot_btn_height = 10

    def __init__(self, **kwargs):
        if 'varspace' in kwargs:
            self._varspace = kwargs.pop('varspace')
        else:
            self._varspace = None
        super(ABMashScreen, self).__init__(x=0, y=0, w=240, h=64, **kwargs)

        #upper 'title'
        self._mashctltitle = Button(text=self._composite_label_text('Mash Ctl', ' ', 29),
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

        self._statframe = Frame(x=0,
                                y=self._mashctltitle.y+self._mashctltitle.h+1,
                                w=self.w-1,
                                h=self.h - self._foot_btn_height - self._mashctltitle.h - 3)

        self._configframe = Frame(x=0,
                                  y=self._mashctltitle.y+self._mashctltitle.h+1,
                                  w=self.w-1,
                                  h=self.h - self._foot_btn_height - self._mashctltitle.h - 3)

        self._box_l = Box(x=0,
                          y=0,
                          w=self.w/2 - 1,
                          h=self.h - self._foot_btn_height - self._mashctltitle.h - 3)
        self._box_r = Box(x=self.w/2,
                          y=0,
                          w=self.w/2 - 1,
                          h=self.h - self._foot_btn_height - self._mashctltitle.h - 3)

        self._state_label = Label(text='STATE', font='5x12',
                                  y=2,
                                  x=2)
        self._phase_label = Label(text='PHASE', font='5x12',
                                  y=14,
                                  x=2)
        self._timer_label = Label(text='TIMER', font='5x12',
                                  y=26,
                                  x=2)

        #in box R, show current values
        self._hlt_temp_label = Label(text='HLT_TEMP', font='5x12',
                                     y=2,
                                     x=self.w/2 + 2)
        self._mlt_temp_label = Label(text='MLT_TEMP', font='5x12',
                                     y=14,
                                     x=self.w/2 + 2)

        #message modal
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

        #add stuff
        self.add_element(self._statframe)
        self.add_element(self._configframe)

        self.add_element(self._mashctltitle)
        self.add_element(self._footb_l)
        self.add_element(self._footb_ml)
        self.add_element(self._footb_mr)
        self.add_element(self._footb_r)


        self._statframe.add_element(self._box_l)
        self._statframe.add_element(self._box_r)
        self._statframe.add_element(self._state_label)
        self._statframe.add_element(self._phase_label)
        self._statframe.add_element(self._timer_label)
        self._statframe.add_element(self._hlt_temp_label)
        self._statframe.add_element(self._mlt_temp_label)

        self.add_element(self._msg_modal)

        #configuration menu
        self._cfgmenu = Menu(x=0,
                             y=self._mashctltitle.y+self._mashctltitle.h+3,
                             w=self.w-1,
                             h=self.h - self._foot_btn_height - self._mashctltitle.h - 5,
                             selector_radius=5,
                             font='5x12',
                             cols=2,
                             value_format='[{}]')

        get_fn = lambda inst, method: self._varspace.get_driver_method(inst, method)
        def _cfgitems():
            yield MenuItem('mashtemp',
                           'Temp Mash',
                           value_getter=get_fn('MashCtl', 'get_mash_sp'),
                           value_setter=get_fn('MashCtl', 'set_mash_sp'),
                           value_type=int,
                           item_action='edit')
            yield MenuItem('mashouttemp',
                           'Temp Mashout',
                           value_getter=get_fn('MashCtl', 'get_mashout_sp'),
                           value_setter=get_fn('MashCtl', 'set_mashout_sp'))
            yield MenuItem('hystlevel',
                           'Niv Histerese',
                           value_getter=get_fn('MashCtl', 'get_hyst_level'),
                           value_setter=get_fn('MashCtl', 'set_hyst_level'))
            yield MenuItem('mashdur',
                           'Dur Mash',
                           value_getter=get_fn('MashCtl', 'get_mash_duration'),
                           value_setter=get_fn('MashCtl', 'set_mash_duration'))
            yield MenuItem('mashoutdur',
                           'Dur Mashout',
                           value_getter=get_fn('MashCtl', 'get_mashout_duration'),
                           value_setter=get_fn('MashCtl', 'set_mashout_duration'))
            yield MenuItem('spargedur',
                           'Dur Sparge',
                           value_getter=get_fn('MashCtl', 'get_sparge_duration'),
                           value_setter=get_fn('MashCtl', 'set_sparge_duration'))
        self._cfgmenu.add_items(_cfgitems())
        self.add_element(self._cfgmenu)

        #track manual mode
        self._manual = False
        self._manual_changed = True

        #local state tracking
        self._state = 'idle'
        self._mash_phase = None
        self._modal_showing = False
        self._panic_saved_state = None

        #find mash controller instance
        self.ctl_inst = self._varspace.find_driver_by_classname('MashController')[0]

        #recurrent call
        self._upd_call_id = None

        #configuration / stat
        self._current_frame = 'stat'

    def _show_stats(self):
        self._cfgmenu.hide()
        self._statframe.show()
        self._footb_ml.set_text('Inicia')
        self._footb_mr.set_text('Config')
        self._current_frame = 'stat'

    def _show_config(self):
        self._statframe.hide()
        self._cfgmenu.show()
        self._update_config()
        self._footb_ml.set_text('Edita')
        self._footb_mr.set_text('Status')
        self._current_frame = 'config'

    def _update_config(self):
        self._cfgmenu.update_values()

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
        self._cfgmenu.select_first()
        self.update_screen()

    def _enter_active(self):
        #change layout
        self._footb_r.set_text('Parar')
        self._footb_ml.set_text('Pausa')
        self._state_label.set_text(self._composite_label_text('Estado', 'ativo', 23))
        if self._state == 'idle':
            self._phase_label.set_text(self._composite_label_text('Fase Mash', 'preaquecendo', 23))
        self._state = 'active'

    def _enter_idle(self):
        self._footb_r.set_text('Sair')
        self._footb_ml.set_text('Inicia')
        self._state_label.set_text(self._composite_label_text('Estado', 'ocioso', 23))
        self._phase_label.set_text(self._composite_label_text('Fase Mash', 'parado', 23))
        self._timer_label.set_text(self._composite_label_text('Timer', 'Nenhum', 23))
        self._state = 'idle'

    def _enter_paused(self):
        self._footb_ml.set_text('Retoma')
        self._state_label.set_text(self._composite_label_text('Estado', 'pausa', 23))
        self._state = 'paused'

    def _enter_panic(self):
        if self._state == 'panic':
            return
        self._footb_ml.set_text('Retoma')
        self._state_label.set_text(self._composite_label_text('Estado', 'panico', 23))
        self._panic_saved_state = self._state
        self._state = 'panic'

    def _confirm_press(self):
        if self._modal_showing:

            self._hide_msg_modal()

            if self._mash_phase == 'check_water':
                #next
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
            if self._mash_phase == 'check_water':
                pass
            self._hide_msg_modal()

    def _show_msg_modal(self, message):
        lines = message.split('\n')

        while len(lines) < 3:
            lines.append('')

        if len(lines) > 3:
            #self.log_err('exceeded number of lines in message, truncating')
            lines = lines[0:3]

        #allocate lines
        self._modal_label_1.set_text(lines[0])
        self._modal_label_2.set_text(lines[1])
        self._modal_label_3.set_text(lines[2])
        self._modal_showing = True
        self._msg_modal.show()

    def _hide_msg_modal(self):
        self._modal_showing = False
        self._msg_modal.hide()

    def _mash_start(self):
        self._varspace.call_driver_method(self.ctl_inst, 'reset')
        self._mash_phase = 'check_water'
        self._show_msg_modal('Encha o HLT com agua agora\n'
                             'Pressione CONFIRMA para continuar')

    def _mash_done(self):
        self._mash_phase = 'mashout'
        self._phase_label.set_text(self._composite_label_text('Fase Mash', 'mashout', 23))

    def _mashout_done(self):
        self._mash_phase = 'presparge'
        self._phase_label.set_text(self._composite_label_text('Fase Mash', 'pre-sparge', 23))
        self._timer_label.set_text(self._composite_label_text('Timer', 'Nenhum', 23))
        self._show_msg_modal('Aguardando para iniciar Sparge\n'
                             'Pressione CONFIRMA para continuar')

    def _sparge(self):
        self._mash_phase = 'sparge'
        self._phase_label.set_text(self._composite_label_text('Fase Mash', 'sparge', 23))
        self._varspace.call_driver_method(self.ctl_inst, 'enter_sparge')

    def _sparge_done(self):
        self._mash_phase = None
        self._enter_idle()
        self._show_msg_modal('Fim do mash\n'
                             'Pressione CONFIRMA para continuar')

    def _mash_pause_unpause(self):
        if self._state == 'paused':
            self._enter_active()
            self._varspace.call_driver_method(self.ctl_inst, 'unpause_transfer')
        elif self._state == 'active':
            self._varspace.call_driver_method(self.ctl_inst, 'pause_transfer')
            self._enter_paused()

    def _preheat_done(self):
        self._mash_phase = 'preheat_done'
        self._varspace.call_driver_method(self.ctl_inst, 'enter_transfer')
        self._show_msg_modal('Temperatura atingida\n'
                             'Transfira agua quente ao MLT agora\n'
                             'Pressione CONFIRMA para continuar')

    def _addgrains(self):
        self._mash_phase = 'addgrains'
        self._phase_label.set_text(self._composite_label_text('Fase Mash', 'ad. graos', 23))
        self._varspace.call_driver_method(self.ctl_inst, 'enter_addgrains')
        self._show_msg_modal('Adicione agora os graos\n'
                             'Pressione CONFIRMA para continuar')

    def _main_mash(self):
        self._mash_phase = 'mashing'
        self._phase_label.set_text(self._composite_label_text('Fase Mash', 'mash/recirc', 23))
        self._varspace.call_driver_method(self.ctl_inst, 'enter_mash')
        timer_end = self._varspace.call_driver_method(self.ctl_inst, 'get_timer_end')
        self._timer_label.set_text(self._composite_label_text('Timer',
                                                              str(timer_end - datetime.now()).split('.')[0],
                                                              23))

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
                if self._state == 'idle':
                    self._cfgmenu.cancel_edit()
                    self._parent.activate_screen('main')

            if evt['data'] == '2':
                if self._current_frame == 'stat':
                    self._show_config()
                else:
                    self._cfgmenu.cancel_edit()
                    self._show_stats()

            if evt['data'] == '1':
                if self._current_frame == 'stat':
                    if self._state == 'idle':
                        self._mash_start()
                    elif self._state == 'active':
                        self._mash_pause_unpause()
                    elif self._state == 'panic':
                        self._varspace.call_driver_method('GWatch', 'lift_panic')
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

    def _screen_activated(self, **kwargs):
        super(ABMashScreen, self)._screen_activated(**kwargs)

        #install recurrent call
        self._upd_call_id = self._parent.add_recurrent_call(self.update_screen, 1)

        #show default view
        self._show_stats()

    def _screen_deactivated(self, **kwargs):
        super(ABMashScreen, self)._screen_deactivated(**kwargs)

        #remove recurrent call
        if self._upd_call_id is not None:
            self._parent.remove_recurrent_call(self._upd_call_id)
            self._upd_call_id = None

    def update_screen(self):
        #update to current values
        main_title = 'Mash Ctl'
        if self._current_frame == 'config':
            main_title += ' - CONFIG'
        if self._manual:
            self._mashctltitle.set_text(self._composite_label_text(main_title, 'MANUAL', 29))
            if self._varspace.call_driver_method('PumpSwitch', 'get_value'):
                self._varspace.call_driver_method('ManualPumpCtl', 'set_value', value=True)
            else:
                self._varspace.call_driver_method('ManualPumpCtl', 'set_value', value=False)
        else:
            self._mashctltitle.set_text(self._composite_label_text(main_title, ' ', 29))
            self._varspace.call_driver_method('ManualPumpCtl', 'set_value', value=False)
        #self._manual_changed = False

        hlt_temp = self._varspace.call_driver_method(self.ctl_inst, 'get_hlt_temp')
        mlt_temp = self._varspace.call_driver_method(self.ctl_inst, 'get_mlt_temp')
        state = self._varspace.call_driver_method(self.ctl_inst, 'get_state')
        panic = self._varspace.call_driver_method('GWatch', 'is_panic')
        self._hlt_temp_label.set_text(self._composite_label_text('HLT Temp',
                                                                 '{} C'.format(hlt_temp)
                                                                 ,23))
        self._mlt_temp_label.set_text(self._composite_label_text('MLT Temp',
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

        #check state
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
            timer_end = self._varspace.call_driver_method(self.ctl_inst, 'get_timer_end')
            timer_time = timer_end - datetime.now()
            if timer_time.total_seconds() > 0:
                self._timer_label.set_text(self._composite_label_text('Timer',
                                                                      str(timer_time).split('.')[0],
                                                                      23))
