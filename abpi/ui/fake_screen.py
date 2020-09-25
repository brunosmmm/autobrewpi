"""Fake screen."""


class FakeScreen:
    """Fake screen."""

    def SCREEN_Init(self):
        """Screen initialization."""

    def SCREEN_Pset(self, x, y, value):
        """Pixel set."""

    def SCREEN_Draw(self):
        """Redraw."""

    def SCREEN_Line(self, x1, y1, x2, y2, color):
        """Draw line."""

    def SCREEN_Rectangle(self, x1, y1, x2, y2, fill, color):
        """Draw rectangle."""

    def SCREEN_Char(x, y, row_data_array, font_w, font_h, color):
        """Draw character."""

    def SCREEN_Circle(x, y, radius, fill, color):
        """Draw circle."""

    def SCREEN_Erase(self):
        """Erase screen."""

    def SCREEN_Blank(self):
        """Blank screen."""
