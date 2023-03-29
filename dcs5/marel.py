import socket

ip_addr = ""
port = 0
timeout=1
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.settimeout(timeout)

try:
    s.connect((ip_addr, port))
except TimeoutError:
    pass

