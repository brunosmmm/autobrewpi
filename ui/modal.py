from ui.screen import Screen
from ui.instr import DrawInstruction, DrawInstructionGroup

class Modal(Screen):
    def __init__(self, **kwargs):
        super(Modal, self).__init__(**kwargs)

        self.draw_prio = 999
        #not visible by default
        self.visible = False

    def show(self):
        self.visible = True
        self._needs_redrawing()

    def hide(self):
        self.visible = False
        self._needs_redrawing()

    def _get_drawing_instructions(self):

        #draw frame (filled)
        dwg = DrawInstructionGroup(self.draw_prio)
        dwg.add_instructions(
            DrawInstruction('rect',
                            x1=self.x,
                            y1=self.y,
                            x2=self.x+self.w,
                            y2=self.y+self.h,
                            fill=False,
                            color=True
            ),
            DrawInstruction('rect',
                            x1=self.x+1,
                            y1=self.y+1,
                            x2=self.x+self.w-1,
                            y2=self.y+self.h-1,
                            fill=True,
                            color=False
            )
        )

        dwgl= [dwg]
        child_inst = super(Modal, self)._get_drawing_instructions()
        # set maximum priority
        for child in child_inst:
            child.set_priority(1000)
            dwgl.append(child)

        return dwgl

    #de-override
    def _needs_redrawing(self):
        if self._parent is not None:
            self._parent._needs_redrawing()
