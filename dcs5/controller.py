"""
TODO
----
Class to handle interfacing error.

Notes
-----
 The code is written for a stylus calibration.
    Calibration should probably be done with the Finger Stylus and not the Pen Stylus
    since the magnet is further away in the pen (~5mm). If this is the case, the code should be changed.


References
----------
    https://bigfinllc.com/wp-content/uploads/Big-Fin-Scientific-Fish-Board-Integration-Guide-V2_0.pdf?fbclid=IwAR0tJMwvN7jkqxgEhRQABS0W3HLLntpOflg12bMEwM5YrDOwcHStznJJNQM


# MAKE THE CALIBRATION FILE EDITABLE (.dcs5board.conf)
# CLEAR EVERYTHING AFTER IDLING FOR MORE THAN X seconds.
# PERIODICALLY CHECK BATTERY LEVELS
"""
import argparse
import logging
import socket
import threading
import re
from typing import *
import time
import pyautogui as pag

from pathlib import PurePath
from utils import json2dict, resolve_relative_path
from dataclasses import dataclass
from queue import Queue

BOARD_MSG_ENCODING = 'UTF-8'
BUFFER_SIZE = 1024
### Turn this into a data class ?
SETTINGS = json2dict(resolve_relative_path('src_files/default_settings.json', __file__))


CLIENT_SETTINGS = SETTINGS['bluetooth']
DEVICE_NAME = CLIENT_SETTINGS["DEVICE_NAME"]
PORT = CLIENT_SETTINGS["PORT"]
DCS5_ADDRESS = CLIENT_SETTINGS["MAC_ADDRESS"]

BOARD_SETTINGS = SETTINGS['board']
DEFAULT_SETTLING_DELAY = {'measure': BOARD_SETTINGS['DEFAULT_SETTLING_DELAY'], 'typing': 1}
DEFAULT_MAX_DEVIATION = {'measure': BOARD_SETTINGS['DEFAULT_MAX_DEVIATION'], 'typing': 1}
DEFAULT_NUMBER_OF_READING = {'measure': BOARD_SETTINGS['DEFAULT_NUMBER_OF_READING'], 'typing': 1}

MAX_SETTLING_DELAY = BOARD_SETTINGS['MAX_SETTLING_DELAY']
MAX_MAX_DEVIATION = BOARD_SETTINGS['MAX_MAX_DEVIATION']

DEFAULT_BACKLIGHTING_LEVEL = BOARD_SETTINGS['DEFAULT_BACKLIGHTING_LEVEL']
MIN_BACKLIGHTING_LEVEL = BOARD_SETTINGS['MIN_BACKLIGHTING_LEVEL']
MAX_BACKLIGHTING_LEVEL = BOARD_SETTINGS['MAX_BACKLIGHTING_LEVEL']
DEFAULT_BACKLIGHTING_AUTO_MODE = BOARD_SETTINGS['DEFAULT_BACKLIGHTING_AUTO_MODE']
DEFAULT_BACKLIGHTING_SENSITIVITY = BOARD_SETTINGS['DEFAULT_BACKLIGHTING_SENSITIVITY']
MIN_BACKLIGHTING_SENSITIVITY = BOARD_SETTINGS['MIN_BACKLIGHTING_SENSITIVITY']
MAX_BACKLIGHTING_SENSITIVITY = BOARD_SETTINGS['MAX_BACKLIGHTING_SENSITIVITY']

SWIPE_THRESHOLD = 5

XT_KEYS_MAP = {
    "01": "a1",
    "02": "a2",
    "03": "a3",
    "04": "a4",
    "05": "a5",
    "06": "a6",
    "07": "b1",
    "08": "b2",
    "09": "b3",
    "10": "b4",
    "11": "b5",
    "12": "b6",
    "13": "1",
    "14": "2",
    "15": "3",
    "16": "4",
    "17": "5",
    "18": "6",
    "19": "7",
    "20": "8",
    "21": "9",
    "22": ".",
    "23": "0",
    "24": "skip",
    "25": "enter",
    "26": "c1",
    "27": "up",
    "28": "left",
    "29": "right",
    "30": "down",
    "31": "del",
    "32": "mode",
}

