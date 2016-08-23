from ui.checkbox import CheckBox
from ui.instr import DrawInstruction, DrawInstructionGroup
import uuid
from collections import OrderedDict

class GroupError(Exception):
    pass

class RadioGroup(object):

    def __init__(self):
        self._registered_btns = OrderedDict()
        self._selected_btn = None

    def register_btn(self, btn_uid, state_change_cb):
        self._registered_btns[btn_uid] = state_change_cb

    def select_btn(self, btn_uid):
        if btn_uid not in self._registered_btns:
            raise GroupError('uid not registered in this group')

        self._selected_btn = btn_uid
        for uid, cb in self._registered_btns.iteritems():
            if cb is not None:
                if uid == self._selected_btn:
                    cb('pressed')
                else:
                    cb('normal')

    def _select_index(self, index):
        self.select_btn(self._registered_btns.keys()[index])

    def select_first(self):
        self._select_index(0)

    def select_next(self):
        selected_index = self._registered_btns.keys().index(self._selected_btn)
        if selected_index < len(self._registered_btns) - 1:
            self.select_btn(self._registered_btns[selected_index + 1])
        else:
            self.select_first()

    def select_prev(self):
        selected_index = self._registered_btns.keys().index(self._selected_btn)
        if selected_index > 0:
            self.select_btn(self._registered_btns[selected_index - 1])
        else:
            self._select_index(-1)

class RadioButton(CheckBox):
    def __init__(self, **kwargs):
        if 'group' in kwargs:
            self.group = kwargs.pop('group')
        else:
            self.group = None

        #use radius, not w/h
        self.r = kwargs.pop('r')
        kwargs['w'] = 2*self.r
        kwargs['h'] = 2*self.r

        #generate an unique id
        self._uid = uuid.uuid1()

        #register in group
        if self.group is not None:
            self.group.register_btn(self._uid, self.set_state)

        super(RadioButton, self).__init__(**kwargs)

    #override set_state
    def set_state(self, state):
        if self.state != state:
            super(RadioButton, self).set_state(state)
            if self.group is not None:
                if state == 'pressed':
                    self.group.select_btn(self._uid)

    def _get_drawing_instructions(self):
        dwg = DrawInstructionGroup(self.draw_prio)
        dwg.add_instructions(
            DrawInstruction('circle',
                            x=self.x+self.w/2,
                            y=self.y+self.h/2,
                            radius=self.w/2,
                            fill=False,
                            color=True
            )
        )

        if self.state == 'pressed':
            dwg.add_instructions(
                DrawInstruction('circle',
                                x=self.x+self.w/2,
                                y=self.y+self.h/2,
                                radius=self.w/2-3,
                                fill=True,
                                color=True)
                )
        return [dwg]
