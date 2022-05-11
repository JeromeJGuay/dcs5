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
import bluetooth
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

SETTINGS = json2dict(resolve_relative_path('src_files/default_settings.json', __file__))

CLIENT_SETTINGS = SETTINGS['client_settings']
DEVICE_NAME = CLIENT_SETTINGS["DEVICE_NAME"]
PORT = CLIENT_SETTINGS["PORT"]
DCS5_ADDRESS = CLIENT_SETTINGS["DCS5_ADDRESS"]

BOARD_SETTINGS = SETTINGS['board_settings']
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

XT_KEY_MAP = {
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

SWIPE_THRESHOLD = 5

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

KEYBOARD_MAP = {
    'space': 'space',  # keyboard.Key.space,
    'enter': 'enter',  # keyboard.Key.enter,
    'del_last': 'backspace',  # keyboard.Key.backspace,
    'del': 'delete',  # keyboard.Key.delete,
    'up': 'up',  # keyboard.Key.up,
    'down': 'down',  # keyboard.Key.down,
    'left': 'left',  # keyboard.Key.left,
    'right': 'right',  # keyboard.Key.right,
    '1B': '-'
}

# STYLUS SETTINGS

STYLUS_OFFSET = {'pen': 6, 'finger': 1}  # mm -> check calibration procedure. TODO
BOARD_KEY_RATIO = 15.385  # ~200/13
BOARD_KEY_DETECTION_RANGE = 2
BOARD_KEY_ZERO = -3.695 - BOARD_KEY_DETECTION_RANGE
BOARD_NUMBER_OF_KEYS = 49


def shout_to_keyboard(value: str):
    if value in KEYBOARD_MAP:
        pag.press(KEYBOARD_MAP[value])
    elif isinstance(value, (int, float)):
        pag.write(str(value))
    elif value in ['f1', 'f2', 'f3', 'f4', 'f5', 'f6']:
        pag.press(value)
    elif str(value) in '.0123456789abcdefghijklmnopqrstuvwxyz':
        pag.write(value)


def scan_bluetooth_device():
    devices = {}
    logging.info("Scanning for bluetooth devices ...")
    _devices = bluetooth.discover_devices(lookup_names=True, lookup_class=True)
    number_of_devices = len(_devices)
    logging.info(f"{number_of_devices} devices found")
    for addr, name, device_class in _devices:
        devices[name] = {'address': addr, 'class': device_class}
        logging.info(f"Devices Name: {name}")
        logging.info(f"Devices MAC Address: {addr}")
        logging.info(f"Devices Class: {device_class}\n")
    return devices


def search_for_dcs5board() -> str:
    devices = scan_bluetooth_device()
    if DEVICE_NAME in devices:
        logging.info(f'{DEVICE_NAME}, found.')
        return devices[DEVICE_NAME]['address']
    else:
        logging.info(f'{DEVICE_NAME}, not found.')
        return None


class Dcs5Client:
    """
    Notes
    -----
    Both socket and bluetooth methods(socket package) seems to be equivalent.
    """

    def __init__(self):
        self.dcs5_address: str = None
        self.port: int = None
        self.buffer: str = ''
        self.socket = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)
        self.default_timeout = .05
        self.socket.settimeout(self.default_timeout)

    def connect(self, address: str, port: int):
        self.dcs5_address = address
        self.port = port
        self.socket.connect((self.dcs5_address, self.port))

    def send(self, command: str):
        self.socket.send(command.encode(BOARD_MSG_ENCODING))

    def receive(self):
        try:
            self.buffer += self.socket.recv(BUFFER_SIZE).decode(BOARD_MSG_ENCODING)
        except socket.timeout:
            pass

    def clear_all(self):
        self.receive()
        self.buffer = ""

    def close(self):
        self.socket.close()


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


def interrupt_listening(method):
    def inner(self):
        current_sate = self.listening
        self.stop_listening()
        method(self)
        if current_sate is True:
            self.start_listening()
    return inner


