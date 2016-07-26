#include "mcp23016.h"
#include "serv.h"
#include "keypad.h"
#include "encoder.h"
#include "switches.h"
#include <pthread.h>
#include <unistd.h>
#include <string.h>

unsigned char stop = 0x00;
unsigned char pin_states[16];

void _iochange(unsigned char * states)
{
    memcpy(pin_states, states, sizeof(unsigned char)*16);
    ENCODER_SetPinStates(pin_states);
    SWITCHES_SetPinStates(pin_states);
}

int main(void)
{

    pthread_t serv_thread;
    int ret = 0;

    MCP_Init(0x20, 0x01, (MCP_IOCHANGE)_iochange);
    KEYPAD_Init();
    ENCODER_Init();
    SWITCHES_Init();

    //server thread
    ret = pthread_create(&serv_thread, 0x00, ABUSER_serve, (void*)(&stop));

    //do stuff here!
    while(1)
    {

        KEYPAD_Cycle();

        usleep(100);
    }

    stop = 0x01;
    pthread_join(serv_thread, 0x00);

    exit(0);
}
