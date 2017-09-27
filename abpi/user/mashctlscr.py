from abpi.ui.label import ValueCaption, _composite_label_text
from abpi.ui.box import Box
from abpi.ui.menu import MenuItem
from datetime import datetime
from abpi.user.controllerscr import ABCtlScreen


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

        self._state_label = ValueCaption(caption='Estado',
                                         font='6x8',
                                         maximum_width=self._box_l.w,
                                         y=2,
                                         x=2)
        self._phase_label = ValueCaption(caption='Fase',
                                         maximum_width=self._box_l.w,
                                         font='6x8',
                                         **self._state_label.southwest+(0, 1))
        self._timer_label = ValueCaption(caption='Timer',
                                         font='6x8',
                                         maximum_width=self._box_l.w,
                                         **self._phase_label.southwest+(0, 1))

        # in box R, show current values
        self._hlt_temp_label = ValueCaption(caption='Temp HLT',
                                            font='5x12',
                                            maximum_width=self._box_r.w,
                                            y=2,
                                            x=self.w/2 + 2)
        self._mlt_temp_label = ValueCaption(caption='Temp MLT',
                                            font='5x12',
                                            maximum_width=self._box_r.w,
                                            y=14,
                                            x=self.w/2 + 2)
        self._recipe_label = ValueCaption(value='Nenhum',
                                          caption='Receita',
                                          maximum_width=self._box_l.w,
                                          font='6x8',
                                          **self._timer_label.southwest+(0, 1))

        self._statframe.add_element(self._box_l)
        self._statframe.add_element(self._box_r)
        self._statframe.add_element(self._state_label)
        self._statframe.add_element(self._phase_label)
        self._statframe.add_element(self._timer_label)
        self._statframe.add_element(self._hlt_temp_label)
        self._statframe.add_element(self._mlt_temp_label)
        self._statframe.add_element(self._recipe_label)

        def get_fn(inst, method):
            return self._varspace.get_driver_method(inst, method)

        def _cfgitems():
            yield MenuItem('hystlevel',
                           'Niv Histerese',
                           value_getter=get_fn('MashCtl',
                                               'get_hyst_level'),
                           value_setter=get_fn('MashCtl',
                                               'set_hyst_level'),
                           value_type=float,
                           fixp_size=1,
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
        self._loaded_recipe = None

    def load_recipe(self):
        active_recipe = self._recipemgr.get_loaded_recipe()

        if active_recipe is not None:
            recipe = self._recipemgr.get_recipe(active_recipe)
            self._loaded_recipe = recipe['abbrev']

            self._recipe_label.set_value(self._loaded_recipe)

            # load data into controller
            self._varspace.call_driver_method(self.ctl_inst,
                                              'set_mash_stages',
                                              stage_data=recipe['mash']['steps'])

    def _screen_added(self, **kwargs):
        super(ABMashScreen, self)._screen_added(**kwargs)
        # enter idle
        self._enter_idle()

    def _enter_active(self):
        # change layout
        self._footb_r.set_text('Parar')
        self._footb_ml.set_text('Pausa')
        self._state_label.set_value('ativo')
        self._state = 'active'

    def _enter_idle(self):
        self._footb_r.set_text('Sair')
        self._footb_ml.set_text('Inicia')
        self._state_label.set_value('ocioso')
        self._timer_label.set_value('Nenhum')
        self._phase_label.set_value('parado')
        self._varspace.call_driver_method(self.ctl_inst,
                                          'reset')
        self._state = 'idle'

    def _enter_paused(self):
        self._footb_ml.set_text('Retoma')
        self._state_label.set_value('pausa')
        self._state = 'paused'

    def _enter_panic(self):
        if self._state == 'panic':
            return
        self._footb_ml.set_text('Retoma')
        self._state_label.set_value('panico')
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

            current_stage = self._varspace.call_driver_method(self.ctl_inst,
                                                              'get_current_stage_data')
            if current_stage is None:
                return

            next_stage = self._varspace.call_driver_method(self.ctl_inst,
                                                           'get_next_stage_data')

            if current_stage['type'] == 'water_in':
                # next
                self._enter_active()
                self._varspace.call_driver_method(self.ctl_inst, 'next_stage')
            elif current_stage['type'] in ('water_transfer', 'add_items'):
                # next stage but what is it?
                if next_stage['type'] == 'conversion':
                    self._mash_step()
                elif next_stage['type'] in ('fly_sparge',
                                            'batch_sparge',
                                            'sparge'):
                    if self._mash_phase != 'presparge':
                        self._sparge_wait()
                elif next_stage['type'] == 'add_items':
                    self._addgrains()
                else:
                    # illegal transition
                    self.log_err('illegal transition in recipe: '
                                 '{} -> {}'.format(current_stage['type'],
                                                   next_stage['type']))
                    self._enter_idle()
            elif current_stage['type'] in ('fly_sparge',
                                           'batch_sparge',
                                           'sparge'):
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
        recipe_stage = self._varspace.call_driver_method(self.ctl_inst,
                                                         'get_next_stage_data')
        self._varspace.call_driver_method(self.ctl_inst,
                                          'next_stage')
        if recipe_stage['type'] == 'water_in':
            water_amount = recipe_stage['amount']
            water_unit = recipe_stage['unit']
            self._show_msg_modal('Encha o HLT com agua agora ({} {})\n'
                                 'Pressione CONFIRMA '
                                 'para continuar'.format(water_amount,
                                                         water_unit))
        else:
            pass

    def _mash_stop(self):
        self._varspace.call_driver_method(self.ctl_inst,
                                          'stop_mash')
        self._enter_idle()

    def _mash_done(self):
        pass

    def _sparge_wait(self):
        self._mash_phase = 'presparge'
        self._timer_label.set_value('Nenhum')
        self._show_msg_modal('Aguardando para iniciar Sparge\n'
                             'Pressione CONFIRMA para continuar')
        self._varspace.call_driver_method(self.ctl_inst,
                                          'next_stage')

    def _sparge(self):
        self._mash_phase = 'sparge'
        self._varspace.call_driver_method(self.ctl_inst,
                                          'enter_sparge')

    def _sparge_done(self):

        current_stage = self._varspace.call_driver_method(self.ctl_inst,
                                                          'get_current_stage_data')

        if current_stage is None:
            self._mash_phase = None
            self._enter_idle()

            recipe = self._recipemgr.get_loaded_recipe()
            boil_sg = float(self._recipemgr.get_recipe(recipe)['parameters']['pre_boil_gravity'])

            if boil_sg is not None:
                sg = 'Gravidade esp. pre boil = {}'.format(boil_sg)
            else:
                sg = ''

            self._show_msg_modal('Fim do mash\n'
                                 '{}\n'
                                 'Pressione CONFIRMA para continuar'.format(sg))
        else:
            # illegal for now
            self.log_err('illegal transition in recipe: '
                         'sparge -> {}'.format(current_stage['type']))
            self._enter_idle()

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

        next_stage = self._varspace.call_driver_method(self.ctl_inst,
                                                       'get_next_stage_data')
        current_stage = self._varspace.call_driver_method(self.ctl_inst,
                                                          'get_current_stage_data')
        self._varspace.call_driver_method(self.ctl_inst,
                                          'next_stage')
        if next_stage['type'] == 'water_transfer':
            water_amount = next_stage['amount']
            water_unit = next_stage['unit']
            self._show_msg_modal('Temperatura atingida\n'
                                 'Transfira agua quente '
                                 'ao MLT ({} {}) agora\n'
                                 'Pressione CONFIRMA '
                                 'para continuar'.format(water_amount,
                                                         water_unit))
        elif next_stage['type'] == 'conversion':
            self._mash_step()
        elif next_stage['type'] in ('fly_sparge', 'batch_sparge', 'sparge'):
            self._sparge_wait()
        else:
            # illegal transition!!
            self.log_err('illegal transition in recipe: '
                         '{} -> {}'.format(current_stage['type'],
                                           next_stage['type']))
            self._enter_idle()

    def _addgrains(self):
        self._mash_phase = 'addgrains'
        self._varspace.call_driver_method(self.ctl_inst,
                                          'next_stage')
        self._show_msg_modal('Adicione agora os insumos\n'
                             'Pressione CONFIRMA para continuar')

    def _mash_step(self):
        self._mash_phase = 'mashing'
        self._varspace.call_driver_method(self.ctl_inst,
                                          'next_stage')
        timer_end = self._varspace.call_driver_method(self.ctl_inst,
                                                      'get_timer_end')
        self._timer_label.set_value(str(timer_end -
                                        datetime.now()).split('.')[0])

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
                        if self._recipemgr.get_loaded_recipe() is not None:
                            self._mash_start()
                        else:
                            self._show_msg_modal('Nenhuma receita carregada!')
                    elif self._state == 'active':
                        self._mash_pause_unpause()
                    elif self._state == 'panic':
                        self._varspace.call_driver_method('GWatch',
                                                          'lift_panic')

    def _screen_activated(self, **kwargs):
        super(ABMashScreen, self)._screen_activated(**kwargs)

        # activate mash controller
        self._varspace.call_driver_method('MashCtl', 'activate')
        self._enter_idle()
        self.load_recipe()

    def _screen_deactivated(self, **kwargs):
        super(ABMashScreen, self)._screen_deactivated(**kwargs)

        # deactivate mash controller
        self._varspace.call_driver_method('MashCtl', 'deactivate')

    def update_screen(self):
        # update to current values
        super(ABMashScreen, self).update_screen()
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
        self._hlt_temp_label.set_value('{} C'.format(hlt_temp))
        self._mlt_temp_label.set_value('{} C'.format(mlt_temp))

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
        current_stage = self._varspace.call_driver_method(self.ctl_inst,
                                                          'get_current_stage_data')
        if current_stage is not None:
            if current_stage['type'] == 'preheat':
                self._phase_label.set_value('preaquecedo')
                if state == 'preheat_done':
                    self._preheat_done()
            elif current_stage['type'] == 'conversion':
                self._phase_label.set_value('mash')
                if state != 'mash':
                    self._mash_done()
            elif current_stage['type'] == 'mashout':
                self._phase_label.set_value('mashout')
                if state != 'mashout':
                    pass
            elif current_stage['type'] in ('fly_sparge',
                                           'batch_sparge',
                                           'sparge'):
                self._phase_label.set_value('sparge')

        if self._mash_phase == 'sparge':
            if state not in ('sparge', 'sparge_wait'):
                self._sparge_done()

        if self._mash_phase in ('mashing', 'mashout', 'sparge'):
            timer_end = self._varspace.call_driver_method(self.ctl_inst,
                                                          'get_timer_end')
            if timer_end is not None:
                timer_time = timer_end - datetime.now()
                if timer_time.total_seconds() > 0:
                    self._timer_label.set_value(str(timer_time).split('.')[0])
