"""RPC client adapter."""

from jsonrpcclient import request


class RPCClient:
    """RPC client."""

    def __init__(self, addr, port):
        """Initialize."""
        self._addr = addr
        self._port = port

    @property
    def address(self):
        """Get address."""
        return self._addr

    @property
    def port(self):
        """Get port."""
        return self._port

    @property
    def fulladdr(self):
        """Get full address."""
        return "http://{}:{}".format(self.address, self.port)

    def __getattribute__(self, name):
        try:
            attr = super().__getattribute__(name)
            return attr
        except AttributeError:
            # we'l try calling
            def _request_wrapper_fn(*args, **kwargs):
                response = request(self.fulladdr, name, *args, **kwargs)
                return response.data.result

            return _request_wrapper_fn
