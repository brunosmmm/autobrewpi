from multiprocessing import Process, Queue, Event
from abpi.gadget.rpcclient import RPCClient
from queue import Empty as QueueEmpty
import time
import uuid
from abpi.util.thread import StoppableThread
import signal
from urllib.error import URLError
import logging


class HbusJsonServerError(Exception):
    pass


class HbusClientRequest:

    _REQUEST_KINDS = ("readobj", "writeobj", "stop")

    def __init__(self, kind, parameters, callback=None, user_data=None):
        self._cb = callback
        self._ud = user_data
        self._kind = kind
        self.uuid = uuid.uuid1()
        self.is_async = False

        if parameters is None:
            self._param = []
        else:
            self._param = parameters

    @property
    def kind(self):
        """Get kind."""
        return self._kind

    @property
    def params(self):
        """Get params."""
        return self._param

    @property
    def userdata(self):
        """Get user data."""
        return self._ud

    def __call__(self, *args, **kwargs):
        """Call."""
        if self._cb is not None:
            self._cb(*args, **kwargs)


class HbusClientResponse:
    def __init__(self, response, uuid, callback=None, user_data=None):
        self.resp = response
        self.cb = callback
        self.ud = user_data
        self.uuid = uuid


class ResponseDispatcher(StoppableThread):
    def __init__(self, async_queue):
        super().__init__()
        self._queue = async_queue

        self._cbwait = {}

    def add_callback(self, req_uuid, cb):
        self._cbwait[req_uuid] = cb

    def run(self):

        while True:
            if self.is_stopped():
                return

            try:
                resp = self._queue.get(False)
                if resp.uuid in self._cbwait:
                    if self._cbwait[resp.uuid] is not None:
                        self._cbwait[resp.uuid](resp.resp, resp.ud)
                        del self._cbwait[resp.uuid]
            except QueueEmpty:
                pass

            time.sleep(0.01)


