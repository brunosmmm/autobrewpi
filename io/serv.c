#include "serv.h"
#include <unistd.h>
#include <pthread.h>
#include <stdio.h>

static ABUEVT evt_queue[ABU_EVT_QUEUE_SIZE];
static unsigned int read_ptr, write_ptr;
static pthread_mutex_t lock = PTHREAD_MUTEX_INITIALIZER;

void ABUSER_Init(void)
{
    read_ptr = 0;
    write_ptr = 0;
}

void ABUSER_trigger_evt(ABUEVT evt)
{
    pthread_mutex_lock(&lock);
    evt_queue[write_ptr++] = evt;

    if (write_ptr > (ABU_EVT_QUEUE_SIZE - 1))
    {
        //wrap around
        write_ptr = 0;
    }
    pthread_mutex_unlock(&lock);

}

static ABUEVT _read_queue(void)
{
    ABUEVT result;
    pthread_mutex_lock(&lock);
    result = evt_queue[read_ptr++];

    if (read_ptr > (ABU_EVT_QUEUE_SIZE - 1))
    {
        //wrap
        read_ptr = 0;
    }
    pthread_mutex_unlock(&lock);

    return result;
}

static unsigned int _read_queue_len(void)
{
    if (write_ptr >= read_ptr)
    {
        return write_ptr - read_ptr;
    }

    return ABU_EVT_QUEUE_SIZE - read_ptr + write_ptr;
}

void* ABUSER_serve(void* data)
{
    void* context = zmq_ctx_new();
    void* publisher = zmq_socket(context, ZMQ_PUB);
    int rc = zmq_bind(publisher, "tcp://127.0.0.1:5556");
    ABUEVT event;
    char message[16];

    ABUSER_Init();

    if (rc != 0)
    {
        printf("something went wrong with ZMQ\n");
    }

    while(1)
    {

        if (*(unsigned char*)data)
        {
            return 0;
        }

        //check for data in queue
        if (_read_queue_len() > 0)
        {
            //do stuff!!
            event = _read_queue();
            sprintf(message, "KEYPAD %d %c", event.type, event.data);
            zmq_send (publisher, message, 10, 0);
        }

        usleep(10000);

    }

    return 0;
}
