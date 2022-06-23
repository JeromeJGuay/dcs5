"""
Author : JeromeJGuay
Date : May 2022

This module contains the Class relative to the DCS5_XT Board Controller and Client.

Notes # TODO
-----
 The code is written for a stylus calibration.
    Calibration should probably be done with the Finger Stylus and not the Pen Stylus
    since the magnet is further away in the pen (~5mm). If this is the case, the code should be changed.


References
----------
    https://bigfinllc.com/wp-content/uploads/Big-Fin-Scientific-Fish-Board-Integration-Guide-V2_0.pdf?fbclid=IwAR0tJMwvN7jkqxgEhRQABS0W3HLLntpOflg12bMEwM5YrDOwcHStznJJNQM

"""

import logging
import queue
import re
import socket
import threading
import time
from dataclasses import dataclass
from queue import Queue
from typing import *

import bluetooth
import pyautogui as pag

from dcs5.config import load_config, ControllerConfiguration
from dcs5.dcs5_devices_specification import load_devices_specification, DevicesSpecification
from dcs5.dcs5_control_box_statics import load_control_box_parameters, ControlBoxParameters

BOARD_MSG_ENCODING = 'UTF-8'
BUFFER_SIZE = 1024


def cycle(my_list: iter):
    index = 0
    while True:
        yield my_list[index]
        index = (index + 1) % len(my_list)


@dataclass
class InternalBoardState:
    sensor_mode: str = None
    stylus_status_msg: str = None
    stylus_settling_delay: int = None
    stylus_max_deviation: int = None
    number_of_reading: int = None

    battery_level: str = None
    board_stats: str = None
    board_interface: str = None
    calibrated: bool = None
    cal_pt_1: int = None
    cal_pt_2: int = None

    backlighting_level: int = None
    backlighting_auto_mode: bool = None
    backlighting_sensitivity: int = None


class Shouter:
    def __init__(self):
        self.input: str = None

    def is_valid_key(self):
        if isinstance(self.input, list):
            return all(map(pag.isValidKey, self.input))
        else:
            return pag.isValidKey(self.input)


class ServerInput(Shouter):
    def __init__(self):
        self.input_queue = queue.Queue()


class KeyboardInput(Shouter):
    def __init__(self):
        super(Shouter, self).__init__()
        self._with_control = False
        self._with_shift = False
        self._with_alt = False
        self.input: str = None

        self.combo = []

    def shout_to_keyboard(self, value: str):
        self.input = value
        if self.input == 'ctrl':
            self._with_control = not self._with_control
        elif self.input == 'shift':
            self._with_shift = not self._with_shift
        elif self.input == 'alt':
            self._with_alt = not self._with_alt
        else:
            self._shout_to_keyboard()

    def _shout_to_keyboard(self):
        if self._with_control:
            self.combo.append('ctrl')
            self._with_control = False
        if self._with_alt:
            self.combo.append('alt')
            self._with_alt = False
        if self._with_shift:
            self.combo.append('shift')
            self._with_shift = False

        with pag.hold(self.combo):
            logging.debug(f"Keyboard out: {'+'.join(self.combo)} {self.input}")
            if self.is_valid_key():
                pag.press(self.input)
            else:
                pag.write(str(self.input))
            self.combo = []