BOARD_KEYS_MAP = {
    'top': 7 * ['space'] + \
           list('abcdefghijklmnopqrstuvwxyz') + \
           [f'{i + 1}B' for i in range(8)] + \
           6 * ['space'] + 2 * ['del_last'],
    'bottom': 7 * ['space'] + \
              list('01234.56789') + \
              ['view', 'batch', 'tab', 'histo', 'summary', 'dismiss', 'fish', 'sample',
               'sex', 'size', 'light_bulb', 'scale', 'location', 'pit_pwr', 'settings'] + \
              [f'{i + 1}G' for i in range(8)] + \
              6 * ['space'] + 2 * ['del_last'], }

#seperate file json config TODO
SHOUT_MAPPING = {
    'a1': 'f1',
    'a2': 'f3',
    'a3': 'f4',
    'a4': 'f5',
    'a5': 'f8',
    'a6': 'f9',
    'b1': 'f10',
    'b2': 'f11',
    'b3': 'f12',
    'b4': 'escape',
    'b5': ['Y', 'enter'],
    'b6': 'backspace',
    'space': 'space',
    'skip': 'pagedown',
    'enter': 'enter',
    'del_last': 'backspace',
    'del': 'delete',
    'up': 'up',
    'down': 'down',
    'left': 'left',
    'right': 'right',
    '1B': '-'
}

# STYLUS PHYSICAL MEASUREMENTS.

STYLUS_OFFSET = {'pen': 6, 'finger': 1}  # mm -> check calibration procedure. TODO
BOARD_KEY_RATIO = 15.385  # ~200/13
BOARD_KEY_DETECTION_RANGE = 2
BOARD_KEY_ZERO = -3.695 - BOARD_KEY_DETECTION_RANGE
BOARD_NUMBER_OF_KEYS = 49

active_thread_sync_barrier = threading.Barrier(2)


def shout_to_keyboard(value: str, with_control=False):
    if value in SHOUT_MAPPING:
        key = SHOUT_MAPPING[value]
        if with_control is True:
            with pag.hold('ctrl'):
                pag.press(key)
        else:
            pag.press(key)
    elif isinstance(value, (int, float)):
        pag.write(str(value))
    elif str(value) in '.0123456789abcdefghijklmnopqrstuvwxyz':
        pag.press(value)
    else:
        logging.info('Key not mapped to keyboard.')


class Dcs5Client:
    """
    Notes
    -----
    Both socket and bluetooth methods(socket package) seems to be equivalent.
    """

    def __init__(self):
        self._mac_address: str = None
        self._port: int = None
        self._buffer: str = ''
        self.socket: socket.socket = None
        self.default_timeout = .5

    def connect(self, address: str = None, port: int = None, timeout: int = None):
        self.socket = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)
        self.socket.settimeout(timeout if timeout is not None else self.default_timeout)

        self._mac_address = address if address is not None else self._mac_address
        self._port = port if port is not None else self._port
        self.socket.connect((self._mac_address, self._port))

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
        self.socket.send(command.encode(BOARD_MSG_ENCODING))

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
        """Appends at the begining of the buffer."""
        self._buffer = msg + self._buffer

    def close(self):
        self.socket.close()


@dataclass(unsafe_hash=True, init=True)
class Dcs5UserSettings:
    #TODO
    stylus_settling_delay: int = None
    stylus_max_deviation: int = None
    number_of_reading: int = None


@dataclass(unsafe_hash=True, init=True)
class Dcs5BoardState:
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


