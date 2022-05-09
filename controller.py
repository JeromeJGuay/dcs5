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
import pyautogui as pag

from pathlib import PurePath
from utils import json2dict, resolve_relative_path
from dataclasses import dataclass
from queue import Queue

ENCODING = 'UTF-8'
BUFFER_SIZE = 1024

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
        self.socket.send(command.encode(ENCODING))

    def receive(self):
        try:
            self.buffer += self.socket.recv(BUFFER_SIZE).decode(ENCODING)
        except socket.timeout:
            pass

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
    #humidity: int = None
    #temperature: int = None
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

    def __init__(self):
        Dcs5BoardState.__init__(self)
        threading.Thread.__init__(self)

        self.board_state = Dcs5BoardState()

        self.listen_thread: threading.Thread = None
        self.command_thread: threading.Thread = None

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

        self.shout_method = 'keyboard'
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

    def queue_command(self, command, message=None):
        logging.info(f'Queued: {[command]}, {[message]}')
        if message is not None:
            self.expected_message_queue.put(message)
        self.send_queue.put(command)

    def start_listening(self):
        self.client.receive()
        logging.info('starting threads')
        listener = Dcs5Listener(self)
        self.listening = True
        self.command_thread = threading.Thread(target=self.handle_command)
        self.command_thread.start()

        self.listen_thread = threading.Thread(target=listener.listen)
        self.listen_thread.start()

    def stop_listening(self):
        self.listening = False
        self.listen_thread.join()
        self.command_thread.join()
        self.clear_queues()

    def clear_queues(self):
        self.send_queue.queue.clear()
        self.received_queue.queue.clear()
        self.expected_message_queue.queue.cleart()

    def unmute_board(self):
        self.is_muted = False

    def mute_board(self):
        self.is_muted = True

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

    def initialize_board(self):
        logging.info('Initializing Board.')

        self.start_listening()
        self.c_set_sensor_mode(1)
        self.c_set_interface(1)
        self.c_set_backlighting_level(DEFAULT_BACKLIGHTING_LEVEL)
        self.c_set_stylus_detection_message(False)
        self.c_set_stylus_settling_delay(DEFAULT_SETTLING_DELAY['measure'])
        self.c_set_stylus_max_deviation(DEFAULT_MAX_DEVIATION['measure'])
        self.c_set_stylus_number_of_reading(DEFAULT_NUMBER_OF_READING['measure'])
        self.c_get_board_stats()
        self.c_get_battery_level()
        self.c_check_calibration_state()

        logging.info('Board Initiatializing Successful')

    def handle_command(self):
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
                    if received == "....":
                        pass  # TODO something

                    elif 'mode activated' in received:
                        logging.info(f'{received}')
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
                        logging.info(f'Calibration point todo set to todo mm')
                        # if self.client.buffer == f'Cal Pt {pt} set to: {pos}\r':
                        #    self.cal_pt[pt - 1] = pos
                        #    logging.info(f'Calibration point {pt} set to {pos} mm')
                        # else:
                        #    logging.error(f'Calibration point {self.client.buffer}')

                    elif '&Xr#' in received:
                        logging.info(f'Set stylus down for point TODO ...')
                        logging.info(f"CAL : {self.received_queue.get()}")
                        time.sleep(0.5)
                        msg=""
                        while self.received_queue.qsize() > 0:
                            print(1)
                            msg += self.received_queue.get()

                        logging.info(f"Point TODO calibrated {msg}")

                else:
                    logging.error(f'Invalid: Command received: {[received]}, Command expected: {[expected]}')
                self.received_queue.task_done()
                self.expected_message_queue.task_done()

            if not self.send_queue.empty():
                self._send_command()

            time.sleep(0.1)

    def _send_command(self):
        command = self.send_queue.get()
        print(command)
        self.client.send(command)
        self.send_queue.task_done()

    def c_board_initialization(self):
        self.queue_command("&init#", "Setting EEPROM init flag.\r")

    def c_reboot(self):  # FIXME NOT WORKING
        self.queue_command("&rr#", "%rebooting")

    def c_ping(self):
        """This could use for something more useful. Like checking at regular interval if the board is still active:
        """
        self.queue_command("a#", "%a:e#")

    def c_get_board_stats(self):
        self.queue_command("b#", "regex_%b.*#")

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
            self.board_state.board_interface = "DCSLinkstream"
            logging.log(f'Interface set to {self.board_state.board_interface}')
        elif value == 1:
            self.board_state.board_interface = "FEED"
            logging.log(f'Interface set to {self.board_state.board_interface}')


    def c_set_backlighting_level(self, value: int):
        """0-95"""
        self.queue_command(f'&o,{value}#', None)
        self.board_state.backlighting_level = value

    def c_set_backlighting_auto_mode(self, value: int):
        self.queue_command(f"&oa,{value}", None)
        self.board_state.backlighting_auto_mode = value

    def c_set_backlighting_sensitivity(self, value: int):
        """0-7"""
        self.queue_command(f"&os,{value}", None)
        self.board_state.backlighting_sensitivity = {True: 'auto', False: 'manual'}

    def c_set_stylus_detection_message(self, value: bool):
        """
        When disabled (false): %t0 %t1 are not sent
        """
        self.queue_command(f'&sn,{int(value)}', f'%sn:{int(value)}#\r')

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
        controller.initialize_board()
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
        format="%(asctime)s [%(levelname)s] %(message)s",
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