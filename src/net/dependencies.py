"""
Combined network dependencies: TCP, Server needs, and HTTP handler heavily based on 'cfreshman's implementation of a captive portal
https://github.com/cfreshman/pico-fi
"""
import gc
import io
import select
import socket
from collections import namedtuple
import micropython
from logging import eth_log
from net import encode, unquote, defaulter_dict, enumstr

class TCP:
    """TCP stream handler"""

    MSS = 536

    class Writer(namedtuple("Writer", ["data", "buff", "buffmv", "range"])): # type: ignore
        pass

    def __init__(self, poller):
        self._poller = poller
        self._reads = {}
        self._writes = defaulter_dict()

    def read(self, sock):
        """Read data from socket"""
        sid = id(sock)
        try:
            current_data = self._reads.get(sid, b"")
            new_data = sock.read()
            if new_data is None:
                request = current_data
            else:
                request = current_data + new_data
            self._reads[sid] = request
        except OSError as e:
            eth_log(f"TCP read error on sock {sid}: {e}")
            request = b""
            self.end(sock)
        return request

    def prepare(self, sock, data):
        """Prepare data for transmission"""
        buff = bytearray(TCP.MSS)
        sid = id(sock)
        writers = self._writes.get(sid, [])
        if not isinstance(data, list):
             data = [data]
        byte_data = [d.encode('utf-8') if isinstance(d, str) else d for d in data]

        writers.append(
            TCP.Writer(io.BytesIO(b"".join(byte_data)), buff, memoryview(buff), [0, 0])
        )
        self._writes[sid] = writers
        self._poller.modify(sock, select.POLLOUT)

    def write(self, sock):
        """Write next packet, return True if all packets written"""
        sid = id(sock)
        writers = self._writes.get(sid, [])
        if not writers:
            return True
        curr = writers[0]

        try:
            if curr.range[0] < curr.range[1]:
                 bytes_to_write = curr.buffmv[curr.range[0]:curr.range[1]]
                 bytes_written = sock.write(bytes_to_write)
                 if bytes_written is None:
                     return False
                 curr.range[0] += bytes_written
                 if curr.range[0] < curr.range[1]:
                     return False
                 curr.range[0] = curr.range[1] = 0

            data = curr.data.read(TCP.MSS)
            if not data:
                writers.pop(0)
                self._writes[sid] = writers
                if not writers:
                     self._poller.modify(sock, select.POLLIN)
                     return True
                else:
                    return False

            curr.buff[: len(data)] = data
            curr.range[1] = len(data)
            curr.range[0] = 0

            bytes_written = sock.write(curr.buffmv[:curr.range[1]])
            if bytes_written is None:
                return False
            curr.range[0] = bytes_written

            if curr.range[0] < curr.range[1]:
                return False

            curr.range[0] = curr.range[1] = 0

        except OSError as e:
            eth_log(f"TCP write error on sock {sid}: {e}")
            if writers and curr == writers[0]:
                writers.pop(0)
            self._writes[sid] = writers
            self.end(sock)
            return True

        return False

    def clear(self, sock):
        """Clear stored data for socket"""
        sid = id(sock)
        if sid in self._reads:
            del self._reads[sid]
        if sid in self._writes:
            del self._writes[sid]
        gc.collect()

    def end(self, sock):
        """Close socket and clean up"""
        sid = id(sock)
        try:
            self._poller.unregister(sock)
        except OSError as e:
            if e.errno != 9:
                 eth_log(f"Error unregistering socket {sid}: {e}")
        except ValueError:
             pass
        except Exception as e:
             eth_log(f"Unexpected error unregistering socket {sid}: {e}")

        try:
            sock.close()
        except OSError as e:
             if e.errno != 9:
                 eth_log(f"Error closing socket {sid}: {e}")
        except Exception as e:
             eth_log(f"Unexpected error closing socket {sid}: {e}")

        self.clear(sock)



class SocketPollHandler:
    """handle events from a pool of sockets registered to a poller"""

    def __init__(self, poller: select.poll, name: str):
        self.poller: select.poll = poller
        self.name = name

    def __repr__(self):
        return f"<handler {self.name}>"

class transport(enumstr):
    def __init__(self, value, sock_type):
        super().__init__(value)
        self.sock_type = sock_type