class Dcs5Controller:
    """
    Notes
    -----
    Firmware update command could be added:
        %h,VER,BR#
        see documentations
    """

    def __init__(self, shout_method='Keyboard', dynamic_stylus_settings=False):
        Dcs5BoardState.__init__(self)
        threading.Thread.__init__(self)

        self.board_state = Dcs5BoardState()
        self.listener = Dcs5Listener(self)
        self.handler = Dcs5Handler(self)
        self.is_listening = False
        self.is_muted = False

        self.listen_thread: threading.Thread = None
        self.command_thread: threading.Thread = None

        self.is_sync = False
        self.ping_received = False

        self.client = Dcs5Client()
        self.client_isconnected = False

        self.stylus: str = 'pen'  # [finger/pen]
        self.stylus_offset: str = STYLUS_OFFSET['pen']
        self.stylus_modes_settling_delay: Dict[str: int] = DEFAULT_SETTLING_DELAY
        self.stylus_modes_number_of_reading: Dict[str: int] = DEFAULT_NUMBER_OF_READING
        self.stylus_modes_max_deviation: Dict[str: int] = DEFAULT_MAX_DEVIATION

        self.shout_method = shout_method
        self.dynamic_stylus_settings = dynamic_stylus_settings
        self.board_output_mode = 'center'

    def start_client(self, address: str = None, port: int = None):
        logging.info(f'Attempting to connect to board via port {port}.')
        if self.client_isconnected:
            logging.info("Client Already Connected.")
        else:
            logging.info('Trying to connect for 30 s.')
            self.client.connect(address, port, timeout=30)
            self.client_isconnected = True
            logging.info('Connection Successful.\n')

    def close_client(self):
        if self.client_isconnected:
            if self.is_listening:
                self.stop_listening()
            self.client.close()
            self.client_isconnected = False
            logging.info('Client Closed.')
        else:
            logging.info('Client Already Closed')

    def restart_client(self):
        self.close_client()
        try:
            self.start_client()
        except OSError as err:
            logging.error(f'Start_Client, OSError: {str(err)}. Trying again ...')
            time.sleep(0.5)
            self.restart_client()

    def start_listening(self):
        if not self.is_listening:
            logging.info('Starting Threads.')
            self.is_listening = True
            self.command_thread = threading.Thread(target=self.handler.processes_queues, name='command')
            self.command_thread.start()

            self.listen_thread = threading.Thread(target=self.listener.listen, name='listen')
            self.listen_thread.start()

        logging.info('Board is Active.')

    def stop_listening(self):
        if self.is_listening:
            self.is_listening = False
            self.listen_thread.join()
            self.command_thread.join()
            logging.info("Active Threads joined.")
            logging.info("Queues and Socket Buffer Cleared.")
        logging.info('Board is Inactive.')

    def restart_listening(self):
        self.stop_listening()
        self.start_listening()

    def unmute_board(self):
        """Unmute board shout output"""
        if self.is_muted:
            self.is_muted = False
            logging.info('Board unmuted')

    def mute_board(self):
        """Mute board shout output"""
        if not self.is_muted:
            self.is_muted = True
            logging.info('Board muted')

    def sync_controller_and_board(self):
        """Init board to default settings.
        TODO have the default settings comme from an attributes. Json file maybe
        """
        logging.info('Syncing Controller and Board.')

        was_listening = self.is_listening
        self.restart_listening()

        self.c_set_interface(1)
        self.c_set_sensor_mode(0)
        self.c_set_backlighting_level(DEFAULT_BACKLIGHTING_LEVEL)
        self.c_set_stylus_detection_message(False)
        self.c_set_stylus_settling_delay(DEFAULT_SETTLING_DELAY['measure'])
        self.c_set_stylus_max_deviation(DEFAULT_MAX_DEVIATION['measure'])
        self.c_set_stylus_number_of_reading(DEFAULT_NUMBER_OF_READING['measure'])
        self.c_check_calibration_state()

        self.wait_for_ping()

        if not was_listening:
            self.stop_listening()

        if (self.board_state.sensor_mode == "length" and
            self.board_state.stylus_status_msg == "disable" and
            self.board_state.stylus_settling_delay == DEFAULT_SETTLING_DELAY["measure"] and
            self.board_state.stylus_max_deviation == DEFAULT_MAX_DEVIATION["measure"] and
            self.board_state.number_of_reading == DEFAULT_NUMBER_OF_READING["measure"]
        ):
            self.is_sync = True
            logging.info("Syncing successful.")
        else:
            logging.info("Syncing  failed.")
            self.is_sync = False

    def wait_for_ping(self, timeout=2):
        self.c_ping()
        count = 0
        while True:
            if self.ping_received or count > timeout/0.2:
                break
            count += 1
            time.sleep(0.2)
        self.ping_received = False

    def calibrate(self, pt: int):
        #TODO test again
        logging.info("Calibration Mode Enable.")

        was_listening = self.is_listening
        self.stop_listening()

        self.client.clear_all()
        self.client.send(f"&{pt}r#")
        self.client.socket.settimeout(5)
        self.client.receive()
        self.stop_listening()
        try:
            if f'&Xr#: X={pt}\r' in self.client.buffer:
                pt_value = self.board_state.__dict__[f"cal_pt_{pt}"]
                logging.info(f"Calibration for point {pt}. Set stylus down at {pt_value} mm ...")
                while f'&{pt}c' not in self.client.buffer:
                    self.client.receive()
                logging.info(f'Point {pt} calibrated.')
        except KeyError:
            logging.info('Calibration Failed.')
        finally:
            self.client.socket.settimeout(self.client.default_timeout)

        if not was_listening:
            self.stop_listening()

    def change_stylus(self, value: str):
        """Stylus must be one of [pen, finger]"""
        self.stylus = value
        self.stylus_offset = STYLUS_OFFSET[self.stylus]
        logging.info(f'Stylus set to {self.stylus}. Stylus offset {self.stylus_offset}')

    def cycle_stylus(self):
        if self.stylus == 'pen':
            self.change_stylus('finger')
        else:
            self.change_stylus('pen')

    def change_board_output_mode(self, value: str):
        """
        value must be one of  [center, bottom, top]
        """
        self.board_output_mode = value
        mode = {'center': 'measure', 'bottom': 'typing', 'top': 'typing'}[value]
        if self.dynamic_stylus_settings is True:
            self.c_set_stylus_settling_delay(self.stylus_modes_settling_delay[mode])
            self.c_set_stylus_number_of_reading(self.stylus_modes_number_of_reading[mode])
            self.c_set_stylus_max_deviation(self.stylus_modes_max_deviation[mode])

    def change_backlighting_level(self, value: int):
        if value == 1:
            if self.board_state.backlighting_level < MAX_BACKLIGHTING_LEVEL:
                self.board_state.backlighting_level += 25
                if self.board_state.backlighting_level > MAX_BACKLIGHTING_LEVEL:
                    self.board_state.backlighting_level = MAX_BACKLIGHTING_LEVEL
                self.c_set_backlighting_level(self.board_state.backlighting_level)
            else:
                logging.info("Backlighting is already at maximum.")

        elif value == -1:
            if self.board_state.backlighting_level > MIN_BACKLIGHTING_LEVEL:
                self.board_state.backlighting_level += -25
                if self.board_state.backlighting_level < MIN_BACKLIGHTING_LEVEL:
                    self.board_state.backlighting_level = MIN_BACKLIGHTING_LEVEL
                self.c_set_backlighting_level(self.board_state.backlighting_level)
            else:
                logging.info("Backlighting is already at minimum.")
        else:
            raise ValueError(value)

    def shout(self, value: Union[int, float, str], with_ctrl=False):
        if self.shout_method == 'Keyboard':
            shout_to_keyboard(value, with_ctrl)

    def c_board_initialization(self):
        self.handler.queue_command("&init#", "Setting EEPROM init flag.\r")
        time.sleep(1)
        self.close_client()

    def c_ping(self):
        """This could use for something more useful. Like checking at regular interval if the board is still active:
        """
        self.handler.queue_command("a#", "%a:e#")

    def c_get_board_stats(self):
        self.handler.queue_command("b#", "regex_%b.*#")

    def c_get_battery_level(self):
        self.handler.queue_command('&q#', "regex_%q:.*#")

    def c_set_sensor_mode(self, value):
        """ 'length', 'alpha', 'shortcut', 'numeric' """
        self.handler.queue_command(f'&m,{value}#', ['length mode activated\r', 'alpha mode activated\r',
                                             'shortcut mode activated\r', 'numeric mode activated\r'][value])

    def c_set_interface(self, value: int):
        """
        FEED seems to enable box key strokes.
        """
        self.handler.queue_command(f"&fm,{value}#", None)
        if value == 0:
            self.board_state.board_interface = "DCSLinkstream"
            logging.info(f'Interface set to {self.board_state.board_interface}')
        elif value == 1:
            self.board_state.board_interface = "FEED"
            logging.info(f'Interface set to {self.board_state.board_interface}')

    def c_set_backlighting_level(self, value: int):
        if 0 <= value <= MAX_BACKLIGHTING_LEVEL:
            self.handler.queue_command(f'&o,{value}#', None)
            self.board_state.backlighting_level = value
        else:
            logging.warning(f"Backlighting level range: (0, {MAX_BACKLIGHTING_LEVEL})")

    def c_set_backlighting_auto_mode(self, value: int):
        self.handler.queue_command(f"&oa,{value}", None)
        self.board_state.backlighting_auto_mode = {True: 'auto', False: 'manual'}

    def c_set_backlighting_sensitivity(self, value: int):
        if 0 <= value <= MAX_BACKLIGHTING_SENSITIVITY:
            self.handler.queue_command(f"&os,{value}", None)
            self.board_state.backlighting_sensitivity = value
        else:
            logging.warning(f"Backlighting sensitivity range: (0, {MAX_BACKLIGHTING_SENSITIVITY})")

    def c_set_stylus_detection_message(self, value: bool):
        """
        When disabled (false): %t0 %t1 are not sent
        """
        self.handler.queue_command(f'&sn,{int(value)}#', f'%sn:{int(value)}#\r')

    def c_set_stylus_settling_delay(self, value: int = 1):
        if 0 <= value <= MAX_SETTLING_DELAY:
            self.handler.queue_command(f"&di,{value}#", f"%di:{value}#\r")
        else:
            logging.warning(f"Settling delay value range: (0, {MAX_SETTLING_DELAY})")

    def c_set_stylus_max_deviation(self, value: int):
        if 0 <= value <= MAX_MAX_DEVIATION:
            self.handler.queue_command(f"&dm,{value}#", f"%dm:{value}#\r")
        else:
            logging.warning(f"Settling delay value range: (0, {MAX_MAX_DEVIATION})")

    def c_set_stylus_number_of_reading(self, value: int = 5):
        self.handler.queue_command(f"&dn,{value}#", f"%dn:{value}#\r")

    def c_restore_cal_data(self):
        self.handler.queue_command("&cr,m1,m2,raw1,raw2#", None)

    def _clear_cal_data(self):
        self.handler.queue_command("&ca#", None)
        self.calibrated = False

    def c_check_calibration_state(self):  # TODO, to be tested
        self.handler.queue_command('&u#', 'regex_%u:\d#\r')

    def c_set_calibration_points_mm(self, pt: int, pos: int):
        self.handler.queue_command(f'&{pt}mm,{pos}#', f'Cal Pt {pt} set to: {pos}\r')


