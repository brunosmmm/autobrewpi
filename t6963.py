import RPi.GPIO as gpio
import struct

DEFAULT_LCD_PINS = {
    'FNT' : 12,
    'REV' : 16,
    'CD' : 18,
    'CE' : 22,
    'D0' : 24,
    'D1' : 26,
    'D2' : 32,
    'D3' : 36,
    'D4' : 38,
    'D5' : 40,
    'D6' : 37,
    'D7' : 35
}

LCD_MODE_OR = 0x00
LCD_MODE_XOR = 0x01
LCD_MODE_AND = 0x03
LCD_MODE_TEXT_ONLY = 0x04
LCD_MODE_CG_RAM = 0x08

DM_GRAPHICS = 0x08
DM_TEXT = 0x04
DM_CURSOR = 0x02
DM_CURSOR_BLINK = 0x01

class T6963(object):

    def __init__(self, width, height, font_select=False, pin_scheme=DEFAULT_LCD_PINS):

        # set pin numbering scheme
        gpio.setmode(gpio.BOARD)

        # configure pin direction
        for name, number in pin_scheme.iteritems():
            gpio.setup(number, gpio.OUT)

        #store pin scheme
        self._pin_scheme = pin_scheme

        # set CE
        self._set_pin('CE')

        #font select
        if font_select:
            self._clr_pin('FNT')
        else:
            self._set_pin('FNT')

        self._font_size = font_select

        #calculate size, etc
        font_width = 8 if font_select else 6;
        font_height = 8

        self._cols = width/font_width
        self._rows = height/font_height
        self._tsize = self._cols*self._rows
        self._gsize = self._cols*self._rows*font_height

        self._tbase = 0
        self._gbase = self._tsize

        #controller initialization
        self.send_command(0x40, struct.pack('h', self._tbase))
        self.send_command(0x41, struct.pack('h', 0x1E if self._font_size else 0x28))
        self.send_command(0x42, struct.pack('h', self._gbase))
        self.send_command(0x43, struct.pack('h', 0x1E if self._font_size else 0x28))

        #set default mode
        self.lcd_mode(LCD_MODE_OR)
        self.lcd_display_mode(DM_TEXT + DM_GRAPHICS)

        #erase screen



    def _set_pin(self, pin_name):

        self._put_pin(pin_name, True)

    def _clr_pin(self, pin_name):

        self._put_pin(pin_name, False)

    def _put_pin(self, pin_name, value):

        if pin_name not in self._pin_scheme:
            raise KeyError('Invalid pin: {}'.format(pin_name))
        if value:
            value = gpio.HIGH
        else:
            value = gpio.LOW

        gpio.output(self._pin_scheme[pin_name], value)

    def _chip_enable(self):

        self._clr_pin('CE')

    def _chip_disable(self):

        self._set_pin('CE')

    def _enable_command(self):

        self._set_pin('CD')

    def _enable_data(self):

        self._clr_pin('CD')

    def _put_data(self, data):

        for i in range(0, 8):
            if data & (1<<i):
                self._set_pin('D{}'.format(i))
            else:
                self._clr_pin('D{}'.format(i))

    def _lcd_command(self, cmd):

        self._put_data(cmd)
        self._enable_command()

        self._chip_enable()
        #sleep
        self._chip_disable()

    def _lcd_data(self, cmd):

        self._put_data(cmd)
        self._enable_data()

        self._chip_enable()
        #sleep
        self._chip_disable()

    def send_command(self, command, params):

        if len(params) > 2:
            params = params[0:2]

        for param in params:
            self._lcd_data(int(param))

        self._lcd_command(int(command))

    def lcd_mode(self, mode):
        self._lcd_command(0x80 + mode)

    def lcd_display_mode(self, display_mode):
        self._lcd_command(0x90 + display_mode)

    def lcd_set_offset_register(self, offset):
        self.send_command(0x22, struct.pack('h', offset))

    def lcd_set_cursor_pointer(self, pointer):
        self.send_command(0x21, struct.pack('h', pointer))

    def lcd_set_address_pointer(self, address):
        self.send_command(0x24, struct.pack('h', address))

    def lcd_data_write(self, data):
        self.send_command(0xC4, struct.pack('b', data))

    def lcd_data_write_up(self, data):
        self.send_command(0xC0, struct.pack('b', data))

    def lcd_write_data_down(self, data):
        self.send_command(0xC2, struct.pack('b', data))

    def lcd_auto_write_start(self):
        self._lcd_command(0xB0)

    def lcd_auto_write(self, data):
        self._lcd_data(data)

    def lcd_auto_write_stop(self):
        self._lcd_command(0xB2);

    def lcd_set_bit(self, bit, val):
        self._lcd_command(0xF7 - bit + 8 if val else 0)

    def lcd_print(self, text):
        for t in text:
            self.lcd_data_write_up(int(t) - 0x20)

    def erase_screen(self):
        self.lcd_set_address_pointer(self._gbase)
        self.lcd_auto_write_start()

        for i in range(0, self._gsize):
            self.lcd_auto_write(0x00)

        self.lcd_auto_write_stop()
        self.lcd_set_address_pointer(self._tbase)

        self.lcd_auto_write_start()
        for i in range(0, self._tsize):
            self.lcd_auto_write(0x00)
        self.lcd_auto_write_stop()
