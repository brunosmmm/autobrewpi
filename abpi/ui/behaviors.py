
class Behavior(object):
    def __init__(self, *args, **kwargs):
        super(Behavior, self).__init__(*args, **kwargs)


class ButtonBehavior(Behavior):

    _BUTTON_STATES = ['normal', 'pressed']

    def __init__(self, *args, **kwargs):
        if 'state' in kwargs:
            self.state = kwargs.pop('state')
        else:
            self.state = 'normal'
        super(ButtonBehavior, self).__init__(*args, **kwargs)

    def set_state(self, state):
        if state in self._BUTTON_STATES:
            self.state = state

    def get_state(self):
        return self.state
