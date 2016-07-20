from pyjsonrpc import HttpClient
from collections import deque

class HbusJsonServerError(Exception):
    pass

class HbusClientRequest(object):

    _REQUEST_KINDS = ('readobj')

    def __init__(self, kind, parameters, callback=None):
        self._cb = callback
        self.kind = kind
        self.param = parameters

class HbusClient(object):

    def __init__(self, server_addr='localhost', server_port=7080):

        self._cli = HttpClient('http://{}:{}'.format(server_addr, server_port))

        #request queue
        self._queue = deque()

    def _unpack_response(self, response):

        if 'status' not in response:
            raise IOError('malformed response')

        if response['status'] not in ('ok', 'deferred'):
            raise HbusJsonServerError('error: {}'.format(response['error']))

        response.pop('status')
        return response

    def get_active_busses(self):

        response = self._cli.activebusses()
        response = self._unpack_response(response)

        return response['list']

    def get_active_slave_list(self):

        response = self._cli.activeslavelist()
        response = self._unpack_response(response)

        return response['list']

    def get_slave_info(self, slave_uid):

        response = self._cli.slaveinformation(slave_uid)
        response = self._unpack_response(response)

        return response

    def get_slave_object_list(self, slave_uid):

        response = self._cli.slaveobjectlist(slave_uid)
        response = self._unpack_response(response)

        return response['list']

    def read_slave_object(self, slave_addr, object_idx, block=True, callback=None):

        self._cli.readobject(slave_addr, object_idx)

        if block:
            status = self._unpack_response(self._cli.readfinished())['value']
            while status is False:
                status = self._unpack_response(self._cli.readfinished())['value']

            data = self._unpack_response(self._cli.retrievelastdata())['value']
            return data

        #non blocking
        #req = HbusClientRequest('readobj',
        #                        parameters={'slave_addr': slave_addr,
        #                                    'object_idx': object_idx},
        #                        callback=callback)
        #req = HbusClientRequest('readobj', callback=callback)
        #self._queue.appendleft(req)
        raise NotImplementedError('must block for now')

    def write_slave_object(self, slave_addr, object_idx, value):

        response = self._cli.writeobject(slave_addr, object_idx, value)
        self._unpack_response(response)

    def _process_queue(self):

        #check for outstanding requests
        if len(self._queue) > 0:
            pass
