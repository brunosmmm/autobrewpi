#include "switches.h"
#include "mcp23016.h"
#include "debounce.h"
#include <string.h>

static DEBOUNCE debounce_sw;
static unsigned char last_state;

void SWITCHES_Init(void)
{

    DEBOUNCE_Init(&debounce_sw);

    MCP_setDirection(SWITCH_1_PIN, MCP_DIRECTION_IN);
    MCP_setDirection(SWITCH_2_PIN, MCP_DIRECTION_IN);
    MCP_setDirection(SWITCH_3_PIN, MCP_DIRECTION_IN);
    MCP_setDirection(SWITCH_4_PIN, MCP_DIRECTION_IN);
    MCP_setDirection(SWITCH_5_PIN, MCP_DIRECTION_IN);

    last_state = 0x00;

}

void SWITCHES_SetPinStates(unsigned char* state)
{
    unsigned char pin_states[16];
    unsigned char debounced_states;
    unsigned int i;
    ABUEVT event;

    if (!state)
    {
        return;
    }

    memcpy(pin_states, state, sizeof(unsigned char)*16);

    //debounce
    DEBOUNCE_UpdState(&debounce_sw, 0x00, pin_states[SWITCH_1_PIN]);
    DEBOUNCE_UpdState(&debounce_sw, 0x01, pin_states[SWITCH_2_PIN]);
    DEBOUNCE_UpdState(&debounce_sw, 0x02, pin_states[SWITCH_3_PIN]);
    DEBOUNCE_UpdState(&debounce_sw, 0x03, pin_states[SWITCH_4_PIN]);
    DEBOUNCE_UpdState(&debounce_sw, 0x04, pin_states[SWITCH_5_PIN]);
    DEBOUNCE_GetStates(&debounce_sw, &debounced_states);

    //generate events
    for (i = 0; i < 5; i++)
    {
        if (debounced_states & (1<<i))
        {
            if (!(last_state & (1<<i)))
            {
                //switch press event
                event.unit = ABU_UNIT_SWITCHES;
                event.type = ABU_EVT_SWPRESS;
                event.data = i;
                ABUSER_trigger_evt(event);
            }
        }
        else
        {
            if (last_state & (1<<i))
            {
                //switch release event
                event.unit = ABU_UNIT_SWITCHES;
                event.type = ABU_EVT_SWRELEASE;
                event.data = i;
                ABUSER_trigger_evt(event);
            }
        }
    }

    //save state
    last_state = debounced_states;
}
