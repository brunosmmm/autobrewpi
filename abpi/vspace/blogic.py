from abpi.vspace import VSpaceDriver, VSpaceInput, VSpaceOutput


class LogicBlock(VSpaceDriver):

    _inputs = {'A': VSpaceInput('BOOLEAN', False),
               'B': VSpaceInput('BOOLEAN', False)}

    _outputs = {'Y': VSpaceOutput('BOOLEAN', False)}

    def __init__(self, logic_fn, **kwargs):
        super(LogicBlock, self).__init__(**kwargs)

        self._fn = logic_fn

    def update_local_variable(self, variable_name, new_value):
        super(LogicBlock).update_local_variable(variable_name, new_value)

        if self._fn == 'OR':
            self.__Y = self.__A or self.__B
        elif self._fn == 'AND':
            self.__Y = self.__A and self.__B
        elif self._fn == 'XOR':
            self.__Y = self.__A ^ self.__B
