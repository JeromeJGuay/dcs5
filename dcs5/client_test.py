import socket
import logging
import re
import time

TEST_STRING = "%mycommand:var1,var2#%mycommand2:#"  # TODO REMOVE

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
            msg = self.socket.recv(BUFFER_SIZE).decode(ENCODING)
            logging.debug(f"Dcs5Client: Recv: {msg}")
            return self.decode(msg)
        except socket.timeout:
            return None, None

    def query(self, command, args: list = None):
        self.send(self.format_msg(command, args))
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
        if command == 'restart':
            logging.debug('Board Controller Restarting')
            logging.debug('Waiting 10s')
            count = 0
            while count < 10:
                command, args = self.receive()
                time.sleep(1)
                if command == 'Board Ready':
                    logging.debug('Board Controller Ready')
                    break
                count += 1
            if count >= 10:
                logging.critical('Board did not answer.')

    def c_units_mm(self):
        command, args = self.query('units', ['mm'])
        if command == 'mm':
            logging.debug('Board Controller units mm')

    def c_units_cm(self):
        command, args = self.query('units', ['cm'])
        if command == 'cm':
            logging.debug('Board Controller units cm')

    def c_mute(self):
        command, args = self.query('mute')
        if command == 'mute':
            logging.debug('Board Controller mode muted')

    def c_unmute(self):
        command, args = self.query('unmute')
        if command == 'unmute':
            logging.debug('Board Controller mode unmuted')

    def c_mode_top(self):
        command, args = self.query('mode', ['top'])
        if command == 'top':
            logging.debug('Board Controller mode top')

    def c_mode_length(self):
        command, args = self.query('mode', ['length'])
        if command == 'length':
            logging.debug('Board Controller mode length')

    def c_mode_bot(self):
        command, args = self.query('mode', ['bot'])
        if command == 'bot':
            logging.debug('Board Controller mode bot')

    def c_state(self):
        command, args = self.query('restart')
        if command == "state":
            state = {
                'isconnected': args[0], 'mode': args[1],
                'units': args[2], 'stylus': args[3]
            }
            logging.info(f'Board Controller State: {state}')


def test_client():
    client = Dcs5Client()
    client.connect(HOST, PORT, AUTH_KEY)

    return client


if __name__ == "__main__":
    c = test_client()
