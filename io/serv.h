#ifndef SERV_H
#define SERV_H

#include <zmq.h>

#define ABU_EVT_KEYPRESS 0x00
#define ABU_EVT_KEYRELEASE 0x01

#define ABU_EVT_QUEUE_SIZE 100

typedef struct ABUEVTS
{
    //type
    unsigned char type;

    //key, other
    unsigned char data;


} ABUEVT;

void ABUSER_trigger_evt(ABUEVT evt);
void* ABUSER_serve(void* data);

#endif /* SERV_H */