class Transport:
    UDP = transport(b"UDP", socket.SOCK_DGRAM)
    TCP = transport(b"TCP", socket.SOCK_STREAM)

    @staticmethod
    def of(sock_type: int):
        return {socket.SOCK_DGRAM: Transport.UDP, socket.SOCK_STREAM: Transport.TCP}.get(sock_type)

class connection:
    _instances: dict[int, 'connection'] = {}

    def __init__(self, tran: transport, sock: socket.socket | None = None):
        self.tran = tran
        if not sock:
            sock = socket.socket(socket.AF_INET, tran.sock_type)
        self.sock = sock
        connection._instances[id(sock)] = self

    def __repr__(self):
        sock_id = id(self.sock)
        return f"<connection {self.tran} {sock_id}>"

    def __hash__(self):
        return id(self.sock)

    @staticmethod
    def of(sock: socket.socket):
        return connection._instances.get(id(sock))

    @staticmethod
    def remove(sock: socket.socket):
         sid = id(sock)
         if sid in connection._instances:
             del connection._instances[sid]

class protocol(enumstr):
    _transports: dict['protocol', transport] = {}

    def __init__(self, value, transport_instance: transport):
        super().__init__(value)
        if self in self._transports:
            if self._transports[self] != transport_instance:
                raise Exception(
                    f"Multiple transports ({self._transports[self]}, {transport_instance}) for protocol {self}"
                )
        else:
            self._transports[self] = transport_instance

    @property
    def transport(self):
         return self._transports.get(self)


class Protocol:
    DNS = protocol(b"DNS", Transport.UDP)
    HTTP = protocol(b"HTTP", Transport.TCP)
    WebSocket = protocol(b"WebSocket", Transport.TCP)


class Orchestrator(SocketPollHandler):
    """direct socket events through registered handlers"""

    def __init__(self, poller: select.poll):
        super().__init__(poller, "Orchestrator")
        self.handlers: dict[connection | protocol | transport, SocketPollHandler | protocol | transport] = {}


    def register(
        self,
        key: connection | protocol | transport,
        handler: SocketPollHandler | protocol | transport,
    ):
         """Register a handler for a connection, protocol, or transport."""
         if not isinstance(key, (connection, protocol, transport)):
             raise TypeError("Registration key must be a connection, protocol, or transport instance.")
         if not isinstance(handler, (SocketPollHandler, protocol, transport)):
            raise TypeError("Handler must be a SocketPollHandler, protocol, or transport instance.")

         self.handlers[key] = handler

    def unregister(
        self,
        key: connection | protocol | transport,
        handler: SocketPollHandler | protocol | transport | None = None,
    ):
        """Unregister a handler associated with a key.
        If handler is provided, only unregister if it matches.
        If handler is None, unregister whatever handler is associated with the key.
        """
        registered_handler = self.handlers.get(key)
        if registered_handler:
             if handler is None or registered_handler == handler:
                 del self.handlers[key]

    def handle(self, sock: socket.socket, event):
        conn = connection.of(sock)
        if not conn:
            try:
                self.poller.unregister(sock)
            except Exception as e:
                 eth_log(f"Orchestrator: Error unregistering dead socket {id(sock)}: {e}")
            return True

        handler = self.handlers.get(conn)

        if handler is None and hasattr(conn, 'proto') and conn.proto:
            handler = self.handlers.get(conn.proto)

        if handler is None:
            handler = self.handlers.get(conn.tran)

        while isinstance(handler, (protocol, transport)):
             handler_key = handler
             handler = self.handlers.get(handler_key)
             if handler is None:
                  eth_log(f"Orchestrator: Handler resolution failed. No handler registered for key {handler_key}")
                  break
             if handler == handler_key:
                  eth_log(f"Orchestrator: Handler resolution cycle detected for key {handler_key}")
                  handler = None
                  break

        if isinstance(handler, SocketPollHandler):
             try:
                 handled = handler.handle(sock, event)
                 if handled:
                     connection.remove(sock)
                     return True
                 else:
                     return False
             except Exception as e:
                 eth_log(f"Orchestrator: Error in handler {handler.name} for {conn}: {e}")
                 connection.remove(sock)
                 try:
                      if hasattr(handler, 'end'):
                          handler.end(sock)
                      elif hasattr(handler, 'stop'):
                          handler.stop(sock)
                      else:
                          try:
                              self.poller.unregister(sock)
                          except: pass
                          try:
                              sock.close()
                          except: pass
                 except Exception as cleanup_e:
                      eth_log(f"Orchestrator: Error during cleanup after handler error for {conn}: {cleanup_e}")
                 return True
        elif handler is None:
            eth_log(f"Orchestrator: No handler found for connection {conn} (Transport: {conn.tran}).")
            connection.remove(sock)
            try:
                self.poller.unregister(sock)
            except: pass
            try:
                sock.close()
            except: pass
            return True
        else:
             eth_log(f"Orchestrator: Invalid handler type '{type(handler)}' found for connection {conn}.")
             connection.remove(sock)
             try:
                 self.poller.unregister(sock)
             except: pass
             try:
                 sock.close()
             except: pass
             return True