class BtClient:
    """
    TODO test port automatic selection.
    Notes
    -----
    Both socket and bluetooth methods(socket package) seems to be equivalent.
    """
    max_port = 65535

    def __init__(self):
        self._mac_address: str = None
        self._port: int = None
        self._buffer: str = ''
        self.socket: socket.socket = None
        self.default_timeout = .5
        self.isconnected = False

    def connect(self, mac_address, timeout: int = None):
        self._mac_address = mac_address
        logging.debug(f'Attempting to connect to board. Timeout: {timeout} seconds')
        try:
            for port in range(self.max_port):  # check for all available ports
                self.socket = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)
                self.socket.settimeout(timeout if timeout is not None else self.default_timeout)
                try:
                    port += 1
                    logging.debug(f'port: {port}')
                    self.socket.connect((self._mac_address, port))
                    self._port = port
                    self.isconnected = True
                    logging.debug(f'Connected to port {self._port}')
                    break
                except PermissionError:
                    pass
                except bluetooth.BluetoothError as err:
                    pass
            if not self.isconnected:
                logging.error('No available ports were found.')

        except OSError as err:
            logging.warning("Devices not found.")
            logging.debug(err)
        finally:
            pass
            self.socket.settimeout(self.default_timeout)

    @property
    def mac_address(self):
        return self._mac_address

    @property
    def port(self):
        return self._port

    @property
    def buffer(self):
        return self._buffer

    def send(self, command: str):
        self.socket.sendall(command.encode(BOARD_MSG_ENCODING))

    def receive(self):
        try:
            self._buffer += self.socket.recv(BUFFER_SIZE).decode(BOARD_MSG_ENCODING)
        except socket.timeout:
            pass

    def clear_all(self):
        self.receive()
        self._buffer = ""

    def pop(self, i=None):
        """Return and clear the client buffer."""
        i = len(self._buffer) if i is None else i
        buffer, self._buffer = self._buffer[:i], self._buffer[i:]
        return buffer

    def put_back(self, msg):
        """Appends at the beginning of the buffer."""
        self._buffer = msg + self._buffer

    def close(self):
        self.socket.close()


