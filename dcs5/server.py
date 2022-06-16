import socket
import logging
import re

from dcs5.logger import init_logging

from dcs5 import VERSION, DEFAULT_DEVICES_SPECIFICATION_FILE, DEFAULT_CONTROLLER_CONFIGURATION_FILE, \
    XT_BUILTIN_PARAMETERS

from dcs5.controller import Dcs5Controller
from dcs5.utils import resolve_relative_path

ENCODING = 'UTF-8'
BUFFER_SIZE = 1024

VALID_AUTH_KEY = ["9999"]

HOST = "127.0.0.1"  # Standard loopback interface address (localhost)
PORT = 9999  # Port to listen on (non-privileged ports are > 1023)

init_logging(stdout_level="debug")


def start_dcs5_controller(
        config_path=DEFAULT_CONTROLLER_CONFIGURATION_FILE,
        devices_specifications_path=DEFAULT_DEVICES_SPECIFICATION_FILE,
        control_box_parameters_path=XT_BUILTIN_PARAMETERS
):
    config_path = resolve_relative_path(config_path, __file__)
    devices_specifications_path = resolve_relative_path(devices_specifications_path, __file__)
    control_box_parameters_path = resolve_relative_path(control_box_parameters_path, __file__)

    controller = Dcs5Controller(config_path, devices_specifications_path, control_box_parameters_path)
    controller.start_client()
    if controller.client.isconnected:
        controller.sync_controller_and_board()
        controller.start_listening()

    return controller


CONTROLLER = start_dcs5_controller()


class Server:
    """
    Add a Queue to Push the server, new shouted ? New Shouter ?
    """
    tag_i = "%"
    tag_v = ":"
    sep_v = ","
    tag_f = "#"

    def __init__(self):
        self.is_connected = False
        self.socket: socket.socket = None
        self.conn: socket.socket = None
        self.regex = f"{self.tag_i}(.*?){self.tag_v}(.*?)(?:{self.sep_v}|$)*{self.tag_f}"
        self.default_timeout = .5

    def bind(self, host, port):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.bind((host, port))
        logging.info('App Server is Online')

    def close(self):
        if self.is_connected:
            self.conn.close()
        self.socket.close()

    def format_msg(self, command, args):
        if args is None:
            args = []
        return self.tag_i + command + self.tag_v + self.sep_v.join(args) + self.tag_f

    def decode(self, msg):
        match = re.findall(self.regex, msg)
        logging.debug(f'Server: Received: {msg}')
        if len(match) > 0:
            m = match[0]
            command = m[0]
            args = m[1].split(self.sep_v)
            return command, args
        else:
            logging.debug(f'Server: Invalid Command')
            return None, None

    def send(self, command, args: list = None):
        msg = self.format_msg(command, args)
        logging.debug(f'Server: Sent {msg}')
        self.conn.sendall(msg.encode(ENCODING))

    def validate_connection(self, conn: socket):
        msg = conn.recv(BUFFER_SIZE).decode(ENCODING)
        logging.debug(f'Server: Auth Received: {msg}')
        command, args = self.decode(msg)
        if args[0] in VALID_AUTH_KEY:
            logging.debug('Authentication Successful')
            self.is_connected = True
            self.conn = conn
            msg = self.format_msg('auth', ['1'])
            conn.sendall(msg.encode(ENCODING))
        else:
            logging.debug('Authentication Failed')
            msg = self.format_msg('auth', ['0'])
            conn.sendall(msg.encode(ENCODING))
            conn.close()

    def runserver(self):
        self.socket.listen(1)
        conn, addr = self.socket.accept()
        logging.debug(f"New Client {addr}.")

        self.validate_connection(conn)

        while self.is_connected:
            data = self.conn.recv(BUFFER_SIZE).decode(ENCODING)
            if not data:
                try:
                    self.send('ping')
                except BrokenPipeError as err:
                    logging.debug(f'Client {addr} disconnected.')
                    self.is_connected = False
                    self.conn.close()
                continue
            else:
                command, args = self.decode(data)

            if command == "ping":
                self.send("ping")
                logging.debug(f'{addr} pinged.')

            elif command == "goodbye":
                self.send('goodbye')
                logging.debug(f'Client {addr} disconnected.')
                self.is_connected = False
                self.conn.close()

            elif command == "units":
                if args[0] == "mm":
                    CONTROLLER.change_length_units_mm()
                    logging.debug(f'Server: Valid Command')
                    self.send('valid')
                elif args[0] == "cm":
                    CONTROLLER.change_length_units_cm()
                    logging.debug(f'Server: Valid Command')
                    self.send('valid')
                else:
                    logging.debug(f'Server: Inalid Arguments')

            elif command == "restart":
                self.send("valid")
                logging.debug(f'Server: Valid Command')
                CONTROLLER.restart_client()
                if CONTROLLER.client.isconnected:
                    CONTROLLER.sync_controller_and_board()
                    CONTROLLER.start_listening()
                self.send('Board Ready')

            elif command == "mute":
                self.send("valid")
                logging.debug(f'Server: Valid Command')
                CONTROLLER.mute_board()

            elif command == "unmute":
                self.send("valid")
                logging.debug(f'Server: Valid Command')
                CONTROLLER.unmute_board()

            elif command == "mode":
                if args[0] == "top":
                    self.send("valid")
                    logging.debug(f'Server: Valid Command')
                    CONTROLLER.change_board_output_mode('top')
                elif args[0] == "bottom":
                    self.send("valid")
                    logging.debug(f'Server: Valid Command')
                    CONTROLLER.change_board_output_mode('bottom')
                elif args[0] == "length":
                    self.send("valid")
                    logging.debug(f'Server: Valid Command')
                    CONTROLLER.change_board_output_mode('length')
                else:
                    logging.debug(f'Server: Invalid Arguments')

            elif data == "state":
                state = {
                    'isconnected': CONTROLLER.client.isconnected,
                    'mode': CONTROLLER.output_mode,
                    'units': CONTROLLER.length_units,
                    'stylus': CONTROLLER.stylus}
                conn.sendall(str(state).encode(ENCODING))
            else:
                logging.debug(f'Server: Invalid Command')


def start_server():
    s = Server()
    s.bind(HOST, PORT)

    try:
        while 1:
            s.runserver()
    except KeyboardInterrupt:
        pass
    finally:
        logging.debug('Dcs5Server: Shutting Down Server')
        s.close()


if __name__ == "__main__":
    start_server()