class Dcs5Controller:
    """
    Notes
    -----
    Firmware update command could be added:
        %h,VER,BR#
        see documentations

    TODO
    QUEUES SHOULD AUTO CLEAR AFTER SOME DELAYS
    """

    def __init__(self, shout_method='Keyboard'):
        Dcs5BoardState.__init__(self)
        threading.Thread.__init__(self)

        self.board_state = Dcs5BoardState()

        self.listen_thread: threading.Thread = None
        self.command_thread: threading.Thread = None
        self.battery_thread: threading.Thread = None
        self.idle_check_thread: threading.Thread = None

        self.client = Dcs5Client()
        self.client_isconnected = False

        self.send_queue = Queue()
        self.received_queue = Queue()
        self.expected_message_queue = Queue()

        self.listening = False
        self.is_muted = False

        self.stylus: str = 'pen'  # [finger/pen]
        self.stylus_offset: str = STYLUS_OFFSET['pen']
        # {'measure': None, 'typing': None}
        self.stylus_modes_settling_delay: Dict[str: int] = DEFAULT_SETTLING_DELAY
        self.stylus_modes_number_of_reading: Dict[str: int] = DEFAULT_NUMBER_OF_READING
        self.stylus_modes_max_deviation: Dict[str: int] = DEFAULT_MAX_DEVIATION

        self.shout_method = shout_method
        self.board_output_mode = 'center'
        self.swipe_triggered = False

    def start_client(self, address: str = None, port: int = None):
        logging.info(f'Attempting to connect to board via port {port}.')
        try:
            logging.info('Trying to connect for 30 s.')
            self.client.socket.settimeout(30)
            self.client.connect(address, port)
            self.client_isconnected = True
            logging.info('Connection Successful.\n')
        except socket.timeout:
            logging.info('Socket.timeout, could not connect. Time Out')
        except OSError as err:
            logging.error('Start_Client, OSError: '+str(err))
        self.client.socket.settimeout(self.client.default_timeout)

    def close_client(self):
        if self.listening is True:
            self.stop_listening()
        self.client.close()
        logging.info('Client Closed.')

    def start_listening(self, clear_queues=False):
        if self.listening is False:
            self.client.clear_all()
            if clear_queues is True:
                self._clear_queues()

            logging.info('starting threads')
            self.listening = True
            self.command_thread = threading.Thread(target=self._handle_commands)
            self.listen_thread = threading.Thread(target=Dcs5Listener(self).listen)
            self.command_thread.start()
            self.listen_thread.start()

        logging.log('Board is Active')

    def stop_listening(self):
        if self.listening is True:
            self.listening = False
            self._join_active_threads()
        logging.info('Board is not Active.')

    def _clear_queues(self):
        self.send_queue.queue.clear()
        self.received_queue.queue.clear()
        self.expected_message_queue.queue.clear()
        logging.info("Controller Queues cleared")

    def _join_active_threads(self):
        """Join the listen and command thread."""
        self.listen_thread.join()
        self.command_thread.join()
        logging.info("Controller Queues joined.")

    def unmute_board(self):
        """Unmute board shout output"""
        if self.is_muted is True:
            self.is_muted = False
            logging.info('Board unmuted')

    def mute_board(self):
        """Mute board shout output"""
        if self.is_muted is False:
            self.is_muted = True
            logging.info('Board muted')

    @interrupt_listening
    def sync_controller_and_board(self):
        """Init board to default settings.
        TODO have the default settings comme from an attributes. Json file maybe
        """
        logging.info('Syncing Controller and Board.')
        self.start_listening(clear_queues=True)

        self.c_set_interface(1)
        self.c_set_sensor_mode(0)
        self.c_set_backlighting_level(DEFAULT_BACKLIGHTING_LEVEL)
        self.c_set_stylus_detection_message(False)
        self.c_set_stylus_settling_delay(DEFAULT_SETTLING_DELAY['measure'])
        self.c_set_stylus_max_deviation(DEFAULT_MAX_DEVIATION['measure'])
        self.c_set_stylus_number_of_reading(DEFAULT_NUMBER_OF_READING['measure'])
        self.c_get_board_stats()
        self.c_get_battery_level()
        self.c_check_calibration_state()

        if (self.board_state.sensor_mode == "length" and
            self.board_state.stylus_status_msg == "disable" and
            self.board_state.stylus_settling_delay == DEFAULT_SETTLING_DELAY["measure"] and
            self.board_state.stylus_max_deviation == DEFAULT_MAX_DEVIATION["measure"] and
            self.board_state.number_of_reading == DEFAULT_NUMBER_OF_READING["measure"]
        ):
            logging.info("Syncing failed.")
            return "failed"
        else:
            logging.info("Syncing successful.")
            return ""

    @interrupt_listening
    def calibrate(self, pt: int):

        logging.info("Calibration Mode Enable.")
        self.client.clear_all()

        self.client.send(f"&{pt}r#")
        self.client.socket.settimeout(5)
        self.client.receive()

        if f'&Xr#: X={pt}\r' in self.client.buffer:
            pt_value = self.board_state.__dict__[f"cal_pt_{[pt]}"]
            logging.info(f"Calibration for point {pt}. Set stylus down at {pt_value} mm ...")
            msg = ""
            while f'&{pt}c' not in msg:
                self.client.receive()
                msg += self.client.buffer  # FIXME
            logging.info(f'Point {pt} calibrated.')

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
        self.c_set_stylus_settling_delay(self.stylus_modes_settling_delay[mode])
        self.c_set_stylus_number_of_reading(self.stylus_modes_number_of_reading[mode])
        self.c_set_stylus_max_deviation(self.stylus_modes_max_deviation[mode])

    def map_stylus_length_measure(self, value: int):
        if self.board_output_mode == 'center':
            return value - self.stylus_offset
        else:
            index = int((value - BOARD_KEY_ZERO) / BOARD_KEY_RATIO)
            logging.info(f'index {index}')
            if index < BOARD_NUMBER_OF_KEYS:
                return BOARD_KEYS_MAP[self.board_output_mode][index]

    def check_for_stylus_swipe(self, value: str):
        self.swipe_triggered = False
        if int(value) > 630:
            self.change_board_output_mode('center')
        elif int(value) > 430:
            self.change_board_output_mode('bottom')
        elif int(value) > 230:
            self.change_board_output_mode('top')
        logging.info(f'Board entry: {self.board_output_mode}.')

    def shout(self, value: Union[int, float, str]):
        if self.shout_method == 'Keyboard':
            shout_to_keyboard(value)

    def change_backlighting_level(self, value: int):
        if value == 1 and self.board_state.backlighting_level < MAX_BACKLIGHTING_LEVEL:
            self.board_state.backlighting_level += 25
            if self.board_state.backlighting_level > MAX_BACKLIGHTING_LEVEL:
                self.board_state.backlighting_level = MAX_BACKLIGHTING_LEVEL
            self.c_set_backlighting_level(self.board_state.backlighting_level)

        if value == -1 and self.board_state.backlighting_level > MIN_BACKLIGHTING_LEVEL:
            self.board_state.backlighting_level += -25
            if self.board_state.backlighting_level < MIN_BACKLIGHTING_LEVEL:
                self.board_state.backlighting_level = MIN_BACKLIGHTING_LEVEL
            self.c_set_backlighting_level(self.board_state.backlighting_level)

    def _handle_commands(self):
        logging.info('Command Handler Initiated')
        while self.listening is True:
            if not self.received_queue.empty():
                isvalid = False
                received = self.received_queue.get()
                expected = self.expected_message_queue.get()
                logging.info(f'Received: {[received]}, Expected: {[expected]}')

                if "regex_" in expected:
                    match = re.findall("(" + expected[6:] + ")", received)[0]
                    if len(match) > 0:
                        isvalid = True
                        logging.info(f'Match {match}') # TODO REMOVE

                elif received == expected:
                    isvalid = True

                if isvalid is True:
                    logging.info('Command Valid')
                    if 'mode activated' in received:
                        for i in ["length", "alpha", "shortcut", "numeric"]:
                            if i in received:
                                self.board_state.sensor_mode = i
                                break
                        logging.info(f'{received}')

                    elif "sn" in received:
                        match = re.findall(f"%sn:(\d)#\r", received)[0]
                        if len(match) > 0:
                            if match == "1":
                                self.board_state.stylus_status_msg = "enable"
                                logging.info('Stylus Status Message Enable')
                            else:
                                self.board_state.stylus_status_msg = "disable"
                                logging.info('Stylus Status Message Disable')

                    elif "di" in received:
                        match = re.findall(f"%di:(\d)#\r", received)[0]
                        if len(match) > 0:
                            self.board_state.stylus_settling_delay = int(match)
                            logging.info(f"Stylus settling delay set to {match}")

                    elif "dm" in received:
                        match = re.findall(f"%dm:(\d)#\r", received)[0]
                        if len(match) > 0:
                            self.board_state.stylus_max_deviation = int(match)
                            logging.info(f"Stylus max deviation set to {int(match)}")

                    elif "dn" in received:
                        match = re.findall(f"%dn:(\d)#\r", received)[0]
                        if len(match) > 0:
                            self.board_state.number_of_reading = int(match)
                            logging.info(f"Stylus number set to {int(match)}")

                    elif "%b" in received:
                        match = re.findall("%b:(.*)#", received)[0]
                        if len(match)>0:
                            logging.info(f'Board State: {match}')
                            self.board_state.board_stats = match

                    elif "%q" in received:
                        match = re.findall("%q:(-*\d*,\d*)#", received)[0]
                        if len(match) > 0:
                            logging.info(f'Battery level: {match}')
                            self.board_state.battery_level = match

                    elif "%u:" in received:
                        match = re.findall("%u:(\d)#", received)[0]
                        if len(match) > 0:
                            if match == '0':
                                logging.info('Board is not calibrated.')
                                self.board_state.calibrated = False
                            elif match == '1':
                                logging.info('Board is calibrated.')
                                self.board_state.calibrated = True
                        else:
                            logging.error(f'Calibration state {self.client.buffer}')

                    elif 'Cal Pt' in received:
                        logging.info(received.strip("\r")+" mm")
                        match = re.findall("Cal Pt (\d) set to: (\d)", received)[0]
                        if len(match) > 0:
                            self.board_state.__dict__[f'cal_pt_{match[0]}'] = int(match[1])
                else:
                    logging.error(f'Invalid: Command received: {[received]}, Command expected: {[expected]}')

                self.received_queue.task_done()
                self.expected_message_queue.task_done()

            if not self.send_queue.empty():
                self._send_command()
            time.sleep(0.1)

    def _queue_command(self, command, message=None):
        logging.info(f'Queued: {[command]}, {[message]}')
        if message is not None:
            self.expected_message_queue.put(message)
        self.send_queue.put(command)

    def _send_command(self):
        command = self.send_queue.get()
        print(command)
        self.client.send(command)
        self.send_queue.task_done()

    def c_board_initialization(self):
        self._queue_command("&init#", "Setting EEPROM init flag.\r")

    def c_reboot(self):  # FIXME NOT WORKING
        self._queue_command("&rr#", "%rebooting")

    def c_ping(self):
        """This could use for something more useful. Like checking at regular interval if the board is still active:
        """
        self._queue_command("a#", "%a:e#")

    def c_get_board_stats(self):
        self._queue_command("b#", "regex_%b.*#")

    def c_get_battery_level(self):
        self._queue_command('&q#', "regex_%q:.*#")

    def c_set_sensor_mode(self, value):
        """ 'length', 'alpha', 'shortcut', 'numeric' """
        self._queue_command(f'&m,{value}#', ['length mode activated\r', 'alpha mode activated\r',
                                            'shortcut mode activated\r', 'numeric mode activated\r'][value])

    def c_set_interface(self, value: int):
        """
        FEED seems to enable box key strokes.
        """
        self._queue_command(f"&fm,{value}#", None)
        if value == 0:
            self.board_state.board_interface = "DCSLinkstream"
            logging.log(f'Interface set to {self.board_state.board_interface}')
        elif value == 1:
            self.board_state.board_interface = "FEED"
            logging.log(f'Interface set to {self.board_state.board_interface}')

    def c_set_backlighting_level(self, value: int):
        if 0 <= value <= MAX_BACKLIGHTING_LEVEL:
            self._queue_command(f'&o,{value}#', None)
            self.board_state.backlighting_level = value
        else:
            logging.warning(f"Backlighting level range: (0, {MAX_BACKLIGHTING_LEVEL})")

    def c_set_backlighting_auto_mode(self, value: int):
        self._queue_command(f"&oa,{value}", None)
        self.board_state.backlighting_auto_mode = {True: 'auto', False: 'manual'}

    def c_set_backlighting_sensitivity(self, value: int):
        if 0 <= value <= MAX_BACKLIGHTING_SENSITIVITY:
            self._queue_command(f"&os,{value}", None)
            self.board_state.backlighting_sensitivity = value
        else:
            logging.warning(f"Backlighting sensitivity range: (0, {MAX_BACKLIGHTING_SENSITIVITY})")

    def c_set_stylus_detection_message(self, value: bool):
        """
        When disabled (false): %t0 %t1 are not sent
        """
        self._queue_command(f'&sn,{int(value)}', f'%sn:{int(value)}#\r')

    def c_set_stylus_settling_delay(self, value: int = 1):
        if 0 <= value <= MAX_SETTLING_DELAY:
            self._queue_command(f"&di,{value}#", f"%di:{value}#\r")
        else:
            logging.warning(f"Settling delay value range: (0, {MAX_SETTLING_DELAY})")

    def c_set_stylus_max_deviation(self, value: int):
        if 0 <= value <= MAX_MAX_DEVIATION:
            self._queue_command(f"&dm,{value}#", f"%dm:{value}#\r")
        else:
            logging.warning(f"Settling delay value range: (0, {MAX_MAX_DEVIATION})")

    def c_set_stylus_number_of_reading(self, value: int = 5):
        self._queue_command(f"&dn,{value}#", f"%dn:{value}#\r")

    def c_restore_cal_data(self):
        self._queue_command("&cr,m1,m2,raw1,raw2#", None)

    def _clear_cal_data(self):
        self._queue_command("&ca#", None)
        self.calibrated = False

    def c_check_calibration_state(self):  # TODO, to be tested
        self._queue_command('&u#', 'regex_%u:\d#\r')

    def c_set_calibration_points_mm(self, pt: int, pos: int):
        self._queue_command(f'&{pt}mm,{pos}#', f'Cal Pt {pt} set to: {pos}\r')


