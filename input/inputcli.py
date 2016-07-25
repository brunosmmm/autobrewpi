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
        socket.setsockopt_string(zmq.SUBSCRIBE, u'ENCODER')

        print 'icli: connected'

        while True:

            if self.is_stopped():
                exit(0)

            #communicate!
            try:
                string = socket.recv_string(flags=zmq.NOBLOCK)

                unit, kind, data = string.split(' ')

                print 'received: unit={}; type = {}; data = {}'.format(unit, kind, data)
            except zmq.ZMQError:
                pass

            time.sleep(0.1)
