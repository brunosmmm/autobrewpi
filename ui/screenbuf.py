from ctypes import CDLL
from fonts.fontmgr import FontManager
from ui.element import UIElement
from ui.screen import Screen
from util.thread import StoppableThread
import time

SCREENBUF_SO_PATH = './lcd/screen.so'

class ScreenBuffer(StoppableThread):

    def __init__(self, width, height, refresh_interval=0.5):
        super(ScreenBuffer, self).__init__()
        # properties
        self._width = width
        self._height = height

        #font manager
        self._fmgr = FontManager()

        # display controller
        self._lcd = CDLL(SCREENBUF_SO_PATH)
        self._lcd.SCREEN_Init()

        #screen manager
        self._screens = {}
        self.active_screen = None

        #auto refresh
        self.refresh_interval = refresh_interval

        #control flow
        self._drawing = False
        self._old = False

    def add_screen(self, screen_id, screen_obj):
        screen_obj._parent = self
        screen_obj._screen_id = screen_id
        self._screens[screen_id] = screen_obj

    def remove_screen(self, screen_id):
        del self._screens[screen_id]

    def set_pixel_value(self, x, y, value):
        self._lcd.SCREEN_PSet(x, y, value)

    def put_buffer(self):
        self._lcd.SCREEN_Draw()

    def draw_line(self, x1, y1, x2, y2, color):

        dx = abs(x2 - x1)
        dy = abs(y2 - y1)

        addx = 1
        addy = 1
        if x1 > x2:
            addx = -1

        if y1 > y2:
            addy = -1

        if dx >= dy:
            dy *= 2
            P = dy - dx
            diff = P - dx

            for i in range(0, dx+1):
                self.set_pixel_value(x1, y1, color)

                if P < 0:
                    P += dy
                    x1 += addx
                else:
                    P += diff
                    x1 += addx
                    y1 += addy
        else:
            dx *= 2
            P = dx - dy
            diff = P - dy

            for i in range(0, dy+1):
                self.set_pixel_value(x1, y1, color)

                if P < 0:
                    P += dx
                    y1 += addy
                else:
                    P += diff
                    x1 += addx
                    y1 += addy

    def draw_rectangle(self, x1, y1, x2, y2, fill, color):

        if fill:
            xmin = min(x1, x2)
            xmax = max(x1, x2)
            ymin = min(y1, y2)
            ymax = max(y1, y2)

            for i in range(xmin, xmax+1):
                for j in range(ymin, ymax+1):
                    self.set_pixel_value(i, j, color)
        else:
            self.draw_line(x1, y1, x2, y1, color)
            self.draw_line(x1, y2, x2, y2, color)
            self.draw_line(x1, y1, x1, y2, color)
            self.draw_line(x2, y1, x2, y2, color)

    def draw_bar(self, x1, y1, x2, y2, width, color):
        pass

    def draw_font_char(self, x, y, font_name, char, color):
        try:
            char_data = self._fmgr.get_font_char(font_name, ord(char))
            font_w = self._fmgr.get_font_width(font_name)
            font_h = self._fmgr.get_font_height(font_name)
        except Exception as e:
            print 'error getting font char: {}'.format(e.message)
            return

        row_data = char_data.tolist()
        for i in range(0, font_h):
            for j in range(0, font_w):
                if row_data[i] & (1<<j):
                    self.set_pixel_value(x+j, y+i, color)

    def draw_font_string(self, x, y, font_name, msg, hjust, vjust, color):

        try:
            font_w = self._fmgr.get_font_width(font_name)
            font_h = self._fmgr.get_font_height(font_name)
        except:
            return

        offset_h = 0
        if hjust == 'right':
            offset_h = 0
        elif hjust == 'left':
            offset_h = -font_w*len(msg)
        elif hjust == 'center':
            offset_h = -font_w*len(msg)/2

        offset_v = 0
        if vjust == 'top':
            offset_v = 0
        elif vjust == 'center':
            offset_v = -font_h/2
        elif vjust == 'bottom':
            offset_v = -font_h

        for i in range(0, len(msg)):
            self.draw_font_char(offset_h+x+i*font_w, offset_v+y, font_name, msg[i], color)

    def draw_circle(self, x, y, radius, fill, color):

        a = 0
        b = radius
        P = 1 - radius

        while (a <= b):
            if fill:
                self.draw_line(x-a, y+b, x+a, y+b, color)
                self.draw_line(x-a, y-b, x+a, y-b, color)
                self.draw_line(x-b, y+a, x+b, y+a, color)
                self.draw_line(x-b, y-a, x+b, y-a, color)
            else:
                self.set_pixel_value(a+x, b+y, color)
                self.set_pixel_value(b+x, a+y, color)
                self.set_pixel_value(x-a, b+y, color)
                self.set_pixel_value(x-b, a+y, color)
                self.set_pixel_value(b+x, y-a, color)
                self.set_pixel_value(a+x, y-b, color)
                self.set_pixel_value(x-a, y-b, color)
                self.set_pixel_value(x-b, y-a, color)

            if P < 0:
                P += 3 + 2*a
                a += 1
            else:
                P += 5 + 2*(a - b)
                a += 1
                b -= 1

    def get_height(self):
        return self._height

    def get_width(self):
        return self._width

    def get_fonts(self):
        return self._fmgr._fonts.keys()

    def draw_ui_element(self, element):

        if not isinstance(element, UIElement):
            raise TypeError('not a UIElement object')

        self._drawing = True

        for dwi in element._draw_proxy():

            if dwi.kind == 'line':
                self.draw_line(**dwi.kwargs)
            elif dwi.kind == 'rect':
                self.draw_rectangle(**dwi.kwargs)
            elif dwi.kind == 'text':
                self.draw_font_string(**dwi.kwargs)
            elif dwi.kind == 'circle':
                self.draw_circle(**dwi.kwargs)

        self._drawing = False

    def erase_screen(self):
        self._drawing = True
        for i in range(0, self._width):
            for j in range(0, self._height):
                self.set_pixel_value(i, j, 0)

        self._drawing = False

    def activate_screen(self, screen_id, erase=True):

        if erase:
            self.erase_screen()

        self.draw_ui_element(self._screens[screen_id])
        self.active_screen = screen_id
        self._old = True

    def screen_needs_redrawing(self, screen_id):

        if screen_id != self.active_screen:
            return

        self.activate_screen(screen_id)

    def run(self):

        while True:

            if self.is_stopped():
                exit(0)

            while self._drawing:
                pass

            if self._old:
                self.put_buffer()
                self._old = False

            time.sleep(self.refresh_interval)