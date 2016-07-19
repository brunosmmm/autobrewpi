from t6963 import T6963

class ScreenBuffer(object):

    def __init__(self, width, height):

        # properties
        self._width = width
        self._height = height

        # display controller
        self._lcd = T6963(width, height)

        # screen buffer (horrible)
        self._screen = []
        for i in range(0, height):
            row = []
            for j in range(0, width/6):
               row.append(0x00)
            self._screen.append(row)

    def set_pixel_value(self, x, y, value):

        if x < 0 or x > self._width - 1:
            raise ValueError('invalid x coordinate: {}'.format(x))

        if y < 0 or y > self._height - 1:
            raise ValueError('invalid y coordinate: {}'.format(y))

        bit_mask_x = (1<<(5 - x%6))

        if value:
            self._screen[y][x/6] |= bit_mask_x
        else:
            self._screen[y][x/6] &= ~bit_mask_x

    def put_screen(self):

        self._lcd.lcd_set_address_pointer(self._lcd._gbase)
        self._lcd.lcd_auto_write_start()

        for row in self._screen:
            for col in row:
                self._lcd.lcd_auto_write(int(col))

        self._lcd.lcd_auto_write_stop()
