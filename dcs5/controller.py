"""
Author : JeromeJGuay
Date : May 2022

wine /home/jeromejguay/.wine/drive_c/users/jeromejguay/AppData/Local/Programs/Python/Python38/Script/pyinstaller.exe --onefile dcs5/gui.py

This module contains the Class relative to the DCS5_XT Board Controller and Client.

Valid Board Commands for key mapping : 'BACKLIGHT_UP', 'BACKLIGHT_DOWN', 'CHANGE_STYLUS', 'UNITS_mm', 'UNITS_cm'

Notes
-----
 The code is written for a stylus calibration.
    Calibration should probably be done with the Finger Stylus and not the Pen Stylus
    since the magnet is further away in the pen (~5mm). If this is the case, the code should be changed.


References
----------
    https://bigfinllc.com/wp-content/uploads/Big-Fin-Scientific-Fish-Board-Integration-Guide-V2_0.pdf?fbclid=IwAR0tJMwvN7jkqxgEhRQABS0W3HLLntpOflg12bMEwM5YrDOwcHStznJJNQM


# MAKE THE CALIBRATION FILE EDITABLE (.dcs5board.conf)

"""
import argparse
import logging
import socket
import threading
import re
from typing import *
import time
import pyautogui as pag

from utils import json2dict, resolve_relative_path
from dataclasses import dataclass
from queue import Queue


BOARD_MSG_ENCODING = 'UTF-8'
BUFFER_SIZE = 1024

active_thread_sync_barrier = threading.Barrier(2)

### Turn this into a data class ?
SETTINGS = json2dict(resolve_relative_path('src_files/default_settings.json', __file__))



##### CLIENT SETTING ##### | BUILT IN COPY
CLIENT_SETTINGS = SETTINGS['bluetooth']
DEVICE_NAME = CLIENT_SETTINGS["DEVICE_NAME"]
PORT = CLIENT_SETTINGS["PORT"]
DCS5_ADDRESS = CLIENT_SETTINGS["MAC_ADDRESS"]

##### App Config ##### FIXME where to put this with general config
SWIPE_THRESHOLD = 5
READING_SETTINGS = {'top': 'key', 'middle': 'length', 'bottom': 'key'}


##### SOFTWARE DEFAULT SETTINGS ##### | BUILT INT COPY ----HALF-READY----
# Make a reading profile.
# then a map from middle, top , bottom to profile
BOARD_SETTINGS = SETTINGS['board']
DEFAULT_SETTLING_DELAY = {'length': BOARD_SETTINGS['DEFAULT_SETTLING_DELAY'],
                          'key': BOARD_SETTINGS['DEFAULT_SETTLING_DELAY']}
DEFAULT_MAX_DEVIATION = {'length': BOARD_SETTINGS['DEFAULT_MAX_DEVIATION'],
                         'key': BOARD_SETTINGS['DEFAULT_SETTLING_DELAY']}
DEFAULT_NUMBER_OF_READING = {'length': BOARD_SETTINGS['DEFAULT_NUMBER_OF_READING'],
                             'key': BOARD_SETTINGS['DEFAULT_SETTLING_DELAY']}

DEFAULT_BACKLIGHTING_LEVEL = BOARD_SETTINGS['DEFAULT_BACKLIGHTING_LEVEL']
DEFAULT_BACKLIGHTING_AUTO_MODE = BOARD_SETTINGS['DEFAULT_BACKLIGHTING_AUTO_MODE']
DEFAULT_BACKLIGHTING_SENSITIVITY = BOARD_SETTINGS['DEFAULT_BACKLIGHTING_SENSITIVITY']

##### HARDWARE PARAMETERS ##### | BUILT IN COPY
MAX_SETTLING_DELAY = BOARD_SETTINGS['MAX_SETTLING_DELAY']
MAX_MAX_DEVIATION = BOARD_SETTINGS['MAX_MAX_DEVIATION']
MIN_BACKLIGHTING_LEVEL = BOARD_SETTINGS['MIN_BACKLIGHTING_LEVEL']
MAX_BACKLIGHTING_LEVEL = BOARD_SETTINGS['MAX_BACKLIGHTING_LEVEL']
MIN_BACKLIGHTING_SENSITIVITY = BOARD_SETTINGS['MIN_BACKLIGHTING_SENSITIVITY']
MAX_BACKLIGHTING_SENSITIVITY = BOARD_SETTINGS['MAX_BACKLIGHTING_SENSITIVITY']