class ProtocolHandler(SocketPollHandler):
    """handle socket events according to protocol"""

    def __init__(self, orch: Orchestrator, proto: protocol, name: str | None = None):
        if not isinstance(proto, protocol):
             raise TypeError("ProtocolHandler requires a valid protocol instance.")

        effective_name = name or str(proto)
        super().__init__(orch.poller, effective_name)
        self.orch = orch
        self.proto = proto
        self.orch.register(self.proto, self)

    def stop(self):
        """Stop handling the protocol and unregister from the orchestrator."""
        eth_log(f"Stopping ProtocolHandler: {self.name}")
        self.orch.unregister(self.proto, self)

class Server(ProtocolHandler):
    def __init__(
        self,
        orch: Orchestrator,
        port: int,
        proto: protocol,
        name: str | None = None
    ):
        if not isinstance(proto, protocol) or not proto.transport:
             raise TypeError("Server requires a valid protocol instance with an associated transport.")
        super().__init__(orch, proto, name or f"{proto}-Server:{port}")
        orch.register(proto.transport, proto)
        orch.register(proto, self)
        self.conn = connection(proto.transport)
        self.sock = self.conn.sock
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.orch.register(self.conn, self)
        self.poller.register(self.sock, select.POLLIN)
        try:
            addr = socket.getaddrinfo("0.0.0.0", port, 0, proto.transport.sock_type)[0][-1]
            self.sock.bind(addr)
            if proto.transport == Transport.TCP:
                self.sock.listen(5)
        except OSError as e:
            eth_log(f"Error binding/listening on port {port}: {e}")
            self.stop()
            raise

    def accept(self, server_sock):
        """Accepts a new connection on the listening socket."""
        try:
            client_sock, addr = server_sock.accept()
            client_sock.setblocking(False)
            client_conn = connection(self.proto.transport, client_sock)
            client_conn.proto = self.proto
            self.poller.register(client_sock, select.POLLIN)


        except OSError as e:
            eth_log(f"{self.name}: Socket accept error: {e}")

        except Exception as e:
            eth_log(f"{self.name}: Unexpected error during accept: {e}")


    def handle(self, sock, event):
         if sock is self.sock:
             if event & select.POLLIN:
                 self.accept(sock)
             else:
                 eth_log(f"{self.name}: Unhandled event {event} on listening socket {id(sock)}")
         else:
             eth_log(f"{self.name}: Received event {event} for client socket {id(sock)}. "
                     f"This should ideally be handled by a dedicated client handler.")
             if not (event & (select.POLLIN | select.POLLOUT)):
                  connection.remove(sock)
                  try:
                      self.poller.unregister(sock)
                  except: pass
                  try:
                      sock.close()
                  except: pass
                  return True


         return False


    def stop(self):
        """Stops the server, closing the listening socket and unregistering."""
        eth_log(f"Stopping Server: {self.name}")
        if hasattr(self, 'sock') and self.sock:
            try:
                self.poller.unregister(self.sock)
            except Exception as e:
                 eth_log(f"Error unregistering listening socket {id(self.sock)}: {e}")

            try:
                self.sock.close()
            except Exception as e:
                 eth_log(f"Error closing listening socket {id(self.sock)}: {e}")


            if hasattr(self, 'conn'):
                 connection.remove(self.sock)
                 self.orch.unregister(self.conn, self)

        super().stop()
        if hasattr(self, 'proto') and self.proto and self.proto.transport:
             self.orch.unregister(self.proto.transport, self.proto)