class Dcs5Listener:
    """
    """

    def __init__(self, controller: Dcs5Controller):
        self.controller = controller
        self.message_queue = Queue()

        self.stdout_value: str = None

    def listen(self):
        logging.info('Listening started')
        self.controller.client.receive()
        while self.controller.listening is True:
            self.controller.client.receive()
            if len(self.controller.client.buffer) > 0:
                self.split_board_message()
                self.process_board_message()
                self.controller.idle_timer.start()
        logging.info('Listening stopped')

    def split_board_message(self):
        delimiters = ["\n", "\r", "#", "%rebooting", "Rebooting in 2 seconds ..."]
        for d in delimiters:
            msg = self.controller.client.buffer.split(d)
            if len(msg) > 1:
                self.controller.client.buffer = msg[-1]
                self.message_queue.put(msg[0] + d)

    def process_board_message(self):
        """ANALYZE SOLICITED VS UNSOLICITED MESSAGE"""
        while not self.message_queue.empty():
            message = self.message_queue.get()
            stdout_value = None
            msg_type, msg_value = self.decode_board_message(message)
            if msg_type == "xt_key":
                if msg_value in ['a1', 'a2', 'a3', 'a4', 'a5', 'a6']:
                    stdout_value = f'f{msg_value[-1]}'
                elif msg_value in ['b1', 'b2', 'b3', 'b4', 'b5', 'b6']:
                    if msg_value == 'b1':
                        self.controller.change_backlighting_level(1)
                    elif msg_value == 'b2':
                        self.controller.change_backlighting_level(-1)
                    else:
                        logging.info(f'{msg_value} not mapped.')
                elif msg_value == 'mode':
                    self.controller.cycle_stylus()
                elif msg_value == 'skip':
                    stdout_value = 'space'
                elif msg_value in ['c1']:
                    logging.info(f'{msg_value} not mapped.')
                else:
                    stdout_value = msg_value

            elif msg_type == 'swipe':
                self.controller.swipe_value = msg_value
                if msg_value > SWIPE_THRESHOLD:
                    self.controller.swipe_triggered = True

            elif msg_type == 'length':
                if self.controller.swipe_triggered is True:
                    self.controller.check_for_stylus_swipe(msg_value)
                else:
                    stdout_value = self.controller.map_stylus_length_measure(msg_value)

            elif msg_type == "unsolicited":
                self.controller.received_queue.put(msg_value)

            self.message_queue.task_done()
            if stdout_value is not None:
                logging.info(f'output value {stdout_value}')
                if self.controller.is_muted is False:
                    shout_to_keyboard(stdout_value)
            time.sleep(0.001)

    @staticmethod
    def decode_board_message(value: str):
        pattern = "%t,([0-9])#|%l,([0-9]*)#|%s,([0-9]*)#|F,([0-9]{2})#"
        match = re.findall(pattern, value)
        if len(match) > 0:
            if match[0][1] != "":
                return 'length', int(match[0][1])
            elif match[0][2] != "":
                return 'swipe', int(match[0][2])
            elif match[0][3] != "":
                return 'xt_key', XT_KEY_MAP[match[0][3]]
        else:
            return 'unsolicited', value