STYLUS_OFFSET = {'pen': 6, 'finger': 1}  # mm -> check calibration procedure.----HALF-READY----

##### DECAL SPECIFICATION json ##### | BUILT IN COPY ----READY----
DECAL_KEY_DETECTION_RANGE = 2
DECAL_KEY_RATIO = 15.385  # ~200/13
DECAL_KEY_ZERO = -3.695
DECAL_KEY_DETECTION_ZERO = DECAL_KEY_ZERO - DECAL_KEY_DETECTION_RANGE
DECAL_NUMBER_OF_KEYS = 49

#DECALS_LAYOUT | BUILT INT COPY
DECAL_KEYS_LAYOUT = { # config
    'top': 7 * ['left_space'] + \
           list('abcdefghijklmnopqrstuvwxyz') + \
           [f'{i + 1}B' for i in range(8)] + \
           6 * ['right_space'] + 2 * ['del_last'],
    'bottom': 7 * ['left_space'] + \
              list('01234.56789') + \
              ['view', 'batch', 'tab', 'histo', 'summary', 'dismiss', 'fish', 'sample',
               'sex', 'size', 'light_bulb', 'scale', 'location', 'pit_pwr', 'settings'] + \
              [f'{i + 1}G' for i in range(8)] + \
              6 * ['right_space'] + 2 * ['del_last']}

