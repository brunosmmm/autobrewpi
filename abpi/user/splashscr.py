from abpi.ui.screen import Screen
from abpi.ui.label import Label


class ABSplashScreen(Screen):

    def __init__(self, **kwargs):
        super(ABSplashScreen, self).__init__(x=0, y=0, w=240, h=64, **kwargs)

        # AutoBrew
        ab_name = Label(text='AutoBrew', font='16x26', x=10, y=10)
        # ab_img = Image(path='user/beer.png', x=190, y=2)

        # self.add_element(ab_img)
        self.add_element(ab_name)
