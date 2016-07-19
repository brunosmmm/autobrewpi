#include "screen_buf.h"
#include <string.h>
#include "lcd_controller.h"
#include "lcd_screen.h"
#include "lcd_graphics.h"
#include <stdio.h>

#define SCREEN_MEM_SIZE SCREEN_WIDTH*SCREEN_HEIGHT/6

static unsigned char ScreenBuf_FRONT[SCREEN_WIDTH/6][SCREEN_HEIGHT], ScreenBuf_BACK[SCREEN_WIDTH/6][SCREEN_HEIGHT];
static unsigned char ScreenFlags;

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

    SCREEN_Erase();
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

void SCREEN_Flip(void)
{
    unsigned char temp[SCREEN_WIDTH/6][SCREEN_HEIGHT];

    memcpy(temp, ScreenBuf_BACK, SCREEN_MEM_SIZE);
    memcpy(ScreenBuf_BACK, ScreenBuf_FRONT, SCREEN_MEM_SIZE);
    memcpy(ScreenBuf_FRONT, temp, SCREEN_MEM_SIZE);
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
        }
    }
    LCD_auto_write_stop();
}

void SCREEN_Erase(void)
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
