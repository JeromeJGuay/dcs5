import socket
import time
import threading
import logging
import re
import queue

TEST_STRING = "%mycommand:var1,var2#%mycommand2:#" #TODO REMOVE

# PUT THIS SOMEWHERE ELSE
AUTH_KEY = "9999"
HOST = "127.0.0.1"  # The server's hostname or IP address
PORT = 9999  # The port used by the server

ENCODING = 'UTF-8'
BUFFER_SIZE = 1024

logging.getLogger().setLevel('DEBUG')


class Dcs5Client:
    tag_i = "%"
    tag_v = ":"
    sep_v = ","
    tag_f = "#"

    def __init__(self):
        self.socket: socket.socket = None
        self.regex = f"{self.tag_i}(.*?){self.tag_v}(.*?)(?:{self.sep_v}|$)*{self.tag_f}"
        self.is_connected = False

    def connect(self, host: str, port: int, auth_key: str, timeout=.05):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.settimeout(timeout)
        self.socket.connect((host, port))
        command, args = self.query(self.format_msg('auth', [auth_key]))
        logging.debug(f'recv {command} {args}')
        if command == "auth":
            if args[0] == "1":
                logging.debug('Authentication Successful. Board Connected.')
                self.is_connected = True
            else:
                logging.debug('Authentication Failed.')
                self.socket.close()
        else:
            logging.critical('Wrong message sent by the server.')

    def close(self):
        self.is_connected = False
        self.socket.close()

    def format_msg(self, command, args):
        if args is None:
            args = []
        return self.tag_i + command + self.tag_v + self.sep_v.join(args) + self.tag_f

    def decode(self, msg):
        match = re.findall(self.regex, msg)
        if len(match) > 0:
            m = match[0]
            command = m[0]
            args = m[1].split(self.sep_v)
            logging.debug(f'Dcs5Client: Decoded Msg: {command, args}')
            return command, args
        else:
            return None, None

    def send(self, msg):
        self.socket.sendall(msg.encode(ENCODING))
        logging.debug(f"Dcs5Client: Sent: {msg}")

    def receive(self):
        try:
            msg =self.socket.recv(BUFFER_SIZE).decode(ENCODING)
            logging.debug(f"Dcs5Client: Recv: {msg}")
            return self.decode(msg)
        except socket.timeout:
            return None

    def query(self, command, args: list = None):
        self.send(command, args)
        return self.receive()

    def ping_server(self):
        command, args = self.query("ping")
        if command == 'ping':
            logging.debug('Board Ping Back')

    def say_goodbye(self):
        command, args = self.query('goodbye')
        if command == 'goodbye':
            logging.debug('Board Ping Back')

    def c_restart(self):
        command, args = self.query('restart')
        if command == 'valid':
            logging.debug('Board Controller Restarting')

    def c_state(self):
        pass
        # 'isconnected': CONTROLLER.client.isconnected,
        # 'mode': CONTROLLER.output_mode,
        # 'units': CONTROLLER.length_units,
        # 'stylus': CONTROLLER.stylus}



def test_client():
    client = Dcs5Client()
    client.connect(HOST, PORT, AUTH_KEY)

    return client


if __name__ == "__main__":
    c=test_client()