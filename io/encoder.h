#ifndef ENCODER_H
#define ENCODER_H

#include "serv.h"

#define ENCODER_BTN_PIN 15
#define ENCODER_A_PIN 13
#define ENCODER_B_PIN 14

//#define ENCODER_BTN_ENABLED

void ENCODER_Init(void);
void ENCODER_Cycle(void);
void ENCODER_SetPinStates(unsigned char * states);

#endif /* ENCODER_H */
