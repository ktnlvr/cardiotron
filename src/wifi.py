import network
import time
import random
import socket
from secrets import secrets
from logging import eth_log

ssid = secrets["ssid"]
password = secrets["password"]
static_ip = secrets["static_ip"]
subnet_mask = secrets["subnet_mask"]
gateway_ip = secrets["gateway_ip"]
dns_server = secrets["dns_server"]
pushgateway_ip = secrets["pushgateway_ip"]
pushgateway_port = int(secrets["pushgateway_port"])
device_id = secrets["device_id"]


def connect_ap():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(ssid, password)

    for _ in range(5):
        if wlan.status() == 3:
            eth_log("Wifi connection successful!")
            network_info = wlan.ifconfig()
            eth_log(f"IP: {network_info[0]}")
            return wlan
        time.sleep(1)
    raise RuntimeError("Wifi connection unsuccessful, are the secrets setup?")


def pushgateway_send(data):
    try:
        if not data:
            eth_log("No data to send")
            return

        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((pushgateway_ip, pushgateway_port))

        http_request = (
            f"PUT /metrics/job/picow HTTP/1.1\r\n"
            f"Host: {pushgateway_ip}:{pushgateway_port}\r\n"
            f"Content-Length: {len(data)}\r\n"
            f"Content-Type: text/plain\r\n"
            f"\r\n"
            f"{data}"
        )

        s.send(http_request.encode())
        response = s.recv(1024)
        s.close()
        eth_log("Data sent")
        eth_log(f"Response: {response}")
    except Exception as e:
        eth_log(f"Error sending: {e}")


def pushgateway_send_test():
    random_value = random.uniform(0, 100)
    type = "Test data"
    data = f'Random{{device="{device_id}",type="{type}"}} {random_value}\n'
    eth_log(data)
    pushgateway_send(data)


connect_ap()
while True:
    pushgateway_send_test()
    time.sleep(1)
