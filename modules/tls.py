# -*- coding: utf-8 -*-
"""SSL context for the built-in server that cannot be stalled by one client.

Werkzeug wraps the listening socket, so the TLS handshake runs inside accept()
in the server's main thread, with no timeout. A client that opens a connection
and never finishes the handshake (port scanners do this) blocks accept()
forever and the whole server stops answering. Here every accepted socket gets
a timeout before the handshake, so such a client is dropped after a few
seconds and the server goes on.
"""

import socket
import ssl

# Seconds a client gets to finish the TLS handshake
HANDSHAKE_TIMEOUT = 10
# Seconds of silence allowed while reading a request or sending a response
CONNECTION_TIMEOUT = 60


class _TimeoutSSLSocket(ssl.SSLSocket):
    def accept(self):
        newsock, addr = socket.socket.accept(self)
        newsock.settimeout(HANDSHAKE_TIMEOUT)
        # On a failed handshake wrap_socket closes the socket and raises
        # OSError; socketserver ignores OSError from accept and goes on
        newsock = self.context.wrap_socket(
            newsock,
            do_handshake_on_connect=self.do_handshake_on_connect,
            suppress_ragged_eofs=self.suppress_ragged_eofs,
            server_side=True)
        newsock.settimeout(CONNECTION_TIMEOUT)
        return newsock, addr


def server_context(certfile, keyfile):
    """The same context Werkzeug builds from a (cert, key) tuple, with timeouts."""
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(certfile, keyfile)
    context.sslsocket_class = _TimeoutSSLSocket
    return context
