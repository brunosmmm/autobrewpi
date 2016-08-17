from pyjsonrpc import HttpClient
from collections import deque
from multiprocessing import Process, Queue
import time
import uuid

class HbusJsonServerError(Exception):
    pass

class HbusClientRequest(object):

    _REQUEST_KINDS = ('readobj', 'writeobj', 'stop')

    def __init__(self, kind, parameters, callback=None):
        self._cb = callback
        self.kind = kind
        self.uuid = uuid.uuid1()

        if parameters is None:
            self.param = []
        else:
            self.param = parameters

    def get_kind(self):
        return self.kind

    def get_params(self):
        return self.param

    def get_cb(self):
        return self._cb

class HbusClientResponse(object):
    def __init__(self, response, uuid):
        self.resp = response
        self.uuid = uuid

class HbusClient(object):

    def __init__(self, server_addr='localhost', server_port=7080):

        #request queue
        self._queue = Queue()
        self._respqueue = Queue()

        self._waitqueue = {}

        #subprocess
        self._task = Process(target=self._process_queue, args=(self._queue, self._respqueue, server_addr, server_port))

    def start(self):
        self._task.start()

    def stop(self):
        self._queue.put(HbusClientRequest('stop', None))
        self._task.join()

    @staticmethod
    def _unpack_response(response):

        if 'status' not in response:
            raise IOError('malformed response')

        if response['status'] not in ('ok', 'deferred'):
            raise HbusJsonServerError('error: {}'.format(response['error']))

        response.pop('status')
        return response

    def _put_req_and_wait(self, req):

        self._queue.put(req)
        resp = self._respqueue.get(timeout=1)
        while resp.uuid != req.uuid:
            self._respqueue.put(resp)
            resp = self._respqueue.get()

        return resp.resp

    def _put_async_req(self, req):
        self._queue.put(req)
        self._waitqueue[req.uuid] = req._cb

    def get_active_busses(self):
        return self._put_req_and_wait(HbusClientRequest('buslist', None))

    @staticmethod
    def _get_active_busses(client):

        response = client.activebusses()
        response = HbusClient._unpack_response(response)

        return response['list']

    def get_active_slave_list(self):
        return self._put_req_and_wait(HbusClientRequest('slavelist', None))

    @staticmethod
    def _get_active_slave_list(client):

        response = client.activeslavelist()
        response = HbusClient._unpack_response(response)

        return response['list']

    def get_slave_info(self, slave_uid):
        return self._put_req_and_wait(HbusClientRequest('slaveinfo', (slave_uid,)))

    @staticmethod
    def _get_slave_info(client, slave_uid):

        response = client.slaveinformation(slave_uid)
        response = HbusClient._unpack_response(response)

        return response

    def get_slave_object_list(self, slave_uid):
        return self._put_req_and_wait(HbusClientRequest('slaveobjlist', (slave_uid,)))

    @staticmethod
    def _get_slave_object_list(client, slave_uid):

        response = client.slaveobjectlist(slave_uid)
        response = HbusClient._unpack_response(response)

        return response['list']

    def read_slave_object(self, slave_addr, object_idx, block=True, callback=None):
        if block:
            return self._put_req_and_wait(HbusClientRequest('read', (slave_addr, object_idx)))
        else:
            self._put_async_req(HbusClientRequest('read', (slave_addr, object_idx), callback))

    @staticmethod
    def _read_slave_object(client, slave_addr, object_idx):

        client.readobject(slave_addr, object_idx)

        status = HbusClient._unpack_response(client.readfinished())['value']
        while status is False:
            status = HbusClient._unpack_response(client.readfinished())['value']

            time.sleep(0.01)

        data = HbusClient._unpack_response(client.retrievelastdata())['value']
        return data

    def write_slave_object(self, slave_addr, object_idx, value):
        self._queue.put(HbusClientRequest('write', (slave_addr, object_idx, value)))

    @staticmethod
    def _write_slave_object(client, slave_addr, object_idx, value):

        response = client.writeobject(slave_addr, object_idx, value)
        HbusClient._unpack_response(response)

    def check_slaves(self):
        self._queue.put(HbusClientRequest('check', None))

    @staticmethod
    def _check_slaves(client):
        client.checkslaves()

    @staticmethod
    def _process_queue(queue, resp_queue, server_addr, server_port):

        client = HttpClient('http://{}:{}'.format(server_addr, server_port))

        while True:
            #check for outstanding requests
            task = queue.get()

            task_kind = task.get_kind()
            task_uuid = task.uuid
            if task_kind == 'stop':
                break
            elif task_kind == 'buslist':
                resp_queue.put(HbusClientResponse(HbusClient._get_active_busses(client), task.uuid))
            elif task_kind == 'slavelist':
                resp_queue.put(HbusClientResponse(HbusClient._get_active_slave_list(client), task_uuid))
            elif task_kind == 'slaveinfo':
                resp_queue.put(HbusClientResponse(HbusClient._get_slave_info(client, *task.get_params()), task_uuid))
            elif task_kind == 'slaveobjlist':
                resp_queue.put(HbusClientResponse(HbusClient._get_slave_object_list(client, *task.get_params()), task_uuid))
            elif task_kind == 'read':
                resp_queue.put(HbusClientResponse(HbusClient._read_slave_object(client, *task.get_params()), task_uuid))
            elif task_kind == 'write':
                HbusClient._write_slave_object(client, *task.get_params())
            elif task_kind == 'check':
                HbusClient._check_slaves(client)

            time.sleep(0.01)
