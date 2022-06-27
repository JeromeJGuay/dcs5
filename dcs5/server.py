import socket
import logging
import re
import json
import time

from dcs5 import VERSION, DEFAULT_DEVICES_SPECIFICATION_FILE, DEFAULT_CONTROLLER_CONFIGURATION_FILE, \
    XT_BUILTIN_PARAMETERS, DEFAULT_SERVER_CONFIGURATION_FILE

from dcs5.config import load_server_config

from dcs5.controller import Dcs5Controller
from dcs5.utils import resolve_relative_path

ENCODING = 'UTF-8'
BUFFER_SIZE = 1024

VALID_AUTH_KEY = ["9999"]


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


class Server:
    """Server communicates with json serialization."""

    def __init__(self):
        self.socket: socket.socket = None
        self.controller: Dcs5Controller = None
        self.total_connections = 0

    def start_controller(self):
        self.controller = start_dcs5_controller()

    def bind(self, host, port):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.bind((host, port))
        logging.debug(f'Socket name: {self.socket.getsockname()}')
        logging.info(f'Dcs5SServer: Online. ({host}:{port})')

    def close(self):
        self.socket.close()

    def listen(self):
        self.socket.listen(1)
        while 1:
            auth_response = 0
            command_response = 0
            state = {
                "connected": None,
                "mode": None,
                "units": None,
                "stylus": None
            }
            logging.info('Dcs5SServer: Waiting for Client ...')
            conn, addr = self.socket.accept()
            logging.debug(f"Dcs5Server: New Client {addr}.")

            data = conn.recv(BUFFER_SIZE).decode(ENCODING)
            logging.debug('Dcs5Server: Receiving Done')
            if data:
                json_data = json.loads(data)
                logging.debug(f'Dcs5Server: Data Received {json_data}')
                # TODO LOGGING
                if json_data['auth'] in VALID_AUTH_KEY:
                    auth_response = 1
                    command_response = self.process_command(json_data['command'])
                    if self.controller is not None:
                        state.update({
                            "connected": self.controller.client.isconnected,
                            "mode": self.controller.output_mode,
                            "units": self.controller.length_units,
                            "stylus": self.controller.stylus
                        })

                response = {
                    'auth': auth_response,
                    'command': command_response,
                    'state': state
                }

                conn.sendall(
                    json.dumps(
                        response
                    ).encode(ENCODING)
                )
                logging.debug(f'Dcs5Server: Data Sent. {response}')

            conn.close()
            self.total_connections += 1
            logging.debug(f'Dcs5Server: {addr} socket closed. total_connections: {self.total_connections}')

    def process_command(self, command: str):
        if command == "ping":
            return 1
        if command == "units_mm":
            if self.controller is not None:
                self.controller.change_length_units_mm()
            return 1
        if command == "units_cm":
            if self.controller is not None:
                self.controller.change_length_units_cm()
            return 1
        if command == "stylus_pen":
            if self.controller is not None:
                self.controller.change_stylus('pen')
            return 1
        if command == "stylus_finger":
            if self.controller is not None:
                self.controller.change_stylus('finger')
            return 1
        if command == "mode_top":
            if self.controller is not None:
                self.controller.change_board_output_mode('top')
            return 1
        if command == "mode_bot":
            if self.controller is not None:
                self.controller.change_board_output_mode('bottom')
            return 1
        if command == "mode_length":
            if self.controller is not None:
                self.controller.change_board_output_mode('length')
            return 1
        if command == "mute":
            if self.controller is not None:
                self.controller.mute_board()
            return 1
        if command == "unmute":
            if self.controller is not None:
                self.controller.unmute_board()
            return 1

        return 0


def start_server(start_controller: bool = True,
                 reconnection_attempts=5,
                 host: str = None,
                 port: int = None):

    server_config = load_server_config(resolve_relative_path(DEFAULT_SERVER_CONFIGURATION_FILE,__file__))

    host = host if host is not None else server_config.host
    port = port if port is not None else server_config.port

    s = Server()
    if start_controller is True:
        logging.debug(f'Dcs5Server: Starting Controller. Controller Version {VERSION}')
        s.start_controller()
    try:
        count = 0
        while 1:
            try:
                s.bind(host, port)
                count = 0
                s.listen()
            except Exception as err:
                s.close()
                time.sleep(1)
                logging.error(f"Dcs5Server: Error on listen loop {err}. Relaunching Server.")
                count += 1
                if count > reconnection_attempts:
                    logging.error(f"Dcs5Server: Failed to relaunching Server.")
                    break
    except KeyboardInterrupt as err:
        logging.debug(f'Dcs5Server: KeyBoard Interrupt')
    finally:
        logging.info('Dcs5Server: Shutting Down Server')
        if s.controller is not None:
            s.controller.close_client()
        s.close()