#seperate file json config | BUILT IN COPY
XT_KEYS_NAME_MAP = {
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

##### mapable keys ##### json | BUIL INT COPY
MAPPABLE_KEYS = [
    'a1', 'a2', 'a3', 'a4', 'a5', 'a6', 'b1', 'b2', 'b3', 'b4', 'b5', 'b6', 'c1',
    'skip', 'enter', 'del_last', 'del', 'up', 'down', 'left', 'right', 'mode',
    'left_space', 'view', 'batch', 'tab', 'histo', 'summary', 'dismiss', 'fish', 'sample',
    'sex', 'size', 'light_bulb', 'scale', 'location', 'pit_pwr', 'settings',
    '1B', '2B', '3B', '4B', '5B', '6B', '7B', '8B',
    '1G', '2G', '3G', '4G', '5G', '6G', '7G', '8G', 'right_space'
]

##### Key map json##### | BUILT IN COPY  ----READY----
VALID_COMMANDS = ["BACKLIGHT_UP", "BACKLIGHT_DOWN", "CHANGE_STYLUS", "UNITS_mm", "UNITS_cm"]
KEYS_MAP = {
    'a1': 'escape',
    'a2': 'f1',
    'a3': 'f2',
    'a4': 'f3',
    'a5': 'f4',
    'a6': 'f5',
    'b1': 'f8',
    'b2': 'f9',
    'b3': 'f10',
    'b4': '11',
    'b5': ['Y', 'enter'],
    'b6': 'backspace',
    'c1': 'ctrl',
    'skip': 'pagedown',
    'enter': 'enter',
    'del': 'delete',
    'up': 'up',
    'down': 'down',
    'left': 'left',
    'right': 'right',
    'mode': 'CHANGE_STYLUS',
    'view': None,
    'batch': None,
    'tab': None,
    'histo': None,
    'summary': None,
    'dismiss': None,
    'fish': None,
    'sample': None,
    'sex': None,
    'size': None,
    'light_bulb': None,
    'scale': None,
    'location': None,
    'pit_pwr': None,
    'settings': None,
    '1B': '-',
    '2B': '(',
    '3B': ')',
    '4B': None,
    '5B': None,
    '6B': None,
    '7B': 'alt',
    '8B': 'shift',
    '1G': 'BACKLIGHT_DOWN',
    '2G': 'BACKLIGHT_UP',
    '3G': None,
    '4G': None,
    '5G': None,
    '6G': None,
    '7G': 'UNITS_mm',
    '8G': 'UNITS_cm',
    'left_space_1': 'space',
    'left_space_2': 'space',
    'left_space_3': 'space',
    'left_space_4': 'space',
    'left_space_5': 'space',
    'left_space_6': 'space',
    'left_space_7': 'space',
    'right_space_1': 'space',
    'right_space_2': 'space',
    'right_space_3': 'space',
    'right_space_4': 'space',
    'right_space_5': 'space',
    'right_space_6': 'space',
    'del_last_1': 'backspace',
    'del_last_2': 'backspace',
}


class KeyMap:
    def __init__(self):
        self.map: dict = None

    def load_map(self, key_map: Dict[str, str]):
        for key, value in key_map.items():
            if key in MAPPABLE_KEYS and value is not None:
                if pag.isValidKey(value) or value in VALID_COMMANDS:
                    self.map[key] = value
                else:
                    logging.warning(f'{key} -> {value}. {value} is not a valid command.')
            else:
                logging.warning(f'{key} -> {value}. {key} is not a valid or mappable board key name.')


class DecalSpecifications:
    def __init__(self, number_of_keys: int, key_to_mm_ratio: float, key_zero: float, detection_range: float):
        """
        x = a*k + b
        x = length in millimeter
        k = length in key scale (where k = 1 at the leftmost point of the  key circle).
        a = ratio between n*keys and m*1 millimeters.

        keys_ratio : a
        keys_zero : b
        """
        self.number_of_keys = number_of_keys
        self.key_to_mm_ratio = key_to_mm_ratio
        self.key_zero = key_zero
        self.detection_range = detection_range
        self.relative_key_zero = None
        self._compute_relative_key_zero()

    def _compute_relative_key_zero(self):
        self.relative_key_zero = self.key_zero - self.detection_range


# one object ot hold current reading settings and other to hold custom settings
class ReadingProfile:
    def __init__(self, settling_delay: int, number_of_reading: int, max_deviation: int):
        self.settling_delay = settling_delay
        self.number_of_reading = number_of_reading
        self.max_deviation = max_deviation


@dataclass(unsafe_hash=True, init=True)
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
        self._with_control = False
        self._with_shift = False
        self._with_alt = False

        self.combo = []

    def shout_to_keyboard(self, value: str):
        if value == 'ctrl':
            self._with_control = not self._with_control
        elif value == 'shift':
            self._with_shift = not self._with_shift
        elif value == 'alt':
            self._with_alt = not self._with_alt
        else:
            self._shout_to_keyboard(value)

    def _shout_to_keyboard(self, value):
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
            logging.info(f"Keyboard out: {'+'.join(self.combo)} {value}")
            if self.is_valid_key(value):
                pag.press(value)
            else:
                pag.write(str(value))
            self.combo = []

    @staticmethod
    def is_valid_key(value):
        if isinstance(value, list):
            return all(map(pag.isValidKey, value))
        else:
            return pag.isValidKey(value)


class BtClient:
    """
    Notes
    -----
    Both socket and bluetooth methods(socket package) seems to be equivalent.
    """

    def __init__(self):
        self._mac_address: str = None
        self._buffer: str = ''
        self.socket: socket.socket = None
        self.default_timeout = .5

    def connect(self, address: str = None, timeout: int = None):
        self.socket = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)
        self.socket.settimeout(timeout if timeout is not None else self.default_timeout)

        self._mac_address = address if address is not None else self._mac_address
        while True: # TODO test me
            for port in range(65535):  # check for all available ports
                try:
                    self.socket.connect((self._mac_address, port))
                    break
                except (PermissionError, OSError):
                    pass
            logging.error('No available ports were found.')
            break
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
        """Appends at the beginning of the buffer."""
        self._buffer = msg + self._buffer

    def close(self):
        self.socket.close()


