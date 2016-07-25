#include "encoder.h"
#include "mcp23016.h"
#include "debounce.h"
#include <string.h>

static unsigned char button_state = 0x00;
static unsigned char a_state = 0x00;
static unsigned char b_state = 0x00;

static DEBOUNCE debounce_ab;

void ENCODER_Init(void)
{
    unsigned char pin_states[16];
    button_state = 0x00;

    DEBOUNCE_Init(&debounce_ab);

    MCP_setDirection(ENCODER_BTN_PIN, MCP_DIRECTION_IN);
    MCP_setDirection(ENCODER_A_PIN, MCP_DIRECTION_IN);
    MCP_setDirection(ENCODER_B_PIN, MCP_DIRECTION_IN);

    //read
    MCP_readPins(0x01, pin_states);

    a_state = pin_states[ENCODER_A_PIN];
    b_state = pin_states[ENCODER_B_PIN];
}

static void _encoder_internal_cycle(unsigned char async, unsigned char * states)
{
    unsigned char pin_states[16];
    unsigned char debounced_states;
    ABUEVT event;

    if (!async)
    {
        MCP_readPins(0x01, pin_states);
    }
    else
    {
        memcpy(pin_states, states, sizeof(unsigned char)*16);
    }

    //debounce
    DEBOUNCE_UpdState(&debounce_ab, 0x00, pin_states[ENCODER_A_PIN]);
    DEBOUNCE_UpdState(&debounce_ab, 0x01, pin_states[ENCODER_B_PIN]);
    DEBOUNCE_GetStates(&debounce_ab, &debounced_states);

    //check button
    if (!pin_states[ENCODER_BTN_PIN])
    {
        if (!button_state)
        {
            //button press
            button_state = 0x01;

            event.unit = ABU_UNIT_ENCODER;
            event.type = ABU_EVT_ENCPRESS;
            event.data = 0x00;
            ABUSER_trigger_evt(event);
        }
    }
    else
    {
        if (button_state)
        {
            //button release
            button_state = 0x00;

            event.unit = ABU_UNIT_ENCODER;
            event.type = ABU_EVT_ENCRELEASE;
            event.data = 0x00;
            ABUSER_trigger_evt(event);
        }
    }

    //check encoder position
    if ((!(debounced_states & 0x01)) && a_state)
    {
        if (debounced_states & 0x02)
        {
            event.unit = ABU_UNIT_ENCODER;
            event.type = ABU_EVT_ENCCW;
            event.data = 0x00;
            ABUSER_trigger_evt(event);
        }
        else
        {
            event.unit = ABU_UNIT_ENCODER;
            event.type = ABU_EVT_ENCCCW;
            event.data = 0x00;
            ABUSER_trigger_evt(event);
        }
    }

    a_state = (debounced_states & 0x01);
}

void ENCODER_SetPinStates(unsigned char * states)
{
    _encoder_internal_cycle(0x01, states);
}

void ENCODER_Cycle(void)
{
    _encoder_internal_cycle(0x00, 0x00);
}
