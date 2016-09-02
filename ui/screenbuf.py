from ctypes import CDLL, c_uint
from fonts.fontmgr import FontManager
from ui.element import UIElement
from util.thread import StoppableThread
from array import array
from datetime import datetime
import logging
import time
import uuid

SCREENBUF_SO_PATH = './lcd/screen.so'


class RecurrentCall(object):
    def __init__(self, callback, interval):
        self.cb = callback
        self.interval = interval

        self._last_called = datetime.now()


class ScreenBuffer(StoppableThread):

    def __init__(self, width, height, input_client,
                 refresh_interval=0.05, screen_on_hook=None,
                 splash=None):
        super(ScreenBuffer, self).__init__()

        # logging
        self.logger = logging.getLogger('AutoBrew.ScreenBuffer')

        # properties
        self._width = width
        self._height = height

        # input client
        self._icli = input_client

        # display controller
        self._lcd = CDLL(SCREENBUF_SO_PATH)
        self._lcd.SCREEN_Init()
        if splash is not None:
            self._splash_screen(splash)

        self._splash = splash

        if screen_on_hook is not None:
            screen_on_hook()

        # font manager
        self._fmgr = FontManager()

        # screen manager
        self._screens = {}
        self.active_screen = None

        # auto refresh
        self.refresh_interval = refresh_interval

        # control flow
        self._drawing = False
        self._old = False

        # local buffer
        self._screenbuf = array('B', [])
        for i in range(0, height):
            for j in range(0, width/6):
                self._screenbuf.append(0x00)

        # flags
        self._needs_redrawing = None
        self._pause_calls = False

        # attach input client callbacks
        self._icli.attach_callback('keypad.press', self._keypad_keypress)
        self._icli.attach_callback('keypad.release', self._keypad_keyrelease)
        self._icli.attach_callback('encoder.cw', self._encoder_rotate_cw)
        self._icli.attach_callback('encoder.ccw', self._encoder_rotate_ccw)
        self._icli.attach_callback('encoder.press', self._encoder_press)
        self._icli.attach_callback('encoder.release', self._encoder_release)
        self._icli.attach_callback('switches.press', self._switch_press)
        self._icli.attach_callback('switches.release', self._switch_release)

        # recurrent call manager
        self.recurrent_calls = {}

    def _switch_press(self, data, uuid):
        if self.active_screen is not None:

            # filter manual switch out
            if data == '4':
                event = {'event': 'mode.change',
                         'data': 'manual'}
            else:
                event = {'event': 'switches.press',
                         'data': data}

            self._screens[self.active_screen]._input_event(event)

    def _switch_release(self, data, uuid):
        if self.active_screen is not None:

            if data == '4':
                event = {'event': 'mode.change',
                         'data': 'normal'}
            else:
                event = {'event': 'switches.release',
                         'data': data}
            self._screens[self.active_screen]._input_event(event)

    def _keypad_keypress(self, data, uuid):
        if self.active_screen is not None:
            active_screen = self._screens[self.active_screen]
            active_screen._input_event({'event': 'keypad.press',
                                        'data': data})

    def _keypad_keyrelease(self, data, uuid):
        if self.active_screen is not None:
            active_screen = self._screens[self.active_screen]
            active_screen._input_event({'event': 'keypad.release',
                                        'data': data})

    def _encoder_rotate_cw(self, data, uuid):
        if self.active_screen is not None:
            active_screen = self._screens[self.active_screen]
            active_screen._input_event({'event': 'encoder.cw',
                                        'data': None})

    def _encoder_rotate_ccw(self, data, uuid):
        if self.active_screen is not None:
            active_screen = self._screens[self.active_screen]
            active_screen._input_event({'event': 'encoder.ccw',
                                        'data': None})

    def _encoder_press(self, data, uuid):
        if self.active_screen is not None:
            active_screen = self._screens[self.active_screen]
            active_screen._input_event({'event': 'encoder.press',
                                        'data': None})

    def _encoder_release(self, data, uuid):
        if self.active_screen is not None:
            active_screen = self._screens[self.active_screen]
            active_screen._input_event({'event': 'encoder.release',
                                        'data': None})

    def add_screen(self, screen_id, screen_obj):
        screen_obj._parent = self
        screen_obj._screen_id = screen_id
        self._screens[screen_id] = screen_obj
        screen_obj._screen_added()

    def remove_screen(self, screen_id):
        del self._screens[screen_id]

    def set_pixel_value(self, x, y, value):
        self._lcd.SCREEN_PSet(x, y, value)

    def put_buffer(self):
        self._lcd.SCREEN_Draw()

    def draw_line(self, x1, y1, x2, y2, color):
        self._lcd.SCREEN_Line(x1, y1, x2, y2, color)

    def draw_rectangle(self, x1, y1, x2, y2, fill, color):
        self._lcd.SCREEN_Rectangle(x1, y1, x2, y2, fill, color)

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
        row_data_array = (c_uint*len(row_data))(*row_data)
        self._lcd.SCREEN_Char(x, y, row_data_array, font_w, font_h, color)

    def draw_bitmap(self, x, y, data):
        for ix in range(0, data.width):
            for iy in range(0, data.height):
                if data.getpixel((ix, iy)) < 255:
                    self.set_pixel_value(x+ix, y+iy, True)
                else:
                    self.set_pixel_value(x+ix, y+iy, False)

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
            self.draw_font_char(offset_h+x+i*font_w,
                                offset_v+y,
                                font_name,
                                msg[i],
                                color)

    def draw_circle(self, x, y, radius, fill, color):
        self._lcd.SCREEN_Circle(x, y, radius, fill, color)

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

        drawing_groups = element._draw_proxy()

        if not isinstance(drawing_groups, list):
            drawing_groups = [drawing_groups]

        # organize drawing list by priority
        drawing_groups = sorted(drawing_groups, key=lambda group: group._prio)

        for group in drawing_groups:
            drawing_list = group._instrlist
            for dwi in drawing_list:
                if dwi.kind == 'line':
                    self.draw_line(**dwi.kwargs)
                elif dwi.kind == 'rect':
                    self.draw_rectangle(**dwi.kwargs)
                elif dwi.kind == 'text':
                    self.draw_font_string(**dwi.kwargs)
                elif dwi.kind == 'circle':
                    self.draw_circle(**dwi.kwargs)
                elif dwi.kind == 'bitmap':
                    self.draw_bitmap(**dwi.kwargs)

        self._drawing = False

    def erase_screen(self, blank=False):
        self._drawing = True

        self._lcd.SCREEN_Erase()
        if blank:
            self._lcd.SCREEN_Blank()

        self._drawing = False

    def activate_screen(self, screen_id, erase=True):
        self._pause_calls = True
        # wait till drawing stops
        while self._drawing:
            time.sleep(0.01)

        self.logger.debug('activating screen {}'.format(screen_id))
        if self.active_screen is not None:
            self._screens[self.active_screen]._screen_deactivated()
        try:
            self._active_screen = None
            self._activate_screen(screen_id, erase, blank=True)
            self._screens[screen_id]._screen_activated()
        except KeyError:
            self.logger.error('invalid screen id: {}'.format(screen_id))

        self._pause_calls = False

    def log_err(self, msg):
        self.logger.error(msg)

    def log_warn(self, msg):
        self.logger.warning(msg)

    def log_info(self, msg):
        self.logger.info(msg)

    def _activate_screen(self, screen_id, erase=True, blank=False):

        # wait
        while self._drawing:
            time.sleep(0.01)

        if erase:
            self.erase_screen(blank)

        self.draw_ui_element(self._screens[screen_id])
        self.active_screen = screen_id
        self._old = True

    def _splash_screen(self, screen):
        self.erase_screen(True)
        self.draw_ui_element(screen)
        self.put_buffer()

    def screen_needs_redrawing(self, screen_id):

        if screen_id != self.active_screen:
            return

        self._needs_redrawing = screen_id

    def add_recurrent_call(self, callback, interval):

        rc_obj = RecurrentCall(callback, interval)
        rc_uuid = str(uuid.uuid1())

        self.recurrent_calls[rc_uuid] = rc_obj
        return rc_uuid

    def remove_recurrent_call(self, rc_uuid):
        if rc_uuid in self.recurrent_calls:
            del self.recurrent_calls[rc_uuid]

    def run(self):

        while True:

            if self.is_stopped():
                # clear screen!
                if self._splash is not None:
                    self._splash_screen(self._splash)
                else:
                    self._lcd.SCREEN_Blank()
                exit(0)

            if self._needs_redrawing is not None:
                self._activate_screen(self._needs_redrawing)
                self._needs_redrawing = None

            while self._drawing:
                time.sleep(0.01)

            if self._old:
                self.put_buffer()
                self._old = False

            # process recurrent calls
            if self._pause_calls is False:
                for rc in self.recurrent_calls.values():
                    td = datetime.now() - rc._last_called
                    if td.total_seconds > rc.interval:
                        if rc.cb is not None:
                            rc.cb()
                            rc._last_called = datetime.now()

            time.sleep(self.refresh_interval)
