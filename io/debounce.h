#ifndef DEBOUNCE_H
#define DEBOUNCE_H

#define DEBOUNCE_COUNT 2

typedef struct DEBOUNCES
{
    unsigned char _counters[8];

    unsigned char _last_state;

    unsigned char current_state;

} DEBOUNCE;

void DEBOUNCE_Init(DEBOUNCE* DStruct);
void DEBOUNCE_UpdState(DEBOUNCE* DStruct, unsigned char bit, unsigned char state);
unsigned char DEBOUNCE_GetStates(DEBOUNCE* DStruct, unsigned char * states);

#endif /* DEBOUNCE_H */
