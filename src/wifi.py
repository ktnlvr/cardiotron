import network
import time
import random
import socket
from secrets import secrets

ssid = secrets['ssid']
password = secrets['password']
static_ip = secrets['static_ip']
subnet_mask = secrets['subnet_mask']
gateway_ip = secrets['gateway_ip']
dns_server = secrets['dns_server']
pushgateway_ip = secrets['pushgateway_ip']
pushgateway_port = int(secrets['pushgateway_port'])
device_id = secrets['device_id']

def ConnectWifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(ssid, password)

    if wlan.status() != 3:
        raise RuntimeError('Wifi connection unsuccessful, are the secrets setup?')
        time.sleep(1)
    else:
        print('Wifi connection successful!')
        network_info = wlan.ifconfig()
        print('IP:', network_info[0])
        return wlan
    
def pushgatewaySend(data):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((pushgateway_ip, pushgateway_port))

        http_request = (
            f'PUT /metrics/job/picow HTTP/1.1\r\n'
            f'Host: {pushgateway_ip}:{pushgateway_port}\r\n'
            f'Content-Length: {len(data)}\r\n'
            f'Content-Type: text/plain\r\n'
            f'\r\n'
            f'{data}'
        )

        s.send(http_request.encode())
        response = s.recv(1024)
        s.close()
        print('Data sent')
        print('Response:', response)
    except Exception as e:
        print('Error sending:', e)

ConnectWifi()
while True:
    random_value = random.uniform(0, 100)
    type = 'Test data'
    data = f'Random{{device="{device_id}",type="{type}"}} {random_value}\n'
    print(data)
    pushgatewaySend(data)
    time.sleep(1)
