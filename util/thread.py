import threading
import uuid


class StoppableThread(threading.Thread):
    """A stoppable thread
    """
    def __init__(self):
        super(StoppableThread, self).__init__()
        self.stop_flag = threading.Event()

    def stop(self):
        self.stop_flag.set()

    def is_stopped(self):
        return self.stop_flag.isSet()


class CallbackStoppableThread(StoppableThread):
    """A stoppable thread that calls a callback
       when stopped
    """
    def __init__(self, callback):
        super(CallbackStoppableThread, self).__init__()
        self.callback = callback
        self.uuid = uuid.uuid1()

    def stop(self):
        super(CallbackStoppableThread, self).stop()
        if self.callback:
            self.callback(self.uuid)