class Dcs5Controller:
    """
    Notes
    -----
    Firmware update command could be added:
        %h,VER,BR#
        see documentations
    """

    def __init__(self, dynamic_stylus_settings=False, length_units="mm"):
        """

        Parameters
        ----------
        dynamic_stylus_settings : [True, False]
        length_units : ['cm', 'mm']
        """
        #threading.Thread.__init__(self) Probably not necessary
        self.listen_thread: threading.Thread = None
        self.command_thread: threading.Thread = None

        self.internal_board_state = InternalBoardState() # BoardCurrentState
        # self.board_settings = Dcs5BoardSettings()
        # self.key_out_map = Dcs5KeyOutMap()
        # self.stylus_spec = StylusSpecs()
        # self.decal_map = DecalMap()

        self.socket_listener = SocketListener(self)
        self.command_handler = CommandHandler(self)
        self.is_listening = False
        self.is_muted = False

        self.is_sync = False
        self.ping_event_check = threading.Event()

        self.client = BtClient()
        self.client_isconnected = False

        self.stylus_type: str = 'pen'  # [finger/pen]
        self.stylus_offset: str = STYLUS_OFFSET['pen']

        #Reading settings
        self.stylus_modes_settling_delay: Dict[str: int] = DEFAULT_SETTLING_DELAY
        self.stylus_modes_number_of_reading: Dict[str: int] = DEFAULT_NUMBER_OF_READING
        self.stylus_modes_max_deviation: Dict[str: int] = DEFAULT_MAX_DEVIATION

        self.shouter = Shouter()
        self.dynamic_stylus_settings = dynamic_stylus_settings
        self.board_output_zone = 'middle'
        self.length_units = length_units

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
        self.c_set_stylus_settling_delay(DEFAULT_SETTLING_DELAY['length'])
        self.c_set_stylus_max_deviation(DEFAULT_MAX_DEVIATION['length'])
        self.c_set_stylus_number_of_reading(DEFAULT_NUMBER_OF_READING['length'])
        self.c_check_calibration_state()

        self.wait_for_ping()

        if not was_listening:
            self.stop_listening()

        if (self.internal_board_state.sensor_mode == "length" and
            self.internal_board_state.stylus_status_msg == "disable" and
            self.internal_board_state.stylus_settling_delay == DEFAULT_SETTLING_DELAY["length"] and
            self.internal_board_state.stylus_max_deviation == DEFAULT_MAX_DEVIATION["length"] and
            self.internal_board_state.number_of_reading == DEFAULT_NUMBER_OF_READING["length"]
        ):
            self.is_sync = True
            logging.info("Syncing successful.")
        else:
            logging.info("Syncing  failed.")
            self.is_sync = False

    def wait_for_ping(self, timeout=2):
        self.c_ping()
        self.ping_event_check.set()
        logging.info('Ping Event Set.')
        count = 0
        while self.ping_event_check.is_set():
            if count > timeout/0.2:
                logging.info('Ping Event Not Received')
                self.ping_event_check.clear()
                break
            count += 1
            time.sleep(0.2)

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
                pt_value = self.internal_board_state.__dict__[f"cal_pt_{pt}"]
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

    def change_length_units(self, value: str):
        if value in ['cm', 'mm']:
            self.length_units = value
            logging.info(f"Length Units Change to {self.length_units}")
        else:
            logging.error("Length Units are either 'mm' or 'cm'.")

    def change_stylus(self, value: str):
        """Stylus must be one of [pen, finger]"""
        self.stylus_type = value
        self.stylus_offset = STYLUS_OFFSET[self.stylus_type]
        logging.info(f'Stylus set to {self.stylus_type}. Stylus offset {self.stylus_offset}')

    def cycle_stylus(self):
        if self.stylus_type == 'pen':
            self.change_stylus('finger')
        else:
            self.change_stylus('pen')

    def change_board_output_zone(self, value: str):
        """
        value must be one of  [middle, bottom, top]
        """
        self.board_output_zone = value
        mode = {'middle': 'length', 'bottom': 'key', 'top': 'key'}[value]
        if self.dynamic_stylus_settings is True:
            self.c_set_stylus_settling_delay(self.stylus_modes_settling_delay[mode])
            self.c_set_stylus_number_of_reading(self.stylus_modes_number_of_reading[mode])
            self.c_set_stylus_max_deviation(self.stylus_modes_max_deviation[mode])

    def backlight_up(self):
        if self.internal_board_state.backlighting_level < MAX_BACKLIGHTING_LEVEL:
            self.internal_board_state.backlighting_level += 25
            if self.internal_board_state.backlighting_level > MAX_BACKLIGHTING_LEVEL:
                self.internal_board_state.backlighting_level = MAX_BACKLIGHTING_LEVEL
            self.c_set_backlighting_level(self.internal_board_state.backlighting_level)
        else:
            logging.info("Backlighting is already at maximum.")

    def backlight_down(self):
        if self.internal_board_state.backlighting_level > MIN_BACKLIGHTING_LEVEL:
            self.internal_board_state.backlighting_level += -25
            if self.internal_board_state.backlighting_level < MIN_BACKLIGHTING_LEVEL:
                self.internal_board_state.backlighting_level = MIN_BACKLIGHTING_LEVEL
            self.c_set_backlighting_level(self.internal_board_state.backlighting_level)
        else:
            logging.info("Backlighting is already at minimum.")

    def shout(self, value: Union[int, float, str]):
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
        self.command_handler.queue_command(f'&m,{value}#', ['length mode activated\r', 'alpha mode activated\r',
                                             'shortcut mode activated\r', 'numeric mode activated\r'][value])

    def c_set_interface(self, value: int):
        """
        FEED seems to enable box key strokes.
        """
        self.command_handler.queue_command(f"&fm,{value}#", None)
        if value == 0:
            self.internal_board_state.board_interface = "DCSLinkstream"
            logging.info(f'Interface set to {self.internal_board_state.board_interface}')
        elif value == 1:
            self.internal_board_state.board_interface = "FEED"
            logging.info(f'Interface set to {self.internal_board_state.board_interface}')

    def c_set_backlighting_level(self, value: int):
        if 0 <= value <= MAX_BACKLIGHTING_LEVEL:
            self.command_handler.queue_command(f'&o,{value}#', None)
            self.internal_board_state.backlighting_level = value
        else:
            logging.warning(f"Backlighting level range: (0, {MAX_BACKLIGHTING_LEVEL})")

    def c_set_backlighting_auto_mode(self, value: int):
        self.command_handler.queue_command(f"&oa,{value}", None)
        self.internal_board_state.backlighting_auto_mode = {True: 'auto', False: 'manual'}

    def c_set_backlighting_sensitivity(self, value: int):
        if 0 <= value <= MAX_BACKLIGHTING_SENSITIVITY:
            self.command_handler.queue_command(f"&os,{value}", None)
            self.internal_board_state.backlighting_sensitivity = value
        else:
            logging.warning(f"Backlighting sensitivity range: (0, {MAX_BACKLIGHTING_SENSITIVITY})")

    def c_set_stylus_detection_message(self, value: bool):
        """
        When disabled (false): %t0 %t1 are not sent
        """
        self.command_handler.queue_command(f'&sn,{int(value)}#', f'%sn:{int(value)}#\r')

    def c_set_stylus_settling_delay(self, value: int = 1):
        if 0 <= value <= MAX_SETTLING_DELAY:
            self.command_handler.queue_command(f"&di,{value}#", f"%di:{value}#\r")
        else:
            logging.warning(f"Settling delay value range: (0, {MAX_SETTLING_DELAY})")

    def c_set_stylus_max_deviation(self, value: int):
        if 0 <= value <= MAX_MAX_DEVIATION:
            self.command_handler.queue_command(f"&dm,{value}#", f"%dm:{value}#\r")
        else:
            logging.warning(f"Settling delay value range: (0, {MAX_MAX_DEVIATION})")

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
                    self.controller.internal_board_state.sensor_mode = i

            logging.info(f'{received}')

        elif "a:e" in received:
            self.controller.ping_event_check.clear()
            logging.info('Ping Event Received.')

        elif "sn" in received:
            match = re.findall(f"%sn:(\d)#\r", received)
            if len(match) > 0:
                if match[0] == "1":
                    self.controller.internal_board_state.stylus_status_msg = "enable"
                    logging.info('Stylus Status Message Enable')
                else:
                    self.controller.internal_board_state.stylus_status_msg = "disable"
                    logging.info('Stylus Status Message Disable')

        elif "di" in received:
            match = re.findall(f"%di:(\d)#\r", received)
            if len(match) > 0:
                self.controller.internal_board_state.stylus_settling_delay = int(match[0])
                logging.info(f"Stylus settling delay set to {match[0]}")

        elif "dm" in received:
            match = re.findall(f"%dm:(\d)#\r", received)
            if len(match) > 0:
                self.controller.internal_board_state.stylus_max_deviation = int(match[0])
                logging.info(f"Stylus max deviation set to {int(match[0])}")

        elif "dn" in received:
            match = re.findall(f"%dn:(\d)#\r", received)
            if len(match) > 0:
                self.controller.internal_board_state.number_of_reading = int(match[0])
                logging.info(f"Stylus number set to {int(match[0])}")

        elif "%b" in received:
            match = re.findall("%b:(.*)#", received)
            if len(match) > 0:
                logging.info(f'Board State: {match[0]}')
                self.controller.internal_board_state.board_stats = match[0]

        elif "%q" in received:
            match = re.findall("%q:(-*\d*,\d*)#", received)
            if len(match) > 0:
                logging.info(f'Battery level: {match[0]}')
                self.controller.internal_board_state.battery_level = match[0]

        elif "%u:" in received:
            match = re.findall("%u:(\d)#", received)
            if len(match) > 0:
                if match[0] == '0':
                    logging.info('Board is not calibrated.')
                    self.controller.internal_board_state.calibrated = False
                elif match[0] == '1':
                    logging.info('Board is calibrated.')
                    self.controller.internal_board_state.calibrated = True
            else:
                logging.error(f'Calibration state {self.controller.client.buffer}')

        elif 'Cal Pt' in received:
            logging.info(received.strip("\r") + " mm")
            match = re.findall("Cal Pt (\d) set to: (\d)", received)
            if len(match) > 0:
                self.controller.internal_board_state.__dict__[f'cal_pt_{match[0][0]}'] = int(match[0][1])

    def queue_command(self, command, message=None):
        if message is not None:
            self.expected_message_queue.put(message)
        self.send_queue.put(command)
        logging.info(f'Queuing: Command -> {[command]}, Expected -> {[message]}')

    def _send_command(self):
        command = self.send_queue.get()
        self.controller.client.send(command)
        logging.info(f'Command Sent: {[command]}')