class IpSink:
    def __init__(self, ip: bytes | str | None = None):
        self.ip = encode(ip) if ip is not None else None


    def get(self):
        return self.ip

    def set(self, ip: bytes | str | None):
         self.ip = encode(ip) if ip is not None else None


# === Contents from http.py ===

class HTTP(Server):
    NL = b"\r\n"
    END = NL + NL

    class Method:
        GET = b"GET"
        POST = b"POST"


    class ContentType:
        class Value:
            TEXT = b"text/plain"
            HTML = b"text/html"
            FORM = b"application/x-www-form-urlencoded"
            CSS = b"text/css"
            JS = b"application/javascript"
            PNG = b"image/png"
            ICO = b"image/x-icon"
            JSON = b"application/json"


        _ext_map = {
            b".html": Value.HTML,
            b".css": Value.CSS,
            b".js": Value.JS,
            b".png": Value.PNG,
            b".ico": Value.ICO,
            b".json": Value.JSON,
            b".txt": Value.TEXT,
        }


        @staticmethod
        def from_path(path: bytes):
             """Determine Content-Type from file extension in path."""
             parts = path.split(b'.')
             if len(parts) > 1:
                 ext = b'.' + parts[-1]
                 return HTTP.ContentType._ext_map.get(ext, HTTP.ContentType.Value.TEXT)
             return HTTP.ContentType.Value.TEXT


        @staticmethod
        def header(content_type_value: bytes):
            """Generate the Content-Type header line."""
            return b"Content-Type: " + content_type_value if content_type_value else b""


    Request = namedtuple(
        "Request", "host method path raw_query query headers body socket"
    )

    class Response:
        class Status:
            OK = b"HTTP/1.1 200 OK"
            REDIRECT = b"HTTP/1.1 307 Temporary Redirect"
            NOT_FOUND = b"HTTP/1.1 404 Not Found"
            BAD_REQUEST = b"HTTP/1.1 400 Bad Request"
            SERVER_ERROR = b"HTTP/1.1 500 Internal Server Error"


        def __init__(self, http_server: 'HTTP', sock: socket.socket, tcp_handler: TCP):
            self.http_server = http_server
            self.sock = sock
            self.tcp = tcp_handler
            self.headers_sent = False


        def _send(self, status_line: bytes, extra_headers: list[bytes] | tuple[bytes] = (), content: bytes | None = None):
            if self.headers_sent:
                eth_log(f"Headers already sent for socket {id(self.sock)}")
                return


            all_headers = [status_line] + list(extra_headers)


            all_headers.append(b"Server: PicoW-HTTP")
            all_headers.append(b"Connection: close")

            content_bytes = b""
            if content:
                if isinstance(content, str):
                    content_bytes = content.encode('utf-8')
                elif isinstance(content, bytes):
                    content_bytes = content
                else:
                   content_bytes = str(content).encode('utf-8')

                all_headers.append(b"Content-Length: " + str(len(content_bytes)).encode())


            header_block = HTTP.NL.join(all_headers) + HTTP.END


            data_to_send = [header_block]
            if content_bytes:
                data_to_send.append(content_bytes)

            eth_log(f"HTTP Response: {status_line.decode()}")
            self.tcp.prepare(self.sock, data_to_send)
            self.headers_sent = True


        def send_status(self, status_line: bytes, extra_headers: list[bytes] | tuple[bytes] = ()):
            """Sends only headers with a specific status."""
            self._send(status_line, extra_headers, None)


        def send(self, status_line: bytes, content_type: bytes | None, content: bytes | str | None, extra_headers: list[bytes] | tuple[bytes] = ()):
            """Sends headers and content."""
            headers = list(extra_headers)
            if content_type:
                headers.append(HTTP.ContentType.header(content_type))
            self._send(status_line, headers, content)


        def ok(self, content_type: bytes | None = None, content: bytes | str | None = b"", extra_headers: list[bytes] | tuple[bytes] = ()):
            """Send 200 OK response."""
            if content_type is None:
                content_type = HTTP.ContentType.Value.TEXT
            self.send(HTTP.Response.Status.OK, content_type, content, extra_headers)

        def html(self, content: bytes | str, extra_headers: list[bytes] | tuple[bytes] = ()):
             """Send 200 OK with HTML content."""
             self.ok(HTTP.ContentType.Value.HTML, content, extra_headers)


        def redirect(self, url: str | bytes, extra_headers: list[bytes] | tuple[bytes] = ()):
             """Send 307 Temporary Redirect response."""
             location_header = b"Location: " + encode(url)
             headers = list(extra_headers) + [location_header]
             self.send_status(HTTP.Response.Status.REDIRECT, headers)


        def not_found(self, extra_headers: list[bytes] | tuple[bytes] = ()):
             """Send 404 Not Found response."""
             self.send(HTTP.Response.Status.NOT_FOUND, HTTP.ContentType.Value.TEXT, b"Not Found", extra_headers)


        def bad_request(self, message: str | bytes = b"Bad Request", extra_headers: list[bytes] | tuple[bytes] = ()):
            """Send 400 Bad Request response."""
            self.send(HTTP.Response.Status.BAD_REQUEST, HTTP.ContentType.Value.TEXT, message, extra_headers)


        def server_error(self, message: str | bytes = b"Internal Server Error", extra_headers: list[bytes] | tuple[bytes] = ()):
             """Send 500 Internal Server Error response."""
             self.send(HTTP.Response.Status.SERVER_ERROR, HTTP.ContentType.Value.TEXT, message, extra_headers)


    def __init__(self, orch: Orchestrator, routes: dict, ip_sink: IpSink | None = None):
        super().__init__(orch, 80, Protocol.HTTP, name="HTTP-Server")
        self.tcp = TCP(orch.poller)
        self.ip_sink = ip_sink
        self.routes = self._prepare_routes(routes)
        self.sock.setblocking(False)


    def _prepare_routes(self, routes_config):
         """Convert string paths in routes config to bytes."""
         prepared = {}
         for path, target in routes_config.items():
             byte_path = path.encode('utf-8') if isinstance(path, str) else path
             if isinstance(target, str):
                 prepared[byte_path] = target.encode('utf-8')
             else:
                 prepared[byte_path] = target
         return prepared


    def handle(self, sock, event):
        if sock is self.sock:
            super().handle(sock, event)
            return False


        if event & select.POLLERR or event & select.POLLHUP:
            eth_log(f"HTTP Client socket error/hangup event: {event} on {id(sock)}")
            self.tcp.end(sock)
            connection.remove(sock)
            return True


        if event & select.POLLIN:
             try:
                  data = self.tcp.read(sock)
                  if not data and not self.tcp._reads.get(id(sock), b""):
                       self.tcp.end(sock)
                       connection.remove(sock)
                       return True

                  self.process_request_data(sock)


             except OSError as e:
                 eth_log(f"HTTP Read error on client socket {id(sock)}: {e}")
                 self.tcp.end(sock)
                 connection.remove(sock)
                 return True
             except Exception as e:
                 eth_log(f"HTTP Unexpected error during read/process on {id(sock)}: {e}")
                 micropython.mem_info()

                 res = HTTP.Response(self, sock, self.tcp)
                 if not res.headers_sent:
                     res.server_error()

                 self.tcp.end(sock)


        if event & select.POLLOUT:
            try:
                if self.tcp.write(sock):
                    self.tcp.end(sock)
                    connection.remove(sock)
                    return True
            except OSError as e:
                eth_log(f"HTTP Write error on client socket {id(sock)}: {e}")
                self.tcp.end(sock)
                connection.remove(sock)
                return True
            except Exception as e:
                eth_log(f"HTTP Unexpected error during write on {id(sock)}: {e}")
                micropython.mem_info()
                self.tcp.end(sock)
                connection.remove(sock)
                return True


        return False


    def process_request_data(self, sock):
         """Check buffer for complete HTTP request and handle if found."""
         sid = id(sock)
         buffered_data = self.tcp._reads.get(sid, b"")


         eoh_index = buffered_data.find(HTTP.END)
         if eoh_index == -1:
             MAX_HEADER_SIZE = 2048
             if len(buffered_data) > MAX_HEADER_SIZE:
                 eth_log(f"Header size exceeded limit for {sid}. Closing connection.")
                 res = HTTP.Response(self, sock, self.tcp)
                 res.bad_request(b"Headers too large")
                 self.tcp.clear(sock)

             return


         header_bytes = buffered_data[:eoh_index]
         body_start_index = eoh_index + len(HTTP.END)
         body_so_far = buffered_data[body_start_index:]


         content_length = 0
         try:
             header_lines = header_bytes.split(HTTP.NL)
             request_line = header_lines[0]
             headers = {}
             for line in header_lines[1:]:
                 if b": " in line:
                     key, value = line.split(b": ", 1)
                     headers[key.lower()] = value

             content_length_bytes = headers.get(b"content-length")
             if content_length_bytes:
                 content_length = int(content_length_bytes)
         except Exception as e:
             eth_log(f"Error parsing headers for {sid}: {e}")
             res = HTTP.Response(self, sock, self.tcp)
             res.bad_request(b"Invalid headers")
             self.tcp.clear(sock)
             return


         if len(body_so_far) < content_length:
             MAX_BODY_SIZE = 1024 * 10
             if content_length > MAX_BODY_SIZE:
                  eth_log(f"Content-Length {content_length} exceeds limit for {sid}. Closing.")
                  res = HTTP.Response(self, sock, self.tcp)
                  res.bad_request(b"Request body too large")
                  self.tcp.clear(sock)

             return


         actual_body = body_so_far[:content_length]

         full_request_bytes = header_bytes + HTTP.END + actual_body


         remaining_data = body_so_far[content_length:]
         self.tcp._reads[sid] = remaining_data


         try:
             req = self.parse_request(request_line, headers, actual_body, sock)
             if req:
                  self.handle_route(req)
             else:
                  res = HTTP.Response(self, sock, self.tcp)
                  res.bad_request(b"Failed to parse request line")


         except Exception as e:
             eth_log(f"Error handling request for {sid}: {e}")
             micropython.mem_info()

             res = HTTP.Response(self, sock, self.tcp)

             if not res.headers_sent:
                 res.server_error()

             self.tcp.end(sock)


         if remaining_data:
             self.process_request_data(sock)


    def parse_request(self, request_line: bytes, headers: dict[bytes, bytes], body_bytes: bytes, sock: socket.socket):
        """Parses the request line and headers into a Request object."""
        try:
            method, full_path, version = request_line.split(b" ", 2)
        except ValueError:
             eth_log(f"Malformed request line: {request_line}")
             return None


        path, *query_parts = full_path.split(b"?", 1)
        raw_query = query_parts[0] if query_parts else None
        query = {}
        if raw_query:
            try:
                params = raw_query.split(b"&")
                for param in params:
                     if b"=" in param:
                         key, val = param.split(b"=", 1)
                         query[unquote(key)] = unquote(val)
                     elif param:
                         query[unquote(param)] = None
            except Exception as e:
                 eth_log(f"Error parsing query string '{raw_query}': {e}")
                 query = {}


        host = headers.get(b"host")


        if not path.startswith(b'/'):
            path = b'/' + path

        return HTTP.Request(host, method, path, raw_query, query, headers, body_bytes, sock)


    def handle_route(self, req: Request):
        """Finds the appropriate handler for the request path and executes it."""
        res = HTTP.Response(self, req.socket, self.tcp)
        route_target = self.routes.get(req.path)


        if req.path == b'/' and route_target is None:
             index_html_path = b'/index.html'
             if index_html_path in self.routes:
                 route_target = self.routes[index_html_path]
             else:
                 res.ok(HTTP.ContentType.Value.TEXT, b"Ok")
                 return


        if route_target:
            try:
                if isinstance(route_target, bytes):
                    content_type = HTTP.ContentType.from_path(route_target)
                    try:
                        with open(route_target, "rb") as f:
                            content = f.read()
                        res.ok(content_type, content)
                    except OSError as e:
                        res.not_found()
                    except Exception as e:
                         eth_log(f"Unexpected error reading file {route_target.decode()}: {e}")
                         res.server_error()


                elif callable(route_target):
                    result = route_target(req, res)
                    if not res.headers_sent:
                        if result is None:
                             pass
                        elif isinstance(result, (bytes, str)):
                            res.ok(HTTP.ContentType.Value.HTML, result)
                        else:
                            eth_log(f"Route handler for {req.path.decode()} returned unhandled type: {type(result)}")
                            res.server_error(b"Handler returned unexpected data type")


                else:
                    eth_log(f"Invalid route target type for {req.path.decode()}: {type(route_target)}")
                    res.server_error(b"Server configuration error")


            except Exception as e:
                if not res.headers_sent:
                    res.server_error()


        else:
             res.not_found()


    def stop(self):
        super().stop() 