class Dcs5Controller:
    config: ControllerConfiguration
    device_specs: DevicesSpecification
    control_box_parameters: ControlBoxParameters

    dynamic_stylus_settings: bool
    output_mode: str
    reading_profile: str
    length_units: str
    stylus: str
    stylus_offset: int
    stylus_cyclical_list: Generator

    def __init__(self, config_path: str, devices_specifications_path: str, control_box_parameters_path: str):
        """

        Parameters
        ----------
        config_path
        devices_specifications_path
        control_box_settings_path
        """
        self.config_path = config_path
        self.devices_specifications_path = devices_specifications_path
        self.control_box_parameters_path = control_box_parameters_path
        self._load_configs()

        self.listen_thread: threading.Thread = None
        self.command_thread: threading.Thread = None

        self.socket_listener = SocketListener(self)
        self.command_handler = CommandHandler(self)

        self.is_listening = False
        self.is_muted = False

        self.is_sync = False
        self.ping_event_check = threading.Event()
        self.thread_barrier = threading.Barrier(2)

        self.client = BtClient()

        self.internal_board_state = InternalBoardState()  # BoardCurrentState
        self.shouter = KeyboardInput()

        self.mappable_commands = {
            "BACKLIGHT_UP": self.backlight_up,
            "BACKLIGHT_DOWN": self.backlight_down,
            "CHANGE_STYLUS": self.cycle_stylus,
            "UNITS_mm": self.change_length_units_mm,
            "UNITS_cm": self.change_length_units_cm
        }

    def _load_configs(self):
        self.config = load_config(self.config_path)
        self.devices_spec = load_devices_specification(self.devices_specifications_path)
        self.control_box_parameters = load_control_box_parameters(self.control_box_parameters_path)

        self.dynamic_stylus_settings = self.config.launch_settings.dynamic_stylus_mode
        self.output_mode = self.config.launch_settings.output_mode
        self.reading_profile = self.config.launch_settings.reading_profile
        self.length_units = self.config.launch_settings.length_units
        self.stylus: str = self.config.launch_settings.stylus
        self.stylus_offset = self.devices_spec.stylus_offset[self.stylus]
        self.stylus_cyclical_list = cycle(list(self.devices_spec.stylus_offset.keys()))

    def reload_configs(self):
        self._load_configs()

    def start_client(self, mac_address: str = None):
        if self.client.isconnected:
            logging.debug("Client Already Connected.")
        else:
            mac_address = mac_address if mac_address is not None else self.config.client.mac_address
            self.client.connect(mac_address, timeout=30)

    def close_client(self):
        if self.client.isconnected:
            if self.is_listening:
                self.stop_listening()
            self.client.close()
            self.client.isconnected = False
            time.sleep(0.5)
            logging.info('ui: Client Closed.')
        else:
            logging.info('ui: Client Already Closed')

    def restart_client(self):
        self.close_client()
        was_listening = self.is_listening
        try:
            self.start_client()
        except OSError as err:
            logging.error(f'Failed to Start_Client. Trying again ...')
            logging.debug(f'restart_client OSError: {str(err)}')
            time.sleep(0.5)
            self.restart_client()
            if was_listening:
                self.start_listening()

    def start_listening(self):
        if not self.is_listening:
            logging.debug('Starting Threads.')
            self.is_listening = True
            self.command_thread = threading.Thread(target=self.command_handler.processes_queues, name='command')
            self.command_thread.start()

            self.listen_thread = threading.Thread(target=self.socket_listener.listen, name='listen')
            self.listen_thread.start()

        logging.info('Board is Active.')

    def stop_listening(self):
        if self.is_listening:
            self.is_listening = False
            self.listen_thread.join()
            self.command_thread.join()
            logging.debug("Active Threads joined.")
            logging.debug("Queues and Socket Buffer Cleared.")
        logging.info('Board is Inactive.')

    def restart_listening(self):
        self.stop_listening()
        self.start_listening()

    def unmute_board(self):
        """Unmute board shout output"""
        if self.is_muted:
            self.is_muted = False
            logging.info('ui: Board unmuted')

    def mute_board(self):
        """Mute board shout output"""
        if not self.is_muted:
            self.is_muted = True
            logging.info('ui: Board muted')

    def sync_controller_and_board(self):
        """Init board to launch settings.
        """
        logging.info('ui: Syncing Controller and Board.')

        was_listening = self.is_listening
        self.restart_listening()

        reading_profile = self.config.reading_profiles[
            self.config.output_modes.mode_reading_profiles[self.output_mode]
        ]
        self.c_set_interface(1)
        self.c_set_sensor_mode(0)
        self.c_set_stylus_detection_message(False)
        self.c_set_backlighting_level(self.config.launch_settings.backlighting_level)
        self.c_set_stylus_settling_delay(reading_profile.settling_delay)
        self.c_set_stylus_max_deviation(reading_profile.max_deviation)
        self.c_set_stylus_number_of_reading(reading_profile.number_of_reading)
        self.c_check_calibration_state()

        self.wait_for_ping()

        if not was_listening:
            self.stop_listening()

        if (
                self.internal_board_state.sensor_mode == "length" and
                self.internal_board_state.stylus_status_msg == "disable" and
                self.internal_board_state.stylus_settling_delay == reading_profile.settling_delay and
                self.internal_board_state.stylus_max_deviation == reading_profile.max_deviation and
                self.internal_board_state.number_of_reading == reading_profile.number_of_reading
        ):
            self.is_sync = True
            logging.info("ui: Syncing successful.")
        else:
            logging.info("ui: Syncing  failed.")
            self.is_sync = False

    def wait_for_ping(self, timeout=2):
        self.c_ping()
        self.ping_event_check.set()
        logging.debug('Ping Event Set.')
        count = 0
        while self.ping_event_check.is_set():
            if count > timeout / 0.2:
                logging.debug('Ping Event Not Received')
                self.ping_event_check.clear()
                break
            count += 1
            time.sleep(0.2)

    def calibrate(self, pt: int):
        # TODO test again
        logging.info("ui: Calibration Mode Enable.")

        was_listening = self.is_listening
        self.stop_listening()

        self.client.clear_all()
        self.client.send(f"&{pt}r#")
        self.client.socket.settimeout(5)
        self.client.receive()
        self.stop_listening()
        try:
            if f'&Xr#: X={pt}\r' in self.client.buffer:
                pt_value = self.internal_board_state.__dict__[f"cal_pt_{pt}"]
                logging.info(f"ui: Calibration for point {pt}. Set stylus down at {pt_value} mm ...")
                while f'&{pt}c' not in self.client.buffer:
                    self.client.receive()
                logging.info(f'ui: Point {pt} calibrated.')
        except KeyError:
            logging.info('ui: Calibration Failed.')
        finally:
            self.client.socket.settimeout(self.client.default_timeout)

        if not was_listening:
            self.stop_listening()

    def change_length_units_mm(self):
        self.length_units = "mm"
        logging.info(f"ui: Length Units Change to mm")

    def change_length_units_cm(self):
        self.length_units = "cm"
        logging.info(f"ui: Length Units Change to cm")

    def change_stylus(self, value: str):
        """Stylus must be one of [pen, finger]"""
        self.stylus = value
        self.stylus_offset = self.devices_spec.stylus_offset[self.stylus]
        logging.info(f'ui: Stylus set to {self.stylus}. Stylus offset {self.stylus_offset}')

    def cycle_stylus(self):
        self.change_stylus(next(self.stylus_cyclical_list))

    def change_board_output_mode(self, value: str):
        """
        value must be one of  [length, bottom, top]
        """
        self.output_mode = value
        logging.debug(f'Board entry: {self.output_mode}.')
        if self.dynamic_stylus_settings is True:
            reading_profile = self.config.reading_profiles[
                self.config.output_modes.mode_reading_profiles[self.output_mode]
            ]
            self.c_set_stylus_settling_delay(reading_profile.settling_delay)
            self.c_set_stylus_max_deviation(reading_profile.max_deviation)
            self.c_set_stylus_number_of_reading(reading_profile.number_of_reading)

    def backlight_up(self):
        if self.internal_board_state.backlighting_level < self.control_box_parameters.max_backlighting_level:
            self.internal_board_state.backlighting_level += 25
            if self.internal_board_state.backlighting_level > self.control_box_parameters.max_backlighting_level:
                self.internal_board_state.backlighting_level = self.control_box_parameters.max_backlighting_level
            self.c_set_backlighting_level(self.internal_board_state.backlighting_level)
        else:
            logging.info("ui: Backlighting is already at maximum.")

    def backlight_down(self):
        if self.internal_board_state.backlighting_level > 0:
            self.internal_board_state.backlighting_level += -25
            if self.internal_board_state.backlighting_level < 0:
                self.internal_board_state.backlighting_level = 0
            self.c_set_backlighting_level(self.internal_board_state.backlighting_level)
        else:
            logging.info("ui: Backlighting is already at minimum.")

    def shout(self, value: Union[int, float, str]):
        if not self.is_muted:
            logging.debug(f"Shouted value {value}")
            self.shouter.shout_to_keyboard(value)

    def c_board_initialization(self):
        self.command_handler.queue_command("&init#", "Setting EEPROM init flag.\r")
        time.sleep(1)
        self.close_client()

    def c_ping(self):
        """This could use for something more useful. Like checking at regular interval if the board is still active:
        """
        self.command_handler.queue_command("a#", "%a:e#")

    def c_get_board_stats(self):
        self.command_handler.queue_command("b#", "regex_%b.*#")

    def c_get_battery_level(self):
        self.command_handler.queue_command('&q#', "regex_%q:.*#")

    def c_set_sensor_mode(self, value):
        """ 'length', 'alpha', 'shortcut', 'numeric' """
        self.command_handler.queue_command(
            f'&m,{value}#', ['length mode activated\r', 'alpha mode activated\r',
                             'shortcut mode activated\r', 'numeric mode activated\r'][value]
        )

    def c_set_interface(self, value: int):
        """
        FEED seems to enable box key strokes.
        """
        self.command_handler.queue_command(f"&fm,{value}#", None)
        if value == 0:
            self.internal_board_state.board_interface = "DCSLinkstream"
            logging.info(f'ui: Interface set to {self.internal_board_state.board_interface}')
        elif value == 1:
            self.internal_board_state.board_interface = "FEED"
            logging.info(f'ui: Interface set to {self.internal_board_state.board_interface}')

    def c_set_backlighting_level(self, value: int):
        if 0 <= value <= self.control_box_parameters.max_backlighting_level:
            self.command_handler.queue_command(f'&o,{value}#', None)
            self.internal_board_state.backlighting_level = value
        else:
            logging.warning(f"Backlighting level range: (0, {self.control_box_parameters.max_backlighting_level})")

    def c_set_backlighting_auto_mode(self, value: int):
        self.command_handler.queue_command(f"&oa,{value}", None)
        self.internal_board_state.backlighting_auto_mode = {True: 'auto', False: 'manual'}

    def c_set_backlighting_sensitivity(self, value: int):
        if 0 <= value <= self.control_box_parameters.max_backlighting_sensitivity:
            self.command_handler.queue_command(f"&os,{value}", None)
            self.internal_board_state.backlighting_sensitivity = value
        else:
            logging.warning(
                f"Backlighting sensitivity range: (0, {self.control_box_parameters.max_backlighting_sensitivity})")

    def c_set_stylus_detection_message(self, value: bool):
        """
        When disabled (false): %t0 %t1 are not sent
        """
        self.command_handler.queue_command(f'&sn,{int(value)}#', f'%sn:{int(value)}#\r')

    def c_set_stylus_settling_delay(self, value: int = 1):
        if 0 <= value <= self.control_box_parameters.max_settling_delay:
            self.command_handler.queue_command(f"&di,{value}#", f"%di:{value}#\r")
        else:
            logging.warning(f"Settling delay value range: (0, {self.control_box_parameters.max_settling_delay})")

    def c_set_stylus_max_deviation(self, value: int):
        if 0 <= value <= self.control_box_parameters.max_max_deviation:
            self.command_handler.queue_command(f"&dm,{value}#", f"%dm:{value}#\r")
        else:
            logging.warning(f"Settling delay value range: (0, {self.control_box_parameters.max_max_deviation})")

    def c_set_stylus_number_of_reading(self, value: int = 5):
        self.command_handler.queue_command(f"&dn,{value}#", f"%dn:{value}#\r")

    def c_restore_cal_data(self):
        self.command_handler.queue_command("&cr,m1,m2,raw1,raw2#", None)

    def _clear_cal_data(self):
        self.command_handler.queue_command("&ca#", None)
        self.calibrated = False

    def c_check_calibration_state(self):  # TODO, to be tested
        self.command_handler.queue_command('&u#', 'regex_%u:\d#\r')

    def c_set_calibration_points_mm(self, pt: int, pos: int):
        self.command_handler.queue_command(f'&{pt}mm,{pos}#', f'Cal Pt {pt} set to: {pos}\r')


