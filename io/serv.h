#ifndef SERV_H
#define SERV_H

#include <zmq.h>

//units
#define ABU_UNIT_KEYPAD 0x00
#define ABU_UNIT_ENCODER 0x01
#define ABU_UNITNAME_KEYPAD "KEYPAD"
#define ABU_UNITNAME_ENCODER "ENCODER"

//keypad
#define ABU_EVT_KEYPRESS 0x00
#define ABU_EVT_KEYRELEASE 0x01

//encoder
#define ABU_EVT_ENCPRESS 0x00
#define ABU_EVT_ENCRELEASE 0x03
#define ABU_EVT_ENCCW 0x01
#define ABU_EVT_ENCCCW 0x02

#define ABU_EVT_QUEUE_SIZE 100

typedef struct ABUEVTS
{
    //unit
    unsigned char unit;
    //type
    unsigned char type;

    //key, other
    unsigned char data;


} ABUEVT;

void ABUSER_trigger_evt(ABUEVT evt);
void* ABUSER_serve(void* data);

#endif /* SERV_H */
