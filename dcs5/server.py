import socket
import logging

from dcs5.logger import init_logging

from dcs5 import VERSION, DEFAULT_DEVICES_SPECIFICATION_FILE, DEFAULT_CONTROLLER_CONFIGURATION_FILE, \
    XT_BUILTIN_PARAMETERS

from dcs5.controller import Dcs5Controller
from dcs5.utils import resolve_relative_path

ENCODING = 'UTF-8'
BUFFER_SIZE = 1024

HOST = "127.0.0.1"  # Standard loopback interface address (localhost)
PORT = 65431  # Port to listen on (non-privileged ports are > 1023)

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
    def __init__(self):
        self.is_active = True
        self.socket: socket.socket = None
        self.default_timeout = .5

    def bind(self, host, port):
        logging.info('App Server is Online')
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.bind((host, port))

    def runserver(self):
        self.socket.listen(1)
        conn, addr = self.socket.accept()
        with conn:
            logging.info(f"New Client {addr}.")
            while self.is_active:
                data = conn.recv(BUFFER_SIZE).decode(ENCODING)
                if not data:
                    pass
                elif data == "hello board":
                    conn.sendall("hello andes".encode(ENCODING))
                    logging.info('The Client Said Hello.')
                elif data == "goodbye":
                    logging.info(f'{addr} said goodbye.')
                    conn.sendall("yay".encode(ENCODING))
                    break
                elif data == "units mm":
                    conn.sendall("yay".encode(ENCODING))
                    CONTROLLER.change_length_units_mm()
                elif data == "units cm":
                    conn.sendall("yay".encode(ENCODING))
                    CONTROLLER.change_length_units_cm()
                elif data == "restart":
                    conn.sendall("yay".encode(ENCODING))
                    CONTROLLER.restart_client()
                elif data == "mute":
                    conn.sendall("yay".encode(ENCODING))
                    CONTROLLER.mute_board()
                elif data == "unmute":
                    conn.sendall("yay".encode(ENCODING))
                    CONTROLLER.unmute_board()
                elif data == "mode top":
                    conn.sendall("yay".encode(ENCODING))
                    CONTROLLER.change_board_output_mode('top')
                elif data == "mode bottom":
                    conn.sendall("yay".encode(ENCODING))
                    CONTROLLER.change_board_output_mode('bottom')
                elif data == "mode length":
                    conn.sendall("yay".encode(ENCODING))
                    CONTROLLER.change_board_output_mode('length')
                elif data == "state":
                    state = {
                        'isconnected': CONTROLLER.client.isconnected,
                        'mode': CONTROLLER.output_mode,
                        'units': CONTROLLER.length_units,
                        'stylus': CONTROLLER.stylus}
                    conn.sendall(str(state).encode(ENCODING))
                else:
                    conn.sendall("nay".encode(ENCODING))

    def close(self):
        self.socket.close()


def start_server():
    s = Server()
    s.bind(HOST, PORT)
    while True:
        s.runserver()


if __name__ == "__main__":
    start_server()