def launch_dcs5_board(port=PORT, address=DCS5_ADDRESS, scan=False):
    _address = search_for_dcs5board() if scan is True else address
    controller = Dcs5Controller()
    controller.start_client(_address, port)
    if controller.client_isconnected is True:
        controller.start_listening()
        controller.sync_controller_and_board()
    return controller


def main(scan: bool = False):
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-v",
        "--verbose",
        default="info",
        help="Provide logging level: [debug, info, warning, error, critical]",
    )
    parser.add_argument(
        "-log",
        "--logfile",
        default='logs/dcs5_log',
        help=("Filename to print the logs to."),
    )
    args = parser.parse_args()

    log_path = str(resolve_relative_path(args.logfile, __file__))

    log_path += "_" + time.strftime("%y%m%dT%H%M%S", time.gmtime()) + ".log"

    logging.basicConfig(
        level=args.verbose.upper(),
        format="%(asctime)s {%(threadName)s} [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(log_path),
            logging.StreamHandler()
        ]
    )
    logging.info('Starting')

    c = launch_dcs5_board(scan=scan)

    return c


if __name__ == "__main__":
#    try:
    c=main(scan=False)
#        while True:
#            pass
#    except (KeyboardInterrupt, SystemExit):
#        pass
#    finally:
#        c.close_client()


""" POssible error
ESError
"""

