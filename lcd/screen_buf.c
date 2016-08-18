#include "screen_buf.h"
#include <string.h>
#include "lcd_controller.h"
#include "lcd_screen.h"
#include "lcd_graphics.h"
#include <stdio.h>
#include <unistd.h>

#define SCREEN_MEM_SIZE SCREEN_WIDTH*SCREEN_HEIGHT/6

static unsigned char ScreenBuf_FRONT[SCREEN_WIDTH/6][SCREEN_HEIGHT], ScreenBuf_BACK[SCREEN_WIDTH/6][SCREEN_HEIGHT];
static unsigned char ScreenFlags;

static void _lcd_erase(void);

#define ABS(x) ((x>0) ? (x) : (-x))
#define MIN(x,y) ((x>y) ? (y) : (x))
#define MAX(x,y) ((x>y) ? (x) : (y))

void SCREEN_Init(void)
{

    memset(ScreenBuf_FRONT, 0x00, SCREEN_MEM_SIZE);
    memset(ScreenBuf_BACK, 0x00, SCREEN_MEM_SIZE);

    ScreenFlags = SCREEN_FLAG_FRONT;

    //initialize LCD screen
    LCD_screen_init(SCREEN_WIDTH, SCREEN_HEIGHT, 0);

    // MODE SET
    LCD_mode( MODE_OR );

    // DISPLAY MODE
    LCD_display_mode(DM_GRAPHICS);

    _lcd_erase();
}

void SCREEN_PSet(unsigned int x, unsigned int y, unsigned char col)
{
    unsigned int bit_mask_x;

    //check
    if (x > SCREEN_WIDTH - 1)
    {
        printf("pset: Illegal x coordinate: %d\n", x);
        return;
    }

    if (y > SCREEN_HEIGHT - 1)
    {
        printf("pset: Illegal y coordinate: %d\n",y);
        return;
    }

    bit_mask_x = (1<<(5 - x%6));

    if (ScreenFlags & SCREEN_FLAG_FRONT)
    {
        if (col)
        {
            ScreenBuf_BACK[x/6][y] |= bit_mask_x;
        }
        else
        {
            ScreenBuf_BACK[x/6][y] &= ~bit_mask_x;
        }
    }
    else
    {
        if (col)
        {
            ScreenBuf_FRONT[x/6][y] |= bit_mask_x;
        }
        else
        {
            ScreenBuf_FRONT[x/6][y] &= ~bit_mask_x;
        }
    }
}

void SCREEN_Line(unsigned int x1, unsigned int y1, unsigned int x2, unsigned int y2, unsigned char col)
{
    int dx, dy;
    int addx, addy;
    int P, diff;
    int i;

    dx = ABS(x2 - x1);
    dy = ABS(y2 - y1);

    addx = 1;
    addy = 1;

    if (x1 > x2)
    {
        addx = -1;
    }

    if (y1 > y2)
    {
        addy = -1;
    }

    if (dx >= dy)
    {
        dy *= 2;
        P = dy - dx;
        diff = P - dx;

        for (i = 0; i < dx+1; i++)
        {
            SCREEN_PSet(x1, y1, col);

            if (P < 0)
            {
                P += dy;
                x1 += addx;
            }
            else
            {
                P += diff;
                x1 += addx;
                y1 += addy;
            }
        }
    }
    else
    {
        dx *= 2;
        P = dx - dy;
        diff = P - dy;

        for (i = 0; i < dy+1; i++)
        {
            SCREEN_PSet(x1, y1, col);

            if (P < 0)
            {
                P += dx;
                y1 += addy;
            }
            else
            {
                P += diff;
                x1 += addx;
                y1 += addy;
            }
        }
    }

}

