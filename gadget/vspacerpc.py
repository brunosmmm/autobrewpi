import pyjsonrpc
from util.thread import StoppableThread

def make_json_server(rpc_request_fn):

    class VSpaceRPCServer(pyjsonrpc.HttpRequestHandler):

        _rpc_req = rpc_request_fn

        @pyjsonrpc.rpcmethod
        def get_variable_value(self, port_id):
            val = self._rpc_req('getval',
                                port_id=port_id)

            if val is None:
                return {'status': 'error'}

            return {'status': 'ok',
                    'data': val}

        @pyjsonrpc.rpcmethod
        def get_port_info(self, port_id):
            val = self._rpc_req('portinfo',
                                 port_id=port_id)

            if val is None:
                return {'status': 'error'}

            return {'status': 'ok',
                    'data': val}

        @pyjsonrpc.rpcmethod
        def find_port_id(self, instance_name, port_name, port_direction):
            val = self._rpc_req('findport',
                                instance_name=instance_name,
                                port_name=port_name,
                                port_direction=port_direction)

            if val is None:
                return {'status': 'error'}

            return {'status': 'ok',
                    'data': val}

        @pyjsonrpc.rpcmethod
        def get_port_list(self):
            return {'status': 'ok',
                    'data': self._rpc_req('portlist')}

        @pyjsonrpc.rpcmethod
        def get_connection_matrix(self):
            return {'status': 'ok',
                    'data': self._rpc_req('matrix')}

        @pyjsonrpc.rpcmethod
        def call_driver_method(self, instance_name, method_name, **kwargs):
            try:
                val = self._rpc_req('call',
                                    instance_name,
                                    method_name,
                                    **kwargs)
            except Exception:
                return {'status': 'error'}

            return {'status': 'ok',
                    'data': val}

    return VSpaceRPCServer

class VSpaceRPCController(StoppableThread):

    def __init__(self, rpc_request_fn):
        super(VSpaceRPCController, self).__init__()
        self._rpc_req = rpc_request_fn
        self._server = None

    def stop(self):
        super(VSpaceRPCController, self).stop()
        if self._server is not None:
            self._server.shutdown()

    def run(self):

        def _handle_sigterm(*args):
            self.stop()

        server_class = make_json_server(self._rpc_req)
        self._server = pyjsonrpc.ThreadingHttpServer(server_address=('', 7090),
                                                     RequestHandlerClass=server_class)

        self._server.serve_forever()
