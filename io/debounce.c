#include "debounce.h"
#include <string.h>
#include <stdio.h>

//#define DEB_DEBUG

void DEBOUNCE_Init(DEBOUNCE* DStruct)
{
    if (!DStruct)
    {
        return;
    }

    memset(DStruct, 0, sizeof(DEBOUNCE));
}

void DEBOUNCE_UpdState(DEBOUNCE* DStruct, unsigned char bit, unsigned char state)
{
    if (!DStruct)
    {
        return;
    }

    if (bit > 7)
    {
        return;
    }

    //check current state
    if (DStruct->_last_state & (1<<bit))
    {
        if (state)
        {
            //increment
            DStruct->_counters[bit]++;
            if (DStruct->_counters[bit] > (DEBOUNCE_COUNT - 1))
            {
                //put status
                #ifdef DEB_DEBUG
                if (!(DStruct->current_state & (1<<bit)))
                {
                    printf("DEBOUNCE: setting bit %d to HIGH\n", bit);
                }
                #endif
                DStruct->current_state |= (1<<bit);
            }
        }
        else
        {
            //zero counter
            DStruct->_counters[bit] = 0;
            DStruct->_last_state &= ~(1<<bit);
        }
    }
    else
    {
        if (state)
        {
            DStruct->_counters[bit] = 0;
            DStruct->_last_state |= (1<<bit);
        }
        else
        {
            DStruct->_counters[bit]++;
            if (DStruct->_counters[bit] > (DEBOUNCE_COUNT - 1))
            {
                #ifdef DEB_DEBUG
                if ((DStruct->current_state & (1<<bit)))
                {
                    printf("DEBOUNCE: setting bit %d to LOW\n", bit);
                }
                #endif
                DStruct->current_state &= ~(1<<bit);
            }
        }
    }
}

unsigned char DEBOUNCE_GetStates(DEBOUNCE* DStruct, unsigned char * states)
{
    if (!DStruct || !states)
    {
        return 0x01;
    }

    *states = DStruct->current_state;

    return 0x00;
}
