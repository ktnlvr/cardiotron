"""
HTTP handler for captive portal
"""
import io
import select
import socket
from collections import namedtuple
import micropython
from typing import Union, Callable, Dict, List

from logging import log
from net import encode, unquote
from net.tcp import TCP
from net.server import Orchestrator, Protocol, Server, connection, IpSink

class HTTP(Server):
    NL = b"\r\n"
    END = NL + NL

    class Method:
        GET = "GET"
        POST = "POST"

    class ContentType:
        class Value:
            TEXT = b"text/plain"
            HTML = b"text/html"
            FORM = b"application/x-www-form-urlencoded"

        @staticmethod
        def of(ext_or_type: Union[str, bytes]) -> bytes:
            return b"Content-Type: " + encode(ext_or_type) if ext_or_type else b""

    Request = namedtuple("Request", "host method path raw_query query headers body socket_id")

    class Response:
        class Status:
            OK = b"HTTP/1.1 200 OK"
            REDIRECT = b"HTTP/1.1 307 Temporary Redirect"
            NOT_FOUND = b"HTTP/1.1 404 Not Found"

            @staticmethod
            def of(code: int) -> bytes:
                return {
                    200: HTTP.Response.Status.OK,
                    307: HTTP.Response.Status.REDIRECT,
                    404: HTTP.Response.Status.NOT_FOUND,
                }.get(code, HTTP.Response.Status.NOT_FOUND)

        def __init__(self, http, sock):
            self.http: HTTP = http
            self.sock = sock
            self.sent = False

        def send(self, header: Union[bytes, int, List[bytes]], body: Union[bytes, str] = b""):
            if isinstance(header, int):
                header = HTTP.Response.Status.of(header)
            if isinstance(header, list):
                header = HTTP.NL.join(header)

            # Convert body to bytes if it's a string
            body_bytes = encode(body)
            content_length = len(body_bytes)

            # Build response header
            response_parts = [
                header,
                HTTP.NL,
                f"Content-Length: {content_length}".encode(),
                HTTP.NL,
                HTTP.NL
            ]
            header_bytes = b"".join(response_parts)

            log("HTTP Response:", header_bytes.split(HTTP.NL)[0].decode())
            if content_length > 0:
                log("Content length:", content_length)

            # Send response
            self.http.tcp.prepare(self.sock, [header_bytes, body_bytes])
            self.sent = True

        def ok(self, body: Union[bytes, str] = b""):
            self.send(HTTP.Response.Status.OK, body)

        def redirect(self, url: Union[bytes, str]):
            self.send([HTTP.Response.Status.REDIRECT, b"Location: " + encode(url)])

        def html(self, content: Union[bytes, str]):
            self.send([HTTP.Response.Status.OK, b"Content-Type: text/html"], content)

    def __init__(self, orch: Orchestrator, ip_sink: IpSink, routes: Dict[bytes, Union[bytes, Callable]]):
        super().__init__(orch, 80, Protocol.HTTP)
        self.tcp = TCP(orch.poller)
        self.ip_sink = ip_sink
        self.ip = ip_sink.get()
        self.routes = routes
        self.sock.listen(5)
        self.sock.setblocking(False)

    @micropython.native
    def handle(self, sock, event):
        if sock is self.sock:
            self.accept(sock)
        elif event & select.POLLIN:
            self.read(sock)
        elif event & select.POLLOUT:
            self.write(sock)
        else:
            return True

    def accept(self, server_sock):
        try:
            client_sock, addr = server_sock.accept()
            client_sock.setblocking(False)
            client_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.orch.register(connection(self.proto.transport, client_sock), self)
            self.poller.register(client_sock, select.POLLIN)
        except Exception as e:
            log("Socket accept error:", e)
            return

    def parse_request(self, raw_req: bytes):
        header_bytes, body_bytes = raw_req.split(HTTP.END)
        header_lines = header_bytes.split(HTTP.NL)
        req_type, full_path, *_ = header_lines[0].split(b" ")
        path, *rest = full_path.split(b"?", 1)
        raw_query = rest[0] if len(rest) else None
        query = {
            unquote(key): unquote(val)
            for key, val in [param.split(b"=") for param in raw_query.split(b"&")]
        } if raw_query else {}
        headers = {
            key: val for key, val in [line.split(b": ", 1) for line in header_lines[1:]]
        }
        host = headers.get(b"Host", None)
        socket_id = headers.get(b"X-Pico-Fi-Socket-Id", None)
        return HTTP.Request(host, req_type, path, raw_query, query, headers, body_bytes, socket_id)

    def parse_route(self, req: Request):
        prefix = b"/" + (req.path.split(b"/") + [b""])[1]
        return (req.host == self.ip or not self.ip_sink.get()) and self.routes.get(prefix, None)

    def handle_request(self, sock, req: Request):
        res = HTTP.Response(self, sock)
        route = self.parse_route(req)
        if route:
            if isinstance(route, bytes):
                with open(route, "rb") as f:
                    res.html(f.read())
            elif callable(route):
                result = route(req, res)
                if not res.sent:
                    res.ok() if result is None else res.ok(result)

    def read(self, sock):
        request = self.tcp.read(sock)
        if not request:
            self.tcp.end(sock)
        elif request[-4:] == HTTP.END:
            req = self.parse_request(request)
            self.handle_request(sock, req)

    def write(self, sock):
        if self.tcp.write(sock):
            conn = connection.of(sock)
            self.tcp.end(sock)
