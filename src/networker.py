import network
import time
import select
import socket
from logging import eth_log
from net.dependencies import Orchestrator, Protocol, Server, HTTP, TCP
import json
import os

ap_ip = "192.168.4.1"
NETWORK_FILE = "/public/networks.json"

REDIRECT_PATHS = {
    b"/portal",
    b"/hotspot-detect.html",
    b"/library/test/success.html",
    b"/success.html",
    b"/generate_204",
    b"/gen_204",
    b"/mobile/status.php",
    b"/check_network_status.txt",
    b"/connectivitycheck",
    b"/redirect",
    b"/login",
    b"/",
}


class dns(Server):
    def __init__(self, orchestrator, ip):
        super().__init__(orchestrator, 53, Protocol.DNS)
        self.ip = ip
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    def handle(self, sock, event):
        if sock is not self.sock:
            return True
        if event == select.POLLHUP:
            return True
        if not (event & select.POLLIN):
            return True

        try:
            data, sender = sock.recvfrom(1024)
            request = dns.Query(data)

            ip_str = self.ip
            if isinstance(self.ip, bytes):
                ip_str = self.ip.decode("utf-8")

            eth_log("DNS request:", request.domain, "->", ip_str)
            sock.sendto(request.answer(ip_str), sender)
            del request
            return False
        except Exception as e:
            eth_log("DNS error:", e)
            return True

    class Query:
        def __init__(self, data):
            self.data = data
            self.domain = ""
            head = 12
            length = data[head]
            while length != 0:
                label = head + 1
                self.domain += data[label : label + length].decode("utf-8") + "."
                head += length + 1
                length = data[head]

        def answer(self, ip):
            packet = self.data[:2]
            packet += b"\x81\x80"
            packet += self.data[4:6] + self.data[4:6]
            packet += b"\x00\x00\x00\x00"
            packet += self.data[12:]
            packet += b"\xC0\x0C"
            packet += b"\x00\x01\x00\x01"
            packet += b"\x00\x00\x00\x3C"
            packet += b"\x00\x04"
            packet += bytes(map(int, ip.split(".")))
            return packet


