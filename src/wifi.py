from constants import ASSUMED_TIMEONE_OFFSET_S
import network
import random
import socket
import ntptime
from secrets import secrets
from logging import eth_log
import machine
import time

ssid = secrets["ssid"]
password = secrets["password"]
static_ip = secrets["static_ip"]
subnet_mask = secrets["subnet_mask"]
gateway_ip = secrets["gateway_ip"]
dns_server = secrets["dns_server"]
pushgateway_ip = secrets["pushgateway_ip"]
pushgateway_port = int(secrets["pushgateway_port"])
device_id = secrets["device_id"]


def make_wlan():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    return wlan


def connect_ap(wlan, ssid):
    wlan.connect(ssid, password)

    tries_left = 5

    last_status = None

    while tries_left > 0:
        tries_left -= 1

        wlan_status = wlan.status()
        if wlan_status != last_status:
            last_status = wlan_status
            tries_left += 5

        if wlan_status == network.STAT_GOT_IP:
            eth_log("Wifi connection successful!")
            network_info = wlan.ifconfig()
            eth_log(f"IP: {network_info[0]}")
            ntptime.settime()

            rtc = machine.RTC()
            ts_utc = time.mktime(rtc.datetime())
            ts_local = ts_utc + ASSUMED_TIMEONE_OFFSET_S
            lt = time.localtime(ts_local)
            rtc.datetime(lt)
            eth_log(f"Time set!")

        yield wlan_status
        eth_log(f"Wlan status {wlan_status}, retrying ({tries_left} tries left)")

    eth_log("Wifi connection unsuccessful, are the secrets set up?")
    return wlan_status


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
