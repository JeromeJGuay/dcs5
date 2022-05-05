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


# ASK FOR CALIBRATION ON BOARD CONNECTION
# ADD STYLUS OFFSETS TO CONFIG FILE
"""
import argparse
import logging
import socket
import bluetooth
import threading
import re
from typing import *
import time
#import pynput.keyboard as keyboard
import pyautogui as pag

from pathlib import PurePath
from utils import json2dict

ENCODING = 'UTF-8'
BUFFER_SIZE = 1024
TERMINATION_CHARACTER = '#'

SETTINGS = json2dict(PurePath(PurePath(__file__).parent, 'src_files/default_settings.json'))

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
    'space': 'space',#keyboard.Key.space,
    'enter': 'enter',#keyboard.Key.enter,
    'del_last': 'backspace',#keyboard.Key.backspace,
    'del': 'delete',#keyboard.Key.delete,
    'up': 'up',#keyboard.Key.up,
    'down': 'down',#keyboard.Key.down,
    'left': 'left',#keyboard.Key.left,
    'right': 'right',#keyboard.Key.right,
    '1B': '-'
}

# STYLUS SETTINGS
STYLUS_OFFSET = {'pen': 6, 'finger': 1}  # mm -> check calibration procedure. TODO
BOARD_KEY_RATIO = 15.385  # ~200/13
BOARD_KEY_DETECTION_RANGE = 2
BOARD_KEY_ZERO = -3.695 - BOARD_KEY_DETECTION_RANGE
BOARD_NUMBER_OF_KEYS = 49


def scan_bluetooth_device():
    devices = {}
    logging.info("Scanning for bluetooth devices ...")
    _devices = bluetooth.discover_devices(lookup_names=True, lookup_class=True)
    number_of_devices = len(_devices)
    logging.info(number_of_devices, " devices found")
    for addr, name, device_class in _devices:
        devices[name] = {'address': addr, 'class': device_class}
        logging.info(f"Devices: \n Name: {name}\n MAC Address: {addr}\n Class: {device_class}")
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

    def __init__(self, method: str = 'socket'):
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
        self.socket.send(command.encode(ENCODING))

    def receive(self):
        try:
            self.buffer += self.socket.recv(BUFFER_SIZE).decode(ENCODING)
        except socket.timeout:
            pass

    def close(self):
        self.socket.close()


class Dcs5BoardState:
    def __init__(self):
        self.sensor_mode: str = None
        self.stylus_status_msg: str = None
        self.stylus_settling_delay: int = None
        self.stylus_max_deviation: int = None
        self.number_of_reading: int = None

        self.battery_level: str = None
        self.humidity: int = None
        self.temperature: int = None
        self.board_stats: str = None
        self.board_interface: str = None

        self.calibrated: bool = None
        self.cal_pt: List[int] = [None, None]

        self.backlighting_level: int = None
        self.backlighting_auto_mode: bool = None
        self.backlighting_sensitivity: int = None


class Dcs5Controller(Dcs5BoardState):
    """
    Notes
    -----
    Firmware update command could be added:
        %h,VER,BR#
        see documentations
    """

    def __init__(self):
        Dcs5BoardState.__init__(self)
        threading.Thread.__init__(self)

        self.listen_thread: threading.Thread = None
        self.command_thread: threading.Thread = None
        self.client: Dcs5Client = Dcs5Client()
        self.client_isconnected: bool = False

        self.send_queue: List[str] = []
        self.received_queue: List[str] = []
        self.expected_message_queue: List[str] = []

        self.listening: bool = False
        self.is_muted: bool = False

        self.stylus: str = 'pen'  # [finger/pen]
        self.stylus_offset: str = STYLUS_OFFSET['pen']
        # {'measure': None, 'typing': None}
        self.stylus_modes_settling_delay: Dict[str: int] = DEFAULT_SETTLING_DELAY
        self.stylus_modes_number_of_reading: Dict[str: int] = DEFAULT_NUMBER_OF_READING
        self.stylus_modes_max_deviation: Dict[str: int] = DEFAULT_MAX_DEVIATION

    def start_client(self, address: str = None, port: int = None):
        logging.info(f'Attempting to connect to board via port {port}.')
        try:
            logging.info('Trying to connect for 30 s.')
            self.client.socket.settimeout(30)
            self.client.connect(address, port)
            self.client_isconnected = True
            logging.info('Connection Successful.')
        except socket.timeout:
            logging.info('Could not connect. Time Out')
        except OSError as err:
            logging.error(err)
        self.client.socket.settimeout(self.client.default_timeout)

    def close_client(self):
        self.client.close()
        logging.info('Client Closed.')

    def queue_command(self, command, message):
        self.send_queue.append(command)
        self.expected_message_queue.append(message)

    def start_listening(self):
        listener = Dcs5Listener(self)
        self.listening = True
        self.command_thread = threading.Thread(target=self.handle_command)
        self.command_thread.start()
        self.listen_thread = threading.Thread(target=listener.listen)
        self.listen_thread.start()

    def stop_listening(self):
        self.listening = False

    def unmute_board(self):
        self.is_muted = False

    def mute_board(self):
        self.is_muted = True

    def change_stylus(self, value: str):
        self.stylus = 'pen'
        self.stylus = STYLUS_OFFSET[self.stylus]
        logging.info(f'Stylus set to {self.stylus}. Stylus offset {self.stylus_offset}')

    def handle_command(self):
        logging.info('Command Handler Initiated')
        while self.listening is True:
            if len(self.received_queue) > 0:
                logging.info(f"Send_Queue: {self.send_queue}")
                logging.info(f"Expected_Queue: {self.expected_message_queue}")
                logging.info(f"Received_Queue: {self.received_queue}")
                isvalid = False
                received = self.received_queue.pop(0)
                expected = None
                while expected is None:
                    expected = self.expected_message_queue.pop(0)
                logging.info(rf'Received: {[received]}, Expected: {[expected]}')
                if "regex_" in expected:
                   # match = re.findall("(" + expected[7:] + ")", received)[0]
                   # if len(match) > 0:
                   #     isvalid = True
                    pass

                elif received == expected:
                    isvalid = True

                if isvalid is True:
                    if received == "....":
                        pass  # TODO something

                    elif 'mode activated' in received:
                        logging.info(f'Mode activated...{received}')
                        pass

                    elif "sn" in received:
                        value = 'TODO'
                        # f'%sn:{int(value)}#\r'
                        # self.number_of_reading = value
                        logging.info('Stylus Status Message Enable')
                    # self.stylus_status_msg = 'Enable'
                    # logging.info('Stylus Status Message Disable')
                    # self.stylus_status_msg = 'Disable'

                    elif "di" in received:
                        value = 'TODO'
                        # f"%di:{value}#\r"
                        # self.number_of_reading = value
                        # self.stylus_settling_delay = value
                        logging.info(f"Stylus settling delay set to {value}")

                    elif "dm" in received:
                        value = "TODO"
                        # f"%dm:{value}#\r":
                        logging.info(f"Stylus max deviation set to {value}")
                        # self.stylus_max_deviation = value

                    elif "dn" in received:
                        value = 'TODO'
                        # f"%dn:{value}#\r":
                        # self.number_of_reading = value
                        logging.info(f"Number of reading set to {value}")

                    elif received == "BATTERY":
                        string = "%q:(-*\d*,\d*)#"

                    elif expected == 'regex_%u:\d#':
                        if received == '%u:0#\r':
                            logging.info('Board is not calibrated.')
                            self.calibrated = False
                        elif received == '%u:1#\r':
                            logging.info('Board is calibrated.')
                            self.calibrated = True
                        else:
                            logging.error(f'Calibration state {self.client.buffer}')

                    elif 'Cal Pt' in received:
                        logging.info(f'Calibration point todo set to todo mm')
                        # if self.client.buffer == f'Cal Pt {pt} set to: {pos}\r':
                        #    self.cal_pt[pt - 1] = pos
                        #    logging.info(f'Calibration point {pt} set to {pos} mm')
                        # else:
                        #    logging.error(f'Calibration point {self.client.buffer}')

                    elif ' &Xr#: X=' in received:
                        logging.info(f'Set stylus down for point TODO ...')
                        # if self.client.buffer == f'&Xr#: X={pt}\r':
                        #    logging.info(f'Set stylus down for point {pt} ...')
                        #    msg = ""
                        #    while f'&{pt}c' not in msg457347:
                        #        self.client.receive()
                        #        msg += self.client.buffer  # FIXME
                        #    logging.info(f'Point {pt} calibrated.')
                else:
                    logging.error(f'Invalid: Command received: {received}, Command expected: {expected}')

            if len(self.send_queue) > 0:
                #  logging.info(f'Send_Queue: {self.send_queue}')
                command = self.send_queue.pop(0)
                self.client.send(command)
                logging.info(f'command sent: {command}')

    def c_board_initialization(self):
        self.queue_command("&init#", "Rebooting in 2 seconds...")

    def c_reboot(self):  # FIXME NOT WORKING
        self.queue_command("&rr#", "%rebooting")

    def c_ping(self):
        """This could use for something more useful. Like checking at regular interval if the board is still active:
        """
        self.queue_command("a#", "%a:e#\r")

    def c_get_board_stats(self):
        self.queue_command("b#", "regex_%.*#")

    def c_get_battery_level(self):
        self.queue_command('&q#', "regex_%q:.*#")

    def c_set_sensor_mode(self, value):
        """ 'length', 'alpha', 'shortcut', 'numeric' """
        self.queue_command(f'&m,{value}#', ['length mode activated\r', 'alpha mode activated\r',
                                            'shortcut mode activated\r', 'numeric mode activated\r'][value])

    def c_set_interface(self, value: int):
        """
        FEED seems to enable box key strokes.
        """
        self.queue_command(f"&fm,{value}#", None)
        if value == 0:
            self.board_interface = "DCSLinkstream"
        elif value == 1:
            self.board_interface = "FEED"

    def c_set_backlighting_level(self, value: int):
        """0-95"""
        self.queue_command(f'&o,{value}#', None)
        self.backlighting_level = value

    def c_set_backlighting_auto_mode(self, value: int):
        self.queue_command(f"&oa,{value}", None)
        self.backlighting_auto_mode = value

    def c_set_backlighting_sensitivity(self, value: int):
        """0-7"""
        self.queue_command(f"&os,{value}", None)
        self.backlighting_sensitivity = {True: 'auto', False: 'manual'}

    def c_set_stylus_detection_message(self, value: bool):
        """
        When disabled (false): %t0 %t1 are not sent
        """
        self.queue_command(f'&sn,{value}', f'%sn:{int(value)}#\r')

    def c_set_stylus_settling_delay(self, value: int = 1):
        self.queue_command(f"&di,{value}#", f"%di:{value}#\r")

    def c_set_stylus_max_deviation(self, value: int):
        self.queue_command(f"&dm,{value}#", f"%dm:{value}#\r")

    def c_set_stylus_number_of_reading(self, value: int = 5):
        self.queue_command(f"&dn,{value}#", f"%dn:{value}#\r")

    def c_restore_cal_data(self):
        self.queue_command("&cr,m1,m2,raw1,raw2#", None)

    def _clear_cal_data(self):
        self.queue_command("&ca#", None)
        self.calibrated = False

    def c_check_calibration_state(self):  # TODO, to be tested
        self.queue_command('&u#', 'regex_%u:\d#\r')

    def c_set_calibration_points_mm(self, pt: int, pos: int):
        self.queue_command(f'&{pt}mm,{pos}#', f'Cal Pt {pt} set to: {pos}\r')

    def c_calibrate(self, pt: int):
        self.queue_command(f"&{pt}r#", f'&Xr#: X={pt}\r')


class Dcs5Listener:
    """
    """

    def __init__(self, controller: Dcs5Controller):
        self.controller = controller
        self.message_queue: list = []

        self.stylus_output_mode: str = 'center'  # [top, center, bottom]
        self.swipe_triggered: bool = False
        self.swipe_value: str = ''

        #self.keyboard_controller = keyboard.Controller()
        self.stdout_value: str = None

    def listen(self):
        self.controller.client.receive()
        logging.info('Listening started')
        while self.controller.listening is True:
            try:
                self.controller.client.receive()
                self.split_board_message()
                self.process_board_message()
            except socket.timeout:
                pass
        logging.info('Listening stopped')

    def split_board_message(self):
        delimiters = ["\n", "\r", "#", "%rebooting", "Rebooting in 2 seconds ..."]
        for d in delimiters:
            msg = self.controller.client.buffer.split(d)
            if len(msg) > 1:
                self.controller.client.buffer = msg[-1]
                self.message_queue.append(msg[0] + d)
                logging.info(rf"messages received: {self.message_queue}")

    def process_board_message(self):
        """ANALYZE SOLICITED VS UNSOLICITED MESSAGE"""
        while len(self.message_queue) > 0:
            message = self.message_queue.pop(0)
            self.stdout_value = None
            msg_type, msg_value = self.decode_board_message(message)
            if msg_type == "xt_key":
                if msg_value in ['a1', 'a2', 'a3', 'a4', 'a5', 'a6']:
                    self.stdout_value = f'f{msg_value[-1]}'
                elif msg_value in ['b1', 'b2', 'b3', 'b4', 'b5', 'b6']:
                    if msg_value == 'b1':
                        self.change_backlighting_level(1)
                    elif msg_value == 'b2':
                        self.change_backlighting_level(-1)
                    else:
                        logging.info(f'{msg_value} not mapped.')
                elif msg_value == 'mode':
                    self.cycle_stylus()
                elif msg_value == 'skip':
                    self.stdout_value = 'space'
                elif msg_value in ['c1']:
                    logging.info(f'{msg_value} not mapped.')
                else:
                    self.stdout_value = msg_value

            elif msg_type == 'swipe':
                self.swipe_value = msg_value
                if msg_value > SWIPE_THRESHOLD:
                    self.swipe_triggered = True

            elif msg_type == 'length':
                if self.swipe_triggered is True:
                    self.check_for_stylus_swipe(msg_value)
                    logging.info(f'Board entry: {self.stylus_output_mode}.')
                else:
                    self.stdout_value = self.map_stylus_length_measure(msg_value)

            elif msg_type == "unsolicited":
                self.controller.received_queue.append(msg_value)

            if self.stdout_value is not None:
                logging.info(f'output value {self.stdout_value}')
                if self.controller.is_muted is False:
                    self.stdout_to_keyboard(self.stdout_value)

    @staticmethod
    def decode_board_message(value: str):
        pattern = "%t,([0-9])#|%l,([0-9]*)#|%s,([0-9]*)#|F,([0-9]{2})#"
        match = re.findall(pattern, value)
        logging.info(match)
        if len(match) > 0:
            if match[0][1] != "":
                return 'length', int(match[0][1])
            elif match[0][2] != "":
                return 'swipe', int(match[0][2])
            elif match[0][3] != "":
                return 'xt_key', XT_KEY_MAP[match[0][3]]
        else:
            return 'unsolicited', value

    def check_for_stylus_swipe(self, value: str):
        self.swipe_triggered = False
        if int(value) > 630:
            self.change_stylus_entry_mode('center')
        elif int(value) > 430:
            self.change_stylus_entry_mode('bottom')
        elif int(value) > 230:
            self.change_stylus_entry_mode('top')

    def change_stylus_entry_mode(self, value: str):
        self.stylus_output_mode = value
        mode = {'center': 'measure', 'bottom': 'typing', 'top': 'typing'}[value]
        self.controller.c_set_stylus_settling_delay(self.controller.stylus_modes_settling_delay[mode])
        self.controller.c_set_stylus_number_of_reading(self.controller.stylus_modes_number_of_reading[mode])
        self.controller.c_set_stylus_max_deviation(self.controller.stylus_modes_max_deviation[mode])

    def map_stylus_length_measure(self, value: int):
        if self.stylus_output_mode == 'center':
            return value - self.controller.stylus_offset
        else:
            index = int((value - BOARD_KEY_ZERO) / BOARD_KEY_RATIO)
            logging.info(f'index {index}')
            if index < BOARD_NUMBER_OF_KEYS:
                return BOARD_KEYS_MAP[self.stylus_output_mode][index]

    def stdout_to_keyboard(self, value: str):
        if value in KEYBOARD_MAP:
            pag.press(KEYBOARD_MAP[value])
        elif isinstance(value, (int, float)):
            pag.write(str(value))
        elif value in ['f1', 'f2', 'f3', 'f4', 'f5', 'f6']:
            pag.press(value)
        elif str(value) in '.0123456789abcdefghijklmnopqrstuvwxyz':
            pag.write(value)

    def cycle_stylus(self):
        if self.controller.stylus == 'pen':
            self.controller.change_stylus('finger')
        else:
            self.controller.change_stylus('pen')

    def change_backlighting_level(self, value: int):
        if value == 1 and self.controller.backlighting_level < MAX_BACKLIGHTING_LEVEL:
            self.controller.backlighting_level += 15
            if self.controller.backlighting_level > MAX_BACKLIGHTING_LEVEL:
                self.controller.backlighting_level = MAX_BACKLIGHTING_LEVEL
            self.controller.c_set_backlighting_level(self.controller.backlighting_level)

        if value == -1 and self.controller.backlighting_level > MIN_BACKLIGHTING_LEVEL:
            self.controller.backlighting_level += -15
            if self.controller.backlighting_level < MIN_BACKLIGHTING_LEVEL:
                self.controller.backlighting_level = MIN_BACKLIGHTING_LEVEL
            self.controller.c_set_backlighting_level(self.controller.backlighting_level)


def init_dcs5_board(c: Dcs5Controller):
    """
    init a board object
    change default settings with settings
    applies them
    """
    c.c_set_sensor_mode(1)
    c.c_set_interface(1)
    c.c_set_backlighting_level(DEFAULT_BACKLIGHTING_LEVEL)
    c.c_set_stylus_detection_message(False)
    c.c_set_stylus_settling_delay(50)#DEFAULT_SETTLING_DELAY)
    c.c_set_stylus_max_deviation(DEFAULT_MAX_DEVIATION)
    c.c_set_stylus_number_of_reading(DEFAULT_NUMBER_OF_READING)


def launch_dcs5_board(scan: bool):
    c = Dcs5Controller()
    address = search_for_dcs5board() if scan is True else DCS5_ADDRESS
    try:
        c.start_client(address, PORT)
        if c.client_isconnected is True:
            try:
                c.start_listening()
                time.sleep(1)
                c.mute_board()
                init_dcs5_board(c)
                c.unmute_board()
            except socket.error as err:
                logging.info(err)
    except (KeyboardInterrupt, SystemExit) as err:
        logging.info(err)
        if c.client_isconnected is True:
            c.close_client()

    return c


def main(scan: bool = False):
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-v",
        "--verbose",
        nargs=1,
        default="info",
        help="Provide logging level: [debug, info, warning, error, critical]",
    )
    #    parser.add_argument(
    #        "-log",
    #        "--logfile",
    #        nargs=1,
    #        default="./lod/dcs5.log",
    #        help=("Filename to print the logs to."),
    #    )
    args = parser.parse_args()

    log_name = 'dcs5_log_' + time.strftime("%y%m%dT%H%M%S", time.gmtime())

    log_path = PurePath(PurePath(__file__).parent, 'logs', log_name)

    logging.basicConfig(
        level=args.verbose.upper(),
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(log_path),
            logging.StreamHandler()
        ]
    )
    logging.info('Starting')
    c = launch_dcs5_board(scan)

    return c


if __name__ == "__main__":
    try:
        c = main()
    except KeyboardInterrupt:
        c.close_client()

