#include "keypad.h"
#include "mcp23016.h"
#include <unistd.h>
#include <stdio.h>

static unsigned int active_row = 0;
static unsigned char * active_key = 0x00;
static unsigned char active_key_row, active_key_col;
unsigned int keypad_row_pins[KEYPAD_ROWS] = {6, 5, 4, 3};
unsigned int keypad_col_pins[KEYPAD_COLS] = {2, 1, 0};

unsigned char keypad_keys[KEYPAD_ROWS][KEYPAD_COLS] = {
    {'1', '2', '3'},
    {'4', '5', '6'},
    {'7', '8', '9'},
    {'*', '0', '#'}
};

static void _set_rows(void)
{
    unsigned char pin_states[16];
    unsigned int i;

    for(i = 0; i < 16; i++)
    {
        pin_states[i] = MCP_STATE_NONE;
    }

    for (i = 0; i < KEYPAD_ROWS; i++)
    {
        if (i == active_row)
        {
            pin_states[keypad_row_pins[i]] = MCP_STATE_HIGH;
        }
        else
        {
            pin_states[keypad_row_pins[i]] = MCP_STATE_LOW;
        }
    }

    MCP_writePins(pin_states);
}

static void _get_cols(unsigned char * col_state)
{
    unsigned int i;
    unsigned char pin_states[16];
    MCP_readPins(0x01, pin_states);

    for (i = 0; i < KEYPAD_COLS; i++)
    {
        if (pin_states[keypad_col_pins[i]])
        {
            col_state[i] = 0x01;
        }
        else
        {
            col_state[i] = 0x00;
        }
    }
}

static void _detect_key(unsigned char * col_state)
{
    unsigned int i;
    int active_col = -1;
    ABUEVT event;
    for (i = 0; i < KEYPAD_COLS; i++)
    {
        if (col_state[i])
        {
            active_col = i;
            break;
        }
    }

    if (active_col < 0)
    {
        if (active_key)
        {
            if (active_key_row == active_row)
            {
                event.unit = ABU_UNIT_KEYPAD;
                event.type = ABU_EVT_KEYRELEASE;
                event.data = keypad_keys[active_key_row][active_key_col];
                ABUSER_trigger_evt(event);

                //release
                //printf("detected key release\n");
                active_key_col = 0;
                active_key_row = 0;
                active_key = 0x00;
            }
        }

        return;
    }

    if (!active_key)
    {
        active_key = &(keypad_keys[active_row][active_col]);
        active_key_col = active_col;
        active_key_row = active_row;

        //trigger event
        event.unit = ABU_UNIT_KEYPAD;
        event.type = ABU_EVT_KEYPRESS;
        event.data = keypad_keys[active_row][active_col];

        ABUSER_trigger_evt(event);
    }

}

void KEYPAD_Init(void)
{
    unsigned int i;
    active_row = 0;

    for (i = 0; i < KEYPAD_ROWS; i++)
    {
        MCP_setDirection(keypad_row_pins[i], MCP_DIRECTION_OUT);
    }

    for (i = 0; i < KEYPAD_COLS; i++)
    {
        MCP_setDirection(keypad_col_pins[i], MCP_DIRECTION_IN);
    }

}

static void _keypad_internal_cycle(unsigned char async, unsigned char * states)
{
    unsigned char col_state[KEYPAD_COLS];
    _set_rows();

    usleep(10);

    _get_cols(col_state);

    //detect
    _detect_key(col_state);

    active_row++;
    if (active_row > (KEYPAD_ROWS - 1))
    {
        active_row = 0;
    }

}

void KEYPAD_Cycle(void)
{
    _keypad_internal_cycle(0x00, 0x00);
}

void KEYPAD_SetPinStates(unsigned char * states)
{
    _keypad_internal_cycle(0x01, states);
}