class Dcs5Handler:
    def __init__(self, controller: Dcs5Controller):
        self.controller = controller

        self.send_queue = Queue()
        self.received_queue = Queue()
        self.expected_message_queue = Queue()

    def clear_queues(self):
        self.send_queue.queue.clear()
        self.received_queue.queue.clear()
        self.expected_message_queue.queue.clear()
        logging.info("Handler Queues Cleared.")

    def processes_queues(self):
        self.clear_queues()
        active_thread_sync_barrier.wait()
        logging.info('Command Handling Started')
        while self.controller.is_listening is True:
            if not self.received_queue.empty():
                self._validate_commands()
            if not self.send_queue.empty():
                self._send_command()
                time.sleep(0.08)
            time.sleep(0.02)
        logging.info('Command Handling Stopped')

    def _validate_commands(self):
        command_is_valid = False
        received = self.received_queue.get()
        expected = self.expected_message_queue.get()
        logging.info(f'Received: {[received]}, Expected: {[expected]}')
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
        logging.info('Command Valid')
        if 'mode activated' in received:
            for i in ["length", "alpha", "shortcut", "numeric"]:
                if i in received:
                    self.controller.board_state.sensor_mode = i

            logging.info(f'{received}')

        elif "sn" in received:
            match = re.findall(f"%sn:(\d)#\r", received)
            if len(match) > 0:
                if match[0] == "1":
                    self.controller.board_state.stylus_status_msg = "enable"
                    logging.info('Stylus Status Message Enable')
                else:
                    self.controller.board_state.stylus_status_msg = "disable"
                    logging.info('Stylus Status Message Disable')

        elif "di" in received:
            match = re.findall(f"%di:(\d)#\r", received)
            if len(match) > 0:
                self.controller.board_state.stylus_settling_delay = int(match[0])
                logging.info(f"Stylus settling delay set to {match[0]}")

        elif "dm" in received:
            match = re.findall(f"%dm:(\d)#\r", received)
            if len(match) > 0:
                self.controller.board_state.stylus_max_deviation = int(match[0])
                logging.info(f"Stylus max deviation set to {int(match[0])}")

        elif "dn" in received:
            match = re.findall(f"%dn:(\d)#\r", received)
            if len(match) > 0:
                self.controller.board_state.number_of_reading = int(match[0])
                logging.info(f"Stylus number set to {int(match[0])}")

        elif "%b" in received:
            match = re.findall("%b:(.*)#", received)
            if len(match) > 0:
                logging.info(f'Board State: {match[0]}')
                self.controller.board_state.board_stats = match[0]

        elif "%q" in received:
            match = re.findall("%q:(-*\d*,\d*)#", received)
            if len(match) > 0:
                logging.info(f'Battery level: {match[0]}')
                self.controller.board_state.battery_level = match[0]

        elif "%u:" in received:
            match = re.findall("%u:(\d)#", received)
            if len(match) > 0:
                if match[0] == '0':
                    logging.info('Board is not calibrated.')
                    self.controller.board_state.calibrated = False
                elif match[0] == '1':
                    logging.info('Board is calibrated.')
                    self.controller.board_state.calibrated = True
            else:
                logging.error(f'Calibration state {self.controller.client.buffer}')

        elif 'Cal Pt' in received:
            logging.info(received.strip("\r") + " mm")
            match = re.findall("Cal Pt (\d) set to: (\d)", received)
            if len(match) > 0:
                self.controller.board_state.__dict__[f'cal_pt_{match[0][0]}'] = int(match[0][1])

    def queue_command(self, command, message=None):
        if message is not None:
            self.expected_message_queue.put(message)
        self.send_queue.put(command)
        logging.info(f'Queuing: Command -> {[command]}, Expected -> {[message]}')

    def _send_command(self):
        command = self.send_queue.get()
        self.controller.client.send(command)
        logging.info(f'Command Sent: {[command]}')


