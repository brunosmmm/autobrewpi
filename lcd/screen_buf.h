#ifndef SCREEN_BUF_H
#define SCREEN_BUF_H

#define SCREEN_WIDTH 240
#define SCREEN_HEIGHT 64
#define LCD_COL_WIDTH 6

#define SCREEN_FLAG_FRONT 0x01
#define SCREEN_FLAG_BACK 0x02

void SCREEN_Init(void);
void SCREEN_PSet(unsigned int x, unsigned int y, unsigned char col);
void SCREEN_Flip(void);
void SCREEN_Draw(void);
void SCREEN_Erase(void);
void SCREEN_Copy(unsigned char* source);

#endif /* SCREEN_BUF_H */