void SCREEN_Rectangle(unsigned int x1, unsigned int y1, unsigned int x2, unsigned int y2, unsigned char fill, unsigned char col)
{
    int xmin, xmax, ymin, ymax, i, j;

    if (fill)
    {
        xmin = MIN(x1, x2);
        xmax = MAX(x1, x2);
        ymin = MIN(y1, y2);
        ymax = MAX(y1, y2);

        for (i = xmin; i < xmax+1; i++)
        {
            for (j = ymin; j < ymax+1; j++)
            {
                SCREEN_PSet(i, j, col);
            }
        }
    }
    else
    {
        SCREEN_Line(x1, y1, x2, y1, col);
        SCREEN_Line(x1, y2, x2, y2, col);
        SCREEN_Line(x1, y1, x1, y2, col);
        SCREEN_Line(x2, y1, x2, y2, col);
    }
}

void SCREEN_Circle(unsigned int x, unsigned int y, unsigned char radius, unsigned char fill, unsigned char col)
{
    int a = 0, b = radius, P = 1- radius;

    while (a <= b)
    {
        if (fill)
        {
            SCREEN_Line(x-a, y+b, x+a, y+b, col);
            SCREEN_Line(x-a, y-b, x+a, y-b, col);
            SCREEN_Line(x-b, y+a, x+b, y+a, col);
            SCREEN_Line(x-b, y-a, x+b, y-a, col);
        }
        else
        {
            SCREEN_PSet(a+x, b+y, col);
            SCREEN_PSet(b+x, a+y, col);
            SCREEN_PSet(x-a, b+y, col);
            SCREEN_PSet(x-b, a+y, col);
            SCREEN_PSet(b+x, y-a, col);
            SCREEN_PSet(a+x, y-b, col);
            SCREEN_PSet(x-a, y-b, col);
            SCREEN_PSet(x-b, y-a, col);
        }

        if (P < 0)
        {
            P += 3 + 2*a;
            a += 1;
        }
        else
        {
            P += 5 + 2*(a - b);
            a += 1;
            b -= 1;
        }
    }
}

void SCREEN_Char(unsigned int x, unsigned int y, unsigned int* row_data, unsigned int font_w, unsigned int font_h, unsigned char col)
{
    int i, j;

    for (i = 0; i < font_h; i++)
    {
        for (j = 0; j < font_w; j++)
        {
            if (row_data[i] & (1<<j))
            {
                SCREEN_PSet(x+j, y+i, col);
            }
        }
    }
}

void SCREEN_Flip(void)
{
    unsigned char temp[SCREEN_WIDTH/6][SCREEN_HEIGHT];

    memcpy(temp, ScreenBuf_BACK, SCREEN_MEM_SIZE);
    memcpy(ScreenBuf_BACK, ScreenBuf_FRONT, SCREEN_MEM_SIZE);
    memcpy(ScreenBuf_FRONT, temp, SCREEN_MEM_SIZE);
}

void SCREEN_Copy(unsigned char* source)
{
    memcpy(ScreenBuf_BACK, source, SCREEN_MEM_SIZE);
}

void SCREEN_Draw(void)
{
    unsigned int x, y;

    LCD_set_address_pointer(LCD_getBaseGraphic());
    LCD_auto_write_start();
    for (y = 0; y < SCREEN_HEIGHT; y++)
    {
        for (x = 0; x < SCREEN_WIDTH/6; x++)
        {
            //FLIPPED!!!!!
            if (ScreenFlags & SCREEN_FLAG_FRONT)
            {
                LCD_auto_write(ScreenBuf_BACK[x][y]);
            }
            else
            {
                LCD_auto_write(ScreenBuf_FRONT[x][y]);
            }

            //throttle optionally
            //usleep(10);
        }
    }
    LCD_auto_write_stop();
}

void SCREEN_Erase(void)
{
    memset(ScreenBuf_BACK, 0, SCREEN_MEM_SIZE);
}

void SCREEN_Blank(void)
{
    _lcd_erase();
}

void _lcd_erase(void)
{
    unsigned int i;
    LCD_set_address_pointer( LCD_getBaseGraphic() );
    LCD_auto_write_start();
    for (i=0;i< LCD_getGraphicScreenSize() ;i++) {
        LCD_auto_write( 0x00 );
    }
    LCD_auto_write_stop();
    LCD_set_address_pointer( LCD_getBaseText() );
}