class http(HTTP):
    def __init__(self, orch, ip_bytes, routes, portal_ref):
        super().__init__(orch, routes)
        self.ap_ip_bytes = ip_bytes
        self.portal_ref = portal_ref

    class FixedResponse(HTTP.Response):
        CONTENT_TYPES = {
            ".html": b"Content-Type: text/html; charset=utf-8",
            ".css": b"Content-Type: text/css",
            ".gif": b"Content-Type: image/gif",
        }

        def _handle_file_error(self, e, path):
            if e.args[0] == 2:
                eth_log("File not found:", path)
                try:
                    self.send(
                        [
                            HTTP.Response.Status.NOT_FOUND,
                            b"Content-Type: text/plain",
                            b"Content-Length: 14",
                            b"Connection: close",
                        ],
                        b"File not found",
                    )
                except Exception:
                    pass
            elif e.args[0] in (104, 9):
                eth_log("File error (connection reset or bad fd):", e)
                try:
                    self.sock.close()
                except Exception:
                    pass
            else:
                eth_log("File error:", e)
                error_msg = f"Error: {e}".encode()
                try:
                    self.send(
                        [
                            HTTP.Response.Status.SERVER_ERROR,
                            b"Content-Type: text/plain",
                            f"Content-Length: {len(error_msg)}".encode(),
                            b"Connection: close",
                        ],
                        error_msg,
                    )
                except Exception:
                    pass

        def file(self, path: bytes | str):
            try:
                if isinstance(path, bytes):
                    path_str = path.decode()
                else:
                    path_str = str(path)

                if not path_str.startswith("/"):
                    fs_path = "/public/" + path_str
                elif (
                    not path_str.startswith("/public") and path_str != "/networks.json"
                ):
                    fs_path = "/public" + path_str
                else:
                    fs_path = path_str

                with open(fs_path, "rb") as f:
                    content = f.read()

                headers = [HTTP.Response.Status.OK]
                content_type = next(
                    (
                        ct
                        for ext, ct in self.CONTENT_TYPES.items()
                        if fs_path.endswith(ext)
                    ),
                    b"Content-Type: application/octet-stream",
                )
                headers.append(content_type)
                headers.append(f"Content-Length: {len(content)}".encode())
                headers.append(b"Connection: close")
                self.send(headers, content)
            except (OSError, ValueError) as e:
                self._handle_file_error(e, fs_path if "fs_path" in locals() else path)
            except Exception as e:
                eth_log(f"General file serving error for {path}: {e}")
                self._handle_file_error(e, path)

    def handle_request(self, sock, req):
        res = self.FixedResponse(self, sock)

        portal_url = b"http://" + self.ap_ip_bytes + b"/portal"

        host = req.host.decode() if req.host else ""
        if host and any(
            check in host
            for check in [
                "connectivitycheck.gstatic.com",
                "clients3.google.com",
                "connectivitycheck.android.com",
                "android.clients.google.com",
                "msftconnecttest.com",
                "apple.com",
            ]
        ):
            res.redirect(portal_url)
            return

        try:
            client_addr = sock.getpeername()
            eth_log(
                f"HTTP Request: {req.method.decode()} {req.path.decode()} from {client_addr[0]}:{client_addr[1]}"
            )
        except:
            eth_log(f"HTTP Request: {req.method.decode()} {req.path.decode()}")

        if req.path in REDIRECT_PATHS:
            eth_log(f"Connectivity check (Path): {req.path.decode()}")
            res.redirect(portal_url)
            return

        route = self.parse_route(req)
        try:
            if route:
                if isinstance(route, bytes):
                    eth_log(f"Serving file route: {route.decode()}")
                    res.file(route)
                elif callable(route):
                    eth_log(f"Calling route handler: {route.__name__}")
                    result = route(req, res)

                    if result is True:
                        if self.portal_ref and hasattr(
                            self.portal_ref, "network_saved"
                        ):
                            eth_log("Setting network_saved flag.")
                            self.portal_ref.network_saved = True

                    elif not res.headers_sent:
                        if result is None:
                            pass
                        elif isinstance(result, (bytes, str)):
                            res.ok(HTTP.ContentType.Value.HTML, result)
                        elif result is False:
                            res.server_error(b"Handler failure")
                        else:
                            res.server_error(b"Handler returned unexpected data type")
                else:
                    res.send(HTTP.Response.Status.NOT_FOUND)
            else:
                res.file(req.path)

        except OSError as e:
            if e.args[0] == 104:
                try:
                    self.tcp.end(sock)
                except Exception as clean_err:
                    eth_log("Socket cleanup error after disconnect:", clean_err)
            else:
                eth_log(f"Request handling OSError: {e}")
                if not res.headers_sent:
                    try:
                        error_msg = f"Server error: {e}".encode()
                        res.send(
                            [
                                HTTP.Response.Status.SERVER_ERROR,
                                b"Content-Type: text/plain",
                                f"Content-Length: {len(error_msg)}".encode(),
                                b"Connection: close",
                            ],
                            error_msg,
                        )
                    except Exception as send_err:
                        eth_log(f"Error sending server error response: {send_err}")
                        self.tcp.end(sock)
        except Exception as e:
            eth_log(f"General request handling error: {e}")
            if not res.headers_sent:
                try:
                    res.send(HTTP.Response.Status.SERVER_ERROR)
                except:
                    self.tcp.end(sock)

    def handle(self, sock, event):
        try:
            return super().handle(sock, event)
        except OSError as e:
            if e.args[0] == 104:
                eth_log("Connection reset during HTTP handling")
                try:
                    self.tcp.end(sock)
                except Exception as clean_err:
                    eth_log("Socket cleanup error after reset:", clean_err)
                return True
            eth_log(f"HTTP handler OSError: {e}")
            try:
                self.tcp.end(sock)
            except:
                pass
            return True
        except Exception as e:
            eth_log(f"Unexpected error in HTTP handle: {e}")
            try:
                self.tcp.end(sock)
            except:
                pass
            return True