class CommandHandler:
    def __init__(self, controller: Dcs5Controller):
        self.controller = controller

        self.send_queue = Queue()
        self.received_queue = Queue()
        self.expected_message_queue = Queue()

    def clear_queues(self):
        self.send_queue.queue.clear()
        self.received_queue.queue.clear()
        self.expected_message_queue.queue.clear()
        logging.debug("Handler Queues Cleared.")

    def processes_queues(self):
        self.clear_queues()
        self.controller.thread_barrier.wait()
        logging.debug('Command Handling Started')
        while self.controller.is_listening is True:
            if not self.received_queue.empty():
                self._validate_commands()
            if not self.send_queue.empty():
                self._send_command()
                time.sleep(0.08)
            time.sleep(0.02)
        logging.debug('Command Handling Stopped')

    def _validate_commands(self):
        command_is_valid = False
        received = self.received_queue.get()
        expected = self.expected_message_queue.get()
        logging.debug(f'Received: {[received]}, Expected: {[expected]}')
        if "regex_" in expected:
            match = re.findall("(" + expected.strip('regex_') + ")", received)
            if len(match) > 0:
                command_is_valid = True
        elif received == expected:
            command_is_valid = True

        if command_is_valid:
            self._process_valid_commands(received)
        else:
            logging.error(f'Invalid: Command received: {[received]}, Command expected: {[expected]}')

    def _process_valid_commands(self, received):
        logging.debug('Command Valid')
        if 'mode activated' in received:
            for i in ["length", "alpha", "shortcut", "numeric"]:
                if i in received:
                    self.controller.internal_board_state.sensor_mode = i

            logging.debug(f'{received}')

        elif "a:e" in received:
            self.controller.ping_event_check.clear()
            logging.debug('Ping Event Received.')

        elif "sn" in received:
            match = re.findall(f"%sn:(\d)#\r", received)
            if len(match) > 0:
                if match[0] == "1":
                    self.controller.internal_board_state.stylus_status_msg = "enable"
                    logging.info('ui: Stylus Status Message Enable')
                else:
                    self.controller.internal_board_state.stylus_status_msg = "disable"
                    logging.info('ui: Stylus Status Message Disable')

        elif "di" in received:
            match = re.findall(f"%di:(\d)#\r", received)
            if len(match) > 0:
                self.controller.internal_board_state.stylus_settling_delay = int(match[0])
                logging.info(f"ui: Stylus settling delay set to {match[0]}")

        elif "dm" in received:
            match = re.findall(f"%dm:(\d)#\r", received)
            if len(match) > 0:
                self.controller.internal_board_state.stylus_max_deviation = int(match[0])
                logging.info(f"ui: Stylus max deviation set to {int(match[0])}")

        elif "dn" in received:
            match = re.findall(f"%dn:(\d)#\r", received)
            if len(match) > 0:
                self.controller.internal_board_state.number_of_reading = int(match[0])
                logging.info(f"ui: Stylus number set to {int(match[0])}")

        elif "%b" in received:
            match = re.findall("%b:(.*)#", received)
            if len(match) > 0:
                logging.info(f'ui: Board State: {match[0]}')
                self.controller.internal_board_state.board_stats = match[0]

        elif "%q" in received:
            match = re.findall("%q:(-*\d*,\d*)#", received)
            if len(match) > 0:
                logging.info(f'ui: Battery level: {match[0]}')
                self.controller.internal_board_state.battery_level = match[0]

        elif "%u:" in received:
            match = re.findall("%u:(\d)#", received)
            if len(match) > 0:
                if match[0] == '0':
                    logging.info('ui: Board is not calibrated.')
                    self.controller.internal_board_state.calibrated = False
                elif match[0] == '1':
                    logging.info('ui: Board is calibrated.')
                    self.controller.internal_board_state.calibrated = True
            else:
                logging.error(f'Calibration state {self.controller.client.buffer}')

        elif 'Cal Pt' in received:
            logging.debug(received.strip("\r") + " mm")
            match = re.findall("Cal Pt (\d) set to: (\d)", received)
            if len(match) > 0:
                self.controller.internal_board_state.__dict__[f'cal_pt_{match[0][0]}'] = int(match[0][1])

    def queue_command(self, command, message=None):
        if message is not None:
            self.expected_message_queue.put(message)
        self.send_queue.put(command)
        logging.debug(f'Queuing: Command -> {[command]}, Expected -> {[message]}')

    def _send_command(self):
        command = self.send_queue.get()
        self.controller.client.send(command)
        logging.debug(f'Command Sent: {[command]}')


