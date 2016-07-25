#ifndef KEYPAD_H
#define KEYPAD_H

#include "serv.h"

#define KEYPAD_ROWS 4
#define KEYPAD_COLS 3


void KEYPAD_Init(void);
void KEYPAD_Cycle(void);
void KEYPAD_SetPinStates(unsigned char * pin_states);


#endif /* KEYPAD_H */
