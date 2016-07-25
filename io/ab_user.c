#include "mcp23016.h"
#include "serv.h"
#include "keypad.h"
#include <pthread.h>
#include <unistd.h>

unsigned char stop = 0x00;

int main(void)
{

    pthread_t serv_thread;
    int ret = 0;

    MCP_Init(0x20, 0x01);
    KEYPAD_Init();

    //server thread
    ret = pthread_create(&serv_thread, 0x00, ABUSER_serve, (void*)(&stop));

    //do stuff here!
    while(1)
    {

        KEYPAD_Cycle();

        usleep(10000);
    }

    stop = 0x01;
    pthread_join(serv_thread, 0x00);

    exit(0);
}