class HbusClient(object):
    def __init__(self, server_addr="localhost", server_port=7080, timeout=30):

        # request queue
        self._wrqueue = Queue()
        self._rdqueue = Queue()

        # results from read operations
        self._respqueue = Queue()
        self._asyncrespqueue = Queue()

        self._waitqueue = {}

        # stop flag
        self._stop_flag = Event()

        # subprocess
        self._task = Process(
            target=self._process_queue,
            args=(
                self._rdqueue,
                self._wrqueue,
                self._respqueue,
                self._asyncrespqueue,
                server_addr,
                server_port,
                self._stop_flag,
            ),
        )

        self._dispatcher = ResponseDispatcher(self._asyncrespqueue)
        self._timeout = timeout
        self.logger = logging.getLogger("AutoBrew.HBUSCli")

    def start(self):
        self._task.start()
        self._dispatcher.start()

    def stop(self):
        self._dispatcher.stop()
        self._dispatcher.join()
        self._stop_flag.set()
        self._task.join()

    @staticmethod
    def _unpack_response(response):

        if "status" not in response:
            raise IOError("malformed response")

        if response["status"] not in ("ok", "deferred"):
            return None

        response.pop("status")
        return response

    def _put_req_and_wait(self, req, timeout=None):

        self._rdqueue.put(req)
        try:
            resp = self._respqueue.get(timeout=timeout)
        except QueueEmpty:
            self.logger.warning("request timed out")

        time = 0.0
        while resp.uuid != req.uuid:
            self._respqueue.put(resp)
            resp = self._respqueue.get(timeout=timeout)
            time.sleep(0.01)
            time += 0.01
            if timeout is not None and time > timeout:
                self.logger.warning("request timed out")
                raise IOError("timeout")

        return resp.resp

    def _put_async_req(self, req):
        req.is_async = True
        self._dispatcher.add_callback(req.uuid, req)
        # req._cb = None
        self._rdqueue.put(req)

    def _put_and_continue(self, req):
        self._wrqueue.put(req)

    def get_active_busses(self):
        return self._put_req_and_wait(
            HbusClientRequest("buslist", None), self._timeout
        )

    def get_master_state(self):
        return self._put_req_and_wait(
            HbusClientRequest("masterstate", None), self._timeout
        )

    @staticmethod
    def _get_active_busses(client):

        response = client.activebusses()
        response = HbusClient._unpack_response(response)

        return response["list"]

    def get_active_slave_list(self):
        return self._put_req_and_wait(
            HbusClientRequest("slavelist", None), self._timeout
        )

    @staticmethod
    def _get_active_slave_list(client):

        response = client.activeslavelist()
        response = HbusClient._unpack_response(response)

        return response["list"]

    def get_slave_info(self, slave_uid):
        return self._put_req_and_wait(
            HbusClientRequest("slaveinfo", (slave_uid,)), self._timeout
        )

    @staticmethod
    def _get_slave_info(client, slave_uid):

        response = client.slaveinformation(slave_uid)
        response = HbusClient._unpack_response(response)

        return response

    def get_slave_object_list(self, slave_uid):
        return self._put_req_and_wait(
            HbusClientRequest("slaveobjlist", (slave_uid,)), self._timeout
        )

    @staticmethod
    def _get_slave_object_list(client, slave_uid):

        response = client.slaveobjectlist(slave_uid)
        response = HbusClient._unpack_response(response)

        return response["list"]

    def read_slave_object(
        self, slave_addr, object_idx, block=True, callback=None, user_data=None
    ):
        if block:
            return self._put_req_and_wait(
                HbusClientRequest("read", (slave_addr, object_idx)),
                self._timeout,
            )
        else:
            self._put_async_req(
                HbusClientRequest(
                    "read", (slave_addr, object_idx), callback, user_data
                )
            )

    @staticmethod
    def _read_slave_object(client, slave_addr, object_idx):

        client.readobject(slave_addr, object_idx)

        status = HbusClient._unpack_response(client.readfinished())["value"]
        while status is False:
            status = HbusClient._unpack_response(client.readfinished())[
                "value"
            ]

            time.sleep(0.01)

        data = HbusClient._unpack_response(client.retrievelastdata())["value"]
        return data

    def write_slave_object(self, slave_addr, object_idx, value):
        self._put_and_continue(
            HbusClientRequest("write", (slave_addr, object_idx, value))
        )

    @staticmethod
    def _write_slave_object(client, slave_addr, object_idx, value):

        response = client.writeobject(slave_addr, object_idx, value)
        HbusClient._unpack_response(response)

    def check_slaves(self):
        self._put_and_continue(HbusClientRequest("check", None))

    @staticmethod
    def _check_slaves(client):
        client.checkslaves()

    @staticmethod
    def _get_master_state(client):
        response = client.masterstate()
        return HbusClient._unpack_response(response)["value"]

    @staticmethod
    def _process_queue(
        rdqueue,
        wrqueue,
        resp_queue,
        async_queue,
        server_addr,
        server_port,
        stop_flag,
    ):

        signal.signal(signal.SIGINT, signal.SIG_IGN)
        client = RPCClient(server_addr, server_port)

        while True:
            # check for outstanding requests
            try:

                # write separately for more responsiveness
                try:
                    wrtask = wrqueue.get(False)
                    task_kind = wrtask.kind
                    if task_kind == "write":
                        HbusClient._write_slave_object(client, *wrtask.params)
                    elif task_kind == "check":
                        HbusClient._check_slaves(client)
                    elif task_kind == "stop":
                        return
                except (URLError):
                    wrqueue.put(wrtask)
                except QueueEmpty:
                    # proceed to read tasks if empty
                    if stop_flag.is_set():
                        return

                try:
                    task = rdqueue.get(False)
                except QueueEmpty:
                    time.sleep(0.01)
                    continue

                task_kind = task.kind
                task_uuid = task.uuid
                if task.is_async:
                    rqueue = async_queue
                else:
                    rqueue = resp_queue
                try:
                    if task_kind == "buslist":
                        rqueue.put(
                            HbusClientResponse(
                                HbusClient._get_active_busses(client),
                                task.uuid,
                                task,
                                task._ud,
                            )
                        )
                    elif task_kind == "slavelist":
                        rqueue.put(
                            HbusClientResponse(
                                HbusClient._get_active_slave_list(client),
                                task_uuid,
                                task,
                                task._ud,
                            )
                        )
                    elif task_kind == "slaveinfo":
                        rqueue.put(
                            HbusClientResponse(
                                HbusClient._get_slave_info(
                                    client, *task.params
                                ),
                                task_uuid,
                                task,
                                task._ud,
                            )
                        )
                    elif task_kind == "slaveobjlist":
                        rqueue.put(
                            HbusClientResponse(
                                HbusClient._get_slave_object_list(
                                    client, *task.params
                                ),
                                task_uuid,
                                task,
                                task._ud,
                            )
                        )
                    elif task_kind == "read":
                        rqueue.put(
                            HbusClientResponse(
                                HbusClient._read_slave_object(
                                    client, *task.params
                                ),
                                task_uuid,
                                task,
                                task._ud,
                            )
                        )
                    elif task_kind == "masterstate":
                        rqueue.put(
                            HbusClientResponse(
                                HbusClient._get_master_state(
                                    client, *task.params
                                ),
                                task_uuid,
                                task,
                                task._ud,
                            )
                        )
                except (URLError):
                    # try again later
                    rdqueue.put(task)
            except KeyboardInterrupt:
                pass

            time.sleep(0.01)