class SocketListener:
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
        try:
            logging.info('Listening started')
            while self.controller.is_listening:
                self.controller.client.receive()
                if len(self.controller.client.buffer) > 0:
                    self._split_board_message()
                    self._process_board_message()
            logging.info('Listening stopped')
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
            logging.info(f'Received Message: {message}')
            out_value = None
            msg_type, msg_value = self._decode_board_message(message)
            logging.info(f"Message Type: {msg_type}, Message Value: {msg_value}")
            if msg_type == "xt_key":
                out_value = msg_value

            elif msg_type == 'swipe':
                self.swipe_value = msg_value
                if msg_value > SWIPE_THRESHOLD:
                    self.swipe_triggered = True

            elif msg_type == 'length':
                if self.swipe_triggered is True:
                    self._check_for_stylus_swipe(msg_value)
                else:
                    out_value = self._map_stylus_length_measurement(msg_value)

            elif msg_type == "unsolicited":
                self.controller.command_handler.received_queue.put(msg_value)

            if out_value is not None:
                self._process_output(out_value)

            time.sleep(0.001)

    def _process_output(self, value):
        shout_value = None
        if value in MAPPABLE_KEYS:
            mapped_value = KEYS_MAP[value]
            if mapped_value == "BACKLIGHT_UP":
                self.controller.backlight_up()
            elif mapped_value == "BACKLIGHT_DOWN":
                self.controller.backlight_down()
            elif mapped_value == "CHANGE_STYLUS":
                self.controller.cycle_stylus()
            elif mapped_value == "UNITS_mm":
                self.controller.change_length_units('mm')
            elif mapped_value == "UNITS_cm":
                self.controller.change_length_units('cm')
            else:
                shout_value = mapped_value
        else:
            shout_value = value

        if not self.controller.is_muted and shout_value is not None:
            logging.info(f"Mapped value {shout_value}")
            self.controller.shout(shout_value)
        else:
            logging.info(f'Key {value} not mapped')

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
                return 'xt_key', XT_KEYS_NAME_MAP[match[0][3]]
        else:
            return 'unsolicited', value

    def _map_stylus_length_measurement(self, value: int):
        if self.controller.board_output_zone == 'middle':
            out_value = value - self.controller.stylus_offset
            if self.controller.length_units == 'cm':
                out_value /= 10
            return out_value
        else:
            index = int((value - DECAL_KEY_DETECTION_ZERO) / DECAL_KEY_RATIO)
            logging.info(f'index {index}')
            if index < DECAL_NUMBER_OF_KEYS:
                return DECAL_KEYS_LAYOUT[self.controller.board_output_zone][index]

    def _check_for_stylus_swipe(self, value: str): #TODO use the swipe_segment and output zone from config
        self.swipe_triggered = False
        if int(value) > 630:
            self.controller.change_board_output_zone('middle')
        elif int(value) > 430:
            self.controller.change_board_output_zone('bottom')
        elif int(value) > 230:
            self.controller.change_board_output_zone('top')
        else:
            self.controller.change_board_output_zone('middle')
        logging.info(f'Board entry: {self.controller.board_output_zone}.')


if __name__ == "__main__":
    from cli import main
    c=main()