class SocketListener:
    def __init__(self, controller: Dcs5Controller):
        self.controller = controller
        self.message_queue = Queue()
        self.swipe_triggered = False
        self.with_ctrl = False

    def listen(self):
        self.controller.client.clear_all()
        self.message_queue.queue.clear()
        logging.debug("Listener Queue and Client Buffers Cleared.")
        self.controller.thread_barrier.wait()
        logging.debug('Listener Queue cleared & Client Buffer Clear.')
        try:
            logging.debug('Listening started')
            while self.controller.is_listening:
                self.controller.client.receive()
                if len(self.controller.client.buffer) > 0:
                    self._split_board_message()
                    self._process_board_message()
            logging.debug('Listening stopped')
        except TimeoutError:
            logging.error("Connection timeout. Board Disconnected.")
            try:
                self.controller.close_client()
            except RuntimeError:
                pass

    def _split_board_message(self):
        delimiters = ["\n", "\r", "#", "Rebooting in 2 seconds ..."]
        for d in delimiters:
            msg = self.controller.client.buffer.split(d)
            if len(msg) > 1:
                self.message_queue.put(self.controller.client.pop(len(msg[0] + d)))

    def _process_board_message(self):
        """ANALYZE SOLICITED VS UNSOLICITED MESSAGE"""
        while not self.message_queue.empty():
            message = self.message_queue.get()
            logging.debug(f'Received Message: {message}')
            out_value = None
            msg_type, msg_value = self._decode_board_message(message)
            logging.debug(f"Message Type: {msg_type}, Message Value: {msg_value}")
            if msg_type == "controller_box_key":
                out_value = self.controller.config.key_maps.control_box[
                    self.controller.devices_spec.control_box.keys_layout[msg_value]
                ]

            elif msg_type == 'swipe':
                self.swipe_value = msg_value
                if msg_value > self.controller.config.output_modes.swipe_threshold:
                    self.swipe_triggered = True

            elif msg_type == 'length':
                if self.swipe_triggered is True:
                    self._check_for_stylus_swipe(msg_value)
                else:
                    out_value = self._map_board_length_measurement(msg_value)
            elif msg_type == "solicited":
                self.controller.command_handler.received_queue.put(msg_value)

            if out_value is not None:
                self._process_output(out_value)

            time.sleep(0.001)

    @staticmethod
    def _decode_board_message(value: str):
        pattern = "%t,([0-9])#|%l,([0-9]*)#|%s,([0-9]*)#|F,([0-9]{2})#"
        match = re.findall(pattern, value)
        if len(match) > 0:
            if match[0][1] != "":
                return 'length', int(match[0][1])
            elif match[0][2] != "":
                return 'swipe', int(match[0][2])
            elif match[0][3] != "":
                return 'controller_box_key', match[0][3]
        else:
            return 'solicited', value

    def _process_output(self, value):
        if isinstance(value, list):
            for _value in value:
                self._process_output(_value)
        else:
            if value in self.controller.mappable_commands:
                self.controller.mappable_commands[value]()
            else:
                self.controller.shout(value)

    def _map_board_length_measurement(self, value: int):
        if self.controller.output_mode == 'length':
            out_value = value - self.controller.stylus_offset
            if self.controller.length_units == 'cm':
                out_value /= 10
            return out_value
        else:
            index = int(
                (value - self.controller.devices_spec.board.relative_zero)
                / self.controller.devices_spec.board.key_to_mm_ratio
            )
            if index < self.controller.devices_spec.board.number_of_keys:
                return self.controller.config.key_maps.board[
                    self.controller.devices_spec.board.keys_layout[self.controller.output_mode][index]
                ]

    def _check_for_stylus_swipe(self, value: str):
        self.swipe_triggered = False
        segments_limits = self.controller.config.output_modes.segments_limits
        if value <= segments_limits[-1]:
            for l_max, l_min, mode in zip(segments_limits[1:],
                                          segments_limits[:-1],
                                          self.controller.config.output_modes.segments_mode):
                if l_max >= int(value) > l_min:
                    self.controller.change_board_output_mode(mode)
                    break
