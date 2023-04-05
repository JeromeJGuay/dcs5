"""
For Marel Marine Scale M2200

Marel Passwords:
 Service: 62735
 W&M conf: 322225

How to communicate with the scale ?
-----------------------------------
    Through an ethernet connection.
     - Setting the IP_ADDRESS in the scale settings. (detail how )

    Available Ports:
        52200: For dot commands according the Marel documentations. (to access model )
        52202: To send a Lua Script (as a string) and overwrite the one on the scale.
        52203: Once connected to the port, the scale will send the Lua script in memory.
        52210: Marel Lua Interpreter Standard Output, for example using Lua print()
        52211: Usable output using the Marel Lua function CommStr(4, <str>). Persistent queue.
        52212: Usable output using the Marel Lua function CommStr(5, <str>).  (?).
        52213: Usable output using the Marel Lua function CommStr(6, <str>).  (?).

What does the scale do ?
------------------------
    + If the Lua App parameter is `On` (detail how), the scale will run the Lua script in memory in a loop.
    + The Lua script seems to be saved on persistent Memory (not RAM).
    + To send weight a Packing method needs to be set in the Scale settings (detail how).

Lua Script
----------
    The Scale has builtin Lua function to interact with the Scale. However, the basic Lua Libraries seem to
    be missing in the scale.

Notes
-----
    Received on scale restart:
    ```
    10043
    20043
    30043
    40043
    50043
    60043
    10043
    20043
    30043
    40043
    50043
    60043
    ```

"""
import re
import logging
import socket
import time
import threading
from typing import *


UNITS_CONVERSION = {
    'kg': 1, 'g': 1e-3, 'lb': 0.453592, 'oz': 0.0283495
}


PORTS = {
    'dot_port': 52200,
    'download_port': 52202,
    'upload_port': 52203,
    'output_port': 52210,
    'comm4_port': 52211,
    'comm5_port': 52212,
    'comm6_port': 52213
}

MAREL_MSG_ENCODING = 'UTF-8'
BUFFER_SIZE = 1024


# def start_client(addr, port):
#     timeout = 10
#     client = socket.socket(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP)
#     client.settimeout(timeout)
#     client.connect((addr, port))
#
#     return client
#
#
# def sock_send(addr, port, msg):
#     s = start_client(addr, port)
#
#     if isinstance(msg, list):
#         print('Sending on port {port}:')
#         for m in msg:
#             print(f'{m}')
#             s.send(m.encode())
#     else:
#         print(f'Sending on port {port}\n```\n{msg}\n```')
#         s.send(msg.encode())
#
#     s.close()
#
#
# def sock_recv(addr, port):
#     s = start_client(addr, port)
#     while True:
#         try:
#             _msg = s.recv(4096).decode()
#             print(f"Port {port} received\n```\n{_msg}\n```")
#             time.sleep(1)
#         except TimeoutError:
#             continue
#         except KeyboardInterrupt:
#             s.close()
#             break