class captive_portal:
    def __init__(self, ap_ip, button_long_check_func=None):
        self.ap_ip = ap_ip
        self.poller = select.poll()
        self.orch = Orchestrator(self.poller)
        self.servers = None
        self.saved_networks = []
        self.network_saved = False
        self.button_long_check_func = button_long_check_func
        self.load_saved_networks()

        portal_routes = [
            b"/portal",
            b"/hotspot-detect.html",
            b"/library/test/success.html",
            b"/success.html",
            b"/generate_204",
            b"/gen_204",
            b"/mobile/status.php",
            b"/check_network_status.txt",
            b"/connectivitycheck.gstatic.com",
            b"/connectivitycheck",
            b"/redirect",
            b"/login",
            b"/",
        ]

        self.routes = {route: b"/public/portal.html" for route in portal_routes}
        self.routes[b"/networks.json"] = self.get_networks_json
        self.routes[b"/save"] = self.save_network
        self.routes[b"/pico_wifi_run.gif"] = b"/public/pico_wifi_run.gif"
        self.routes[b"/pico_wifi.gif"] = b"/public/pico_wifi.gif"

    def load_saved_networks(self):
        try:
            with open(NETWORK_FILE, "r") as f:
                networks_data = json.load(f)
                self.saved_networks = networks_data.get("saved", [])
                eth_log(
                    f"Loaded {len(self.saved_networks)} saved networks from {NETWORK_FILE}"
                )
        except Exception as e:
            eth_log(f"Error loading {NETWORK_FILE}: {e}. Starting with empty list.")
            self.saved_networks = []

    def scan_networks(self):
        try:
            sta = network.WLAN(network.STA_IF)
            if not sta.active():
                sta.active(True)
                time.sleep(1)
            eth_log("Scanning for networks...")
            networks = sta.scan()
            ssids = []
            for n in networks:
                try:
                    ssid = n[0].decode("utf-8", "replace")
                    if ssid:
                        ssids.append(ssid)
                except Exception as decode_err:
                    eth_log(f"Could not decode SSID {n[0]}: {decode_err}")
            unique_ssids = sorted(list(set(ssids)))
            eth_log(f"Scan found {len(unique_ssids)} unique networks.")
            return unique_ssids
        except Exception as e:
            eth_log("Network scan error:", e)
            return []

    def get_networks_json(self, req, res):
        try:
            scanned = self.scan_networks()
            networks_data = {"scanned": scanned, "saved": self.saved_networks}
            json_str = json.dumps(networks_data)
            json_bytes = json_str.encode("utf-8")

            res.ok(
                HTTP.ContentType.Value.JSON,
                json_bytes,
                extra_headers=[
                    b"Cache-Control: no-cache, no-store, must-revalidate",
                    b"Connection: close",
                ],
            )
            return
        except Exception as e:
            eth_log(f"get_networks_json error: {e}")
            if res and not res.headers_sent:
                try:
                    res.server_error()
                except:
                    if hasattr(self, "tcp") and self.tcp:
                        self.tcp.end(res.sock)
                    else:
                        try:
                            res.sock.close()
                        except:
                            pass
            return

    def save_network(self, req, res):
        if req.method != b"POST":
            res.bad_request(b"Expected POST")
            return

        body = req.body.decode("utf-8")
        eth_log(f"Save network request body: {body}")
        params = {}
        try:
            pairs = body.split("&")
            for pair in pairs:
                if "=" in pair:
                    key, val = pair.split("=", 1)
                    params[self.url_decode(key)] = self.url_decode(val)
                elif pair:
                    params[self.url_decode(pair)] = ""

            ssid = params.get("ssid")
            password = params.get("password", "")

            if not ssid:
                res.bad_request(b"Missing SSID")
                return

            self.saved_networks = [{"ssid": ssid, "password": password}]
            try:
                networks_data = {"scanned": [], "saved": self.saved_networks}
                with open(NETWORK_FILE, "w") as f:
                    json.dump(networks_data, f)
            except Exception as e:
                eth_log(f"Error writing {NETWORK_FILE}: {e}")

            response_body = b"Network saved successfully."

            res.ok(HTTP.ContentType.Value.TEXT, response_body)
            while not res.tcp.write(res.sock):
                pass

            res.tcp.end(res.sock)
            eth_log("Save network request successfully processed.")
            time.sleep(1)
            self.network_saved = True

        except Exception as e:
            eth_log(f"Error save network request: {e}")
        try:
            if not res.headers_sent:
                res.server_error(f"Error saving: {e}".encode())
        except Exception as inner_e:
            eth_log(f"Failed to send error response: {inner_e}")

    def url_decode(self, s):
        res = s.replace("+", " ")
        i = 0
        while i < len(res):
            if res[i] == "%":
                if i + 2 < len(res):
                    try:
                        hex_val = res[i + 1 : i + 3]
                        char_code = int(hex_val, 16)
                        res = res[:i] + chr(char_code) + res[i + 3 :]
                        i += 1
                    except ValueError:
                        i += 3
                else:
                    i += 1
            else:
                i += 1
        return res

    def start(self):
        ap_ip_bytes = self.ap_ip.encode("utf-8")
        self.servers = [
            http(self.orch, ap_ip_bytes, self.routes, self),
            dns(self.orch, ap_ip_bytes),
        ]
        eth_log("Portal HTTP and DNS servers started")

    def run(self):
        self.setup_complete = False
        eth_log("Entering captive_portal run loop")
        while True:
            if self.button_long_check_func():
                eth_log("Long button press detected, exiting portal run loop.")
                break

            if self.network_saved:
                self.setup_complete = True
                break

            try:
                events = self.poller.ipoll(1000)
                if not events:
                    continue

                for sock, event in events:
                    if self.orch.handle(sock, event):
                        pass

            except Exception as e:
                eth_log(f"Error in captive_portal run loop: {e}")

        eth_log(f"Final setup_complete status: {self.setup_complete}")

    def stop(self):
        if self.servers:
            for server in self.servers:
                server_sock = getattr(server, "sock", None)
                if server_sock:
                    if hasattr(server_sock, "fileno"):
                        try:
                            self.orch.poller.unregister(server_sock)
                            fd = server_sock.fileno()
                            eth_log(f"Unregistered server socket: {fd}")
                        except ValueError:
                            try:
                                fd = server_sock.fileno()
                                eth_log(f"Server socket {fd} was not registered.")
                            except Exception:
                                eth_log(
                                    f"Server socket (no fileno?) was not registered."
                                )
                        except Exception as e:
                            try:
                                fd = server_sock.fileno()
                                eth_log(f"Error unregistering server socket {fd}: {e}")
                            except Exception:
                                eth_log(
                                    f"Error unregistering server socket (no fileno?): {e}"
                                )
                    try:
                        server_sock.close()
                        eth_log(f"Closed server socket object: {server_sock}")
                    except Exception as e:
                        eth_log(f"Error closing server socket {server_sock}: {e}")

                if hasattr(server, "tcp") and hasattr(server.tcp, "connections"):
                    client_socks = list(server.tcp.connections.keys())
                    if client_socks:
                        eth_log(
                            f"Closing {len(client_socks)} client connections for server {type(server).__name__}"
                        )
                        for client_sock in client_socks:
                            server.tcp.end(client_sock)

        self.servers = None
        eth_log("Portal stopped")


