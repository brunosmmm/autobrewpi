#ifndef SWITCHES_H
#define SWITCHES_H

#include "serv.h"

#define SWITCH_1_PIN 8
#define SWITCH_2_PIN 9
#define SWITCH_3_PIN 10
#define SWITCH_4_PIN 11
#define SWITCH_5_PIN 12

void SWITCHES_Init(void);
void SWITCHES_SetPinStates(unsigned char * state);

#endif /* SWITCHES_H */