class EthernetClient:
    def __init__(self):
        self.ip_address: str = None
        self.port: int = None
        self.socket: socket.socket = None
        self.default_timeout = 0.1
        self._is_connected = False
        self.error_msg = ""
        self.errors = {
            0: 'Socket timeout', ### timed out when the ip address is not found.
        }

    @property
    def is_connected(self):
        return self._is_connected

    def connect(self, ip_address, port, timeout: int = None):
        self.ip_address = ip_address
        self.port = port
        timeout = timeout or self.default_timeout

        logging.debug(f'Attempting to connect to ip: {ip_address} on port {port}. Timeout: {timeout} seconds')

        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP)
            self.socket.settimeout(timeout)
            self.socket.connect((ip_address, port))
            self._is_connected = True
            self.socket.settimeout(self.default_timeout)
        except OSError as err:
            self.error_msg = self._process_os_error_code(err)

    def send(self, command: str):
        try:
            self.socket.sendall(command.encode(MAREL_MSG_ENCODING))
        except OSError as err:
            logging.debug(f'OSError on sendall')
            self.error_msg = self.errors[self._process_os_error_code(err)]
            self.close()

    def receive(self):
        try:
            return self.socket.recv(BUFFER_SIZE).decode(MAREL_MSG_ENCODING)
        except OSError as err:
            if err_code := self._process_os_error_code(err) != 0:
                logging.debug(f'OSError on receive')
                self.error_msg = self.errors[err_code]
                self.close()
            return ""

    def clear(self):
        while self.receive() != "":
            continue

    def close(self):
        self.socket.close()
        self._is_connected = False

    def _process_os_error_code(self, err) -> int:
        """
        # TODO keep the appropriate error.
        Parameters
        ----------
        err : OS error code.

        Returns
        -------
        0: Socket timeout
        1: Port Unavailable
        2: Device not Found
        4: Connection broken
        5: Device Unavailable
        6: Client closed.
        99: Unknown Error

        """
        match err.errno:
            case None:
                return 0
            case 9:
                logging.error(f'Bad file descriptor. (err{err.errno})')
                return 6
            case 16:
                logging.error(f'Port unavailable. (err{err.errno})')
                return 1
            case 22:
                logging.error(f'Port does not exist. (err{err.errno})')
                return 1
            case 77:
                logging.error(f'Bad file descriptor. (err{err.errno})')
                return 6
            case 111:
                logging.error(f'Device unavailable. (err{err.errno})')
                return 5
            case 112:
                logging.error(f'Device not found. (err{err.errno})')
                return 2
            case 104:
                logging.error(f'Connection broken. (err{err.errno})')
                return 4
            case 110:
                logging.error(f'Connection broken. (err{err.errno})')
                return 4
            case 112:
                logging.error(f'Device not found. (err{err.errno})')
                return 2
            case 10038:
                logging.error(f'Bad file descriptor. (err{err.errno})')
                return 6
            case 10048:
                logging.error(f'Device unavailable. (Maybe) (err{err.errno})')
                return 5
            case 10049:
                logging.error(f'Port does not exist. (err{err.errno})')
                return 1
            case 10053:
                logging.error(f'Connection broken. (err{err.errno})')
                return 4
            case 10060:
                logging.error(f'Device not found. (err{err.errno})')
                return 2
            case 10064:
                logging.error(f'Port {self.port} unavailable. (err{err.errno})')
                return 1
            case _:
                logging.error(f'OSError (new): {err.errno}')
                return 99


def convert_units(a, b):
    return UNITS_CONVERSION[a] / UNITS_CONVERSION[b]


class MarelController:
    port = PORTS['comm4_port']
    msg_pattern = "%w,(\d+.\d+)(\S+)#"

    def __init__(self, ip_address: str):
        self.ip_address: str = ip_address
        self.client = EthernetClient()
        self.listen_thread: threading.Thread = None
        self.is_listening = False
        self.weight = ''
        self._weight_units = 'kg'

    def start_client(self):
        self.client.connect(self.ip_address, self.port)

    def close_client(self):
        self.is_listening = False
        self.client.close()

    def set_units(self, units: str):
        if units in UNITS_CONVERSION:
            self._weight_units = units
        else:
            logging.error(f'Invalid units. Available units: {list(UNITS_CONVERSION.keys())}.')

    def clear_marel_buffer(self):
        while self.client.receive():
            pass

    def start_listening(self):
        self.is_listening = True
        self.listen_thread = threading.Thread(target=self.listen(),
                                                      name="marel listening", daemon=True)
        self.listen_thread.start()

    def stop_listening(self):
        self.is_listening = False

    def listen(self):
        while self.is_listening:
            self.start_client()
            self.clear_marel_buffer()
            while self.client.is_connected:
                time.sleep(.1)
                if buff := self.client.receive():
                    messages = buff.split('\n')
                    for msg in messages:
                        match = re.findall(self.msg_pattern, msg)
                        if len(match) > 0:
                            self.weight = float(match[0][0]) * convert_units(match[0][1], self._weight_units)
                        else:
                            self.weight = ""
                else:
                    self.weight = ""


def update_lua_code(filename:str, ip_address: str):
    download_port = PORTS['download_port']
    upload_port = PORTS['upload_port']

    # download
    download_client = EthernetClient()
    download_client.connect(ip_address, download_port)
    with open(filename, 'r') as lua_app:
        lua_script = lua_app.read()

    # TODO check return value ? To see if everything has been sent.
    if download_client.is_connected:
        download_client.send(lua_script)
        download_client.close()

    # integrity check
    upload_client = EthernetClient()
    upload_client.connect(ip_address, upload_port)

    marel_lua_script = ""

    if upload_client.is_connected:
        while True:
            msg = upload_client.receive()
            if msg == "":
                break
            marel_lua_script += msg
        upload_client.close()

    if marel_lua_script == lua_app:
        logging.info('Lua script successfully uploaded.')
    else:
        logging.info('Failed ot upload Lua Script.')


if __name__ == "__main__":
    test_ip_addr = "192.168.0.202"
    lua_script = 'marel_app.lua'

# update_lua_code(lua_script)


