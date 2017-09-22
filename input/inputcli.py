from util.thread import StoppableThread
import time
import zmq
import uuid

_INPUT_EVENTS = {
    'encoder.cw': ('ENCODER', 0x01),
    'encoder.ccw': ('ENCODER', 0x02),
    'encoder.press': ('ENCODER', 0x00),
    'encoder.release': ('ENCODER', 0x03),
    'keypad.press': ('KEYPAD', 0x00),
    'keypad.release': ('KEYPAD', 0x01),
    'switches.press': ('SWITCHES', 0x00),
    'switches.release': ('SWITCHES', 0x01)
}


class InvalidEventError(Exception):
    pass


class ABInputClient(StoppableThread):
    def __init__(self):
        super(ABInputClient, self).__init__()

        self.attached_callbacks = {}

    def attach_callback(self, event, callback):

        if event not in _INPUT_EVENTS:
            raise InvalidEventError('invalid event!')

        if event not in self.attached_callbacks:
            self.attached_callbacks[event] = []

        self.attached_callbacks[event].append(callback)

    def run(self):

        context = zmq.Context()
        socket = context.socket(zmq.SUB)
        socket.connect('tcp://localhost:5556')
        socket.setsockopt_string(zmq.SUBSCRIBE, 'KEYPAD')
        socket.setsockopt_string(zmq.SUBSCRIBE, 'ENCODER')
        socket.setsockopt_string(zmq.SUBSCRIBE, 'SWITCHES')

        while True:

            if self.is_stopped():
                exit(0)

            # communicate!
            try:
                string = socket.recv_string(flags=zmq.NOBLOCK)

                unit, kind, data = string.split(' ')

                for event_type, conditions in _INPUT_EVENTS.items():
                    if conditions[0] == unit and conditions[1] == int(kind):
                        try:
                            for cb in self.attached_callbacks[event_type]:
                                if cb is not None:
                                    cb(data, uuid.uuid1())
                        except KeyError:
                            pass

            except zmq.ZMQError:
                pass

            time.sleep(0.1)