class network_manager:
    def __init__(
        self,
        button_long_check_func=None,
        ap_ssid="Cardiotron",
        ap_password="password",
    ):
        self.sta_if = network.WLAN(network.STA_IF)
        self.ap_if = network.WLAN(network.AP_IF)
        self.ap_ssid = ap_ssid
        self.ap_password = ap_password
        self.portal = None
        self.button_long_check_func = button_long_check_func

    def is_connected(self):
        return self.sta_if.isconnected()

    def get_ip(self):
        if self.is_connected():
            return self.sta_if.ifconfig()[0]
        return None

    def read_saved(self):
        try:
            try:
                os.stat(NETWORK_FILE)
            except OSError:
                eth_log(f"{NETWORK_FILE} not found.")
                return None

            with open(NETWORK_FILE, "r") as f:
                networks_data = json.load(f)
            saved_list = networks_data.get("saved", [])
            if saved_list:
                last_network = saved_list[0]
                ssid = last_network.get("ssid")
                password = last_network.get("password")
                if ssid:
                    return {
                        "ssid": ssid,
                        "password": password if password is not None else "",
                    }
        except Exception as e:
            return None

    def attempt_connect(self, ssid, password):
        eth_log(f"Attempting to connect: {ssid}")
        if not self.sta_if.active():
            self.sta_if.active(True)
            eth_log("Activated STA")

        if self.ap_if.active():
            self.ap_if.active(False)

        self.sta_if.connect(ssid, password)
        time.sleep_ms(500)

        start_time = time.time()
        connection_status = -1
        success = False
        while time.time() - start_time < 10:
            connection_status = self.sta_if.status()
            if connection_status >= 3:
                eth_log("Connection successful! Status >= 3")
                eth_log(f"Network config: {self.sta_if.ifconfig()}")
                success = True
                break
            if connection_status < 0:
                eth_log(f"Connection failed. Status: {connection_status}")
                break

            eth_log("Waiting for connection...")
            time.sleep(1)

        if connection_status < 3:
            eth_log(f"Connection timed out. Final status: {connection_status}")
            self.disconnect()
            return False
        elif success:
            return True

        self.disconnect()
        return False

    def connect(self):
        eth_log("Connecting")
        credentials = self.read_saved()
        if credentials:
            return self.attempt_connect(credentials["ssid"], credentials["password"])
        else:
            eth_log("No saved network found to connect")
            return False

    def disconnect(self):
        if self.sta_if.isconnected():
            self.sta_if.disconnect()
            eth_log("STA disconnected")
        else:
            eth_log("STA was not connected")
        if self.sta_if.active():
            self.sta_if.active(False)
            eth_log("STA deactivated")
        else:
            eth_log("STA was not active")

    def start_portal(self):
        eth_log("Starting captive portal")

        if self.sta_if.active():
            self.disconnect()

        self.ap_if.active(True)
        self.ap_if.config(essid=self.ap_ssid, password=self.ap_password)
        self.ap_if.ifconfig((ap_ip, "255.255.255.0", ap_ip, ap_ip))
        eth_log("AP started. Config:", self.ap_if.ifconfig())

        portal = captive_portal(
            ap_ip, button_long_check_func=self.button_long_check_func
        )
        portal_completed_successfully = False

        try:
            portal.start()
            portal.run()
            portal_completed_successfully = portal.setup_complete
            eth_log(
                f"Portal run finished. Captured setup_complete status: {portal_completed_successfully}"
            )
        finally:
            try:
                portal.stop()
            except Exception as e:
                eth_log(f"Error: portal.stop(): {e}")

        self.ap_if.active(False)
        return portal_completed_successfully