class Dcs5Listener:
    def __init__(self, controller: Dcs5Controller):
        self.controller = controller
        self.message_queue = Queue()
        self.swipe_triggered = False
        self.with_ctrl = False

    def listen(self):
        self.controller.client.clear_all()
        self.message_queue.queue.clear()
        logging.info("Listener Queue and Client Buffers Cleared.")
        active_thread_sync_barrier.wait()
        logging.info('Listener Queue cleared & Client Buffer Clear.')
        logging.info('Listening started')
        while self.controller.is_listening:
            self.controller.client.receive()
            if len(self.controller.client.buffer) > 0:
                self._split_board_message()
                self._process_board_message()
        logging.info('Listening stopped')

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
            logging.info(f'Received Message: {message}')
            shout_value = None
            msg_type, msg_value = self._decode_board_message(message)
            logging.info(f"Message Type: {msg_type}, Message Value: {msg_value}")
            if msg_type == "xt_key":
                if msg_value == 'mode':
                    self.controller.cycle_stylus()
                elif msg_value == 'c1':
                    self.with_ctrl = True
                    logging.info('With Control True.')
                else:
                    shout_value = msg_value

            elif msg_type == 'swipe':
                self.swipe_value = msg_value
                if msg_value > SWIPE_THRESHOLD:
                    self.swipe_triggered = True

            elif msg_type == 'length':
                if self.swipe_triggered is True:
                    self._check_for_stylus_swipe(msg_value)
                else:
                    mapped_msg = self._map_stylus_length_measure(msg_value)
                    if mapped_msg == '1G':
                        self.controller.change_backlighting_level(1)
                    elif mapped_msg == '2G':
                        self.controller.change_backlighting_level(-1)
                    else:
                        shout_value = mapped_msg

            elif msg_type == "unsolicited":
                self.controller.handler.received_queue.put(msg_value)

            if shout_value is not None:
                logging.info(f'output value {shout_value}')
                if not self.controller.is_muted:
                    self.controller.shout(shout_value, with_ctrl=self.with_ctrl)
                    self.with_ctrl = False
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
                return 'xt_key', XT_KEYS_MAP[match[0][3]]
        else:
            return 'unsolicited', value

    def _map_stylus_length_measure(self, value: int):
        if self.controller.board_output_mode == 'center':
            return value - self.controller.stylus_offset
        else:
            index = int((value - BOARD_KEY_ZERO) / BOARD_KEY_RATIO)
            logging.info(f'index {index}')
            if index < BOARD_NUMBER_OF_KEYS:
                return BOARD_KEYS_MAP[self.controller.board_output_mode][index]

    def _check_for_stylus_swipe(self, value: str):
        self.swipe_triggered = False
        if int(value) > 630:
            self.controller.change_board_output_mode('center')
        elif int(value) > 430:
            self.controller.change_board_output_mode('bottom')
        elif int(value) > 230:
            self.controller.change_board_output_mode('top')
        else:
            self.controller.change_board_output_mode('center')
        logging.info(f'Board entry: {self.controller.board_output_mode}.')


if __name__ == "__main__":
    from cli import main
    c=main()
