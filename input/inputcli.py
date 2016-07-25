from util.thread import StoppableThread
import struct
import time
import zmq

class ABInputClient(StoppableThread):
    def __init__(self):
        super(ABInputClient, self).__init__()

    def run(self):

        context = zmq.Context()
        socket = context.socket(zmq.SUB)
        socket.connect('tcp://localhost:5556')
        socket.setsockopt_string(zmq.SUBSCRIBE, u'KEYPAD')

        print 'icli: connected'

        while True:

            if self.is_stopped():
                exit(0)

            #communicate!
            try:
                string = socket.recv_string(flags=zmq.NOBLOCK)
                print 'received some stuff'

                _, kind, data = string.split(' ')

                print 'received: type = {}; data = {}'.format(kind, data)
            except zmq.ZMQError:
                pass

            time.sleep(0.1)
