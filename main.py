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

"""
import argparse
import logging
import socket
import bluetooth
import threading
import re
from typing import *
import time
import datetime
from pynput.keyboard import Key, Controller
from pathlib import PurePath

import PySimpleGUI as sg


SOCKET_METHOD = ['socket', 'bluetooth'][0]
DEVICE_NAME = "BigFinDCS5-E5FE"
PORT = 1

DCS5_ADDRESS = "00:06:66:89:E5:FE"
EXIT_COMMAND = "stop"

ENCODING = 'UTF-8'
BUFFER_SIZE = 4096

DEFAULT_SETTLING_DELAY = {'center': 3, 'top': 1, 'bottom': 1} # from 0 to 20 DEFAULT 1
DEFAULT_MAX_DEVIATION = {'center': 6, 'top': 1, 'bottom': 1}  # from 1 to 100 DEFAULT 6
DEFAULT_NUMBER_OF_READING = {'center': 5, 'top': 1, 'bottom': 1} # from 0 to 20 DEFAULT 1

MAX_SETTLING_DELAY = 20
MAX_MAX_DEVIATION = 100

DEFAULT_BACKLIGHTING_LEVEL = 0
MIN_BACKLIGHTING_LEVEL = 0
MAX_BACKLIGHTING_LEVEL = 95
DEFAULT_BACKLIGHTING_AUTO_MODE = False
DEFAULT_BACKLIGHTING_SENSITIVITY = 0
MIN_BACKLIGHTING_SENSITIVITY = 0
MAX_BACKLIGHTING_SENSITIVITY = 7

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
    'top': list('abcdefghijklmnopqrstuvwxyz') + [f'{i + 1}B' for i in range(8)],
    'bottom': list('01234.56789') + \
           ['view', 'batch', 'tab', 'histo', 'summary', 'dismiss', 'fish', 'sample',
            'sex', 'size', 'light_bulb', 'scale', 'location', 'pit_pwr', 'settings'] + \
           [f'{i + 1}G' for i in range(8)]}

KEYBOARD_MAP = {
    'space': Key.space,
    'enter': Key.enter,
    'del_last': Key.backspace,
    'del': Key.delete,
    'up': Key.up,
    'down': Key.down,
    'left': Key.left,
    'right': Key.right,
    '1B': '-'
}


# STYLUS SETTINGS
STYLUS_OFFSET = {'pen': 6, 'finger': 1}  # mm -> check calibration procedure. TODO
BOARD_KEY_RATIO = 15.385  # ~200/13
BOARD_KEY_DETECTION_RANGE = 2
BOARD_KEY_ZERO = 104 - BOARD_KEY_DETECTION_RANGE
BOARD_KEY_EXTENT = 627 - BOARD_KEY_DETECTION_RANGE
BOARD_KEY_DEL_LAST = 718 - BOARD_KEY_DETECTION_RANGE


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
        self.buffer: str = None
        if method == 'socket':
            self.socket = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)
        elif method == 'bluetooth':
            self.socket = bluetooth.BluetoothSocket(bluetooth.RFCOMM)
        else:
            raise ValueError('Method must be one of [socket, bluetooth]')
        self.method: str = method

    def connect(self, address: str, port: int):
        self.dcs5_address = address
        self.port = port
        self.socket.connect((self.dcs5_address, self.port))

    def send(self, command: str):
        self.socket.send(bytes(command, ENCODING))

    def receive(self):
        self.buffer = str(self.socket.recv(BUFFER_SIZE).decode(ENCODING))

    def clear_socket_buffer(self):
        self.socket.settimeout(.1)
        try:
            self.socket.recv(1024)
        except socket.timeout:
            pass
        self.socket.settimeout(None)

    def close(self):
        self.socket.close()


class Dcs5Interface:
    """
    Notes
    -----
    Firmware update command could be added:
        %h,VER,BR#
        see documentations
    """

    def __init__(self):
        self.client: Dcs5Client = Dcs5Client(method=SOCKET_METHOD)
        self.client_connected: bool = False

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

        self.feedback_msg: str = None

    def start_client(self, address: str = None, port: int = None):
        logging.info(f'Attempting to connect to board via port {port}.')
        try:
            self.client.connect(address, port)
            self.client_connected = True
            logging.info('Connection Successful.')
        except (bluetooth.BluetoothError, socket.error) as err:
            logging.info(err)

    def close_client(self):
        self.client.close()
        logging.info('Client Closed.')

    def set_default_board_settings(self):
        #self.set_sensor_mode(0)  # length measuring mode # doesn't seems to do much
        self.set_interface(1)  # FEED
        self.set_backlighting_level(DEFAULT_BACKLIGHTING_LEVEL)
        self.set_stylus_detection_message(False)
        self.set_stylus_settling_delay(DEFAULT_SETTLING_DELAY['center'])
        self.set_stylus_max_deviation(DEFAULT_MAX_DEVIATION['center'])
        self.set_stylus_number_of_reading(DEFAULT_NUMBER_OF_READING['center'])

    def query(self, value: str, listen: bool = True):
        """Receive message are located in self.client.buffer"""
        self.client.send(value)
        if listen is True:
            time.sleep(0.1) #to prevent some error. Sometime message from the board are cut. This may fix it
            self.client.receive()

    def board_initialization(self):
        self.query('&init#')
        if self.client.buffer == "Rebooting in 2 seconds...":
            logging.info(self.client.buffer)

    def reboot(self):  # FIXME NOT WORKING
        self.query('&rr#')
        if self.client.buffer == "%rebooting":
            logging.info(self.client.buffer)

    def ping(self):
        """This could use for something more useful. Like checking at regular interval if the board is still active:
        """
        self.query('a#')
        if self.client.buffer == '%a:e#':
            logging.info('pong')

    def get_board_stats(self):
        self.query('b#')
        self.board_stats = self.client.buffer
        logging.info(self.client.buffer)

    def get_battery_level(self):
        self.client.send('&q#')
        self.client.receive()
        self.battery_level = re.findall(r'%q:(-*\d*,\d*)#', self.client.buffer)[0]
        logging.info(f"Battery: {self.battery_level}%")

    def set_sensor_mode(self, value):
        """
        0 -> length (length measure mode)
        1 -> alpha (keyboard)
        2 -> shortcut 'shortcut mode activated\r'
        3 -> numeric 'numeric mode activated\r'
        """
        self.client.send(f'&m,{int(value)}#')
        self.client.receive()
        if self.client.buffer == 'length mode activated\r':
            self.sensor_mode = 'length'
            logging.info(self.client.buffer)
        elif self.client.buffer == 'alpha mode activated\r':
            self.sensor_mode = 'alpha'
            logging.info(self.client.buffer)
        elif self.client.buffer == 'shortcut mode activated\r':
            self.sensor_mode = 'shortcut'
            logging.info(self.client.buffer)
        elif self.client.buffer == 'numeric mode activated\r':
            self.sensor_mode = 'numeric'
            logging.info(self.client.buffer)
        else:
            logging.error(f'Return Error,  {self.client.buffer}')

    def set_interface(self, value: int):
        """
        FEED seems to enable box key strokes.
        """
        self.query(f"&fm,{value}#", listen=False)
        if value == 0:
            self.board_interface = "DCSLinkstream"
        elif value == 1:
            self.board_interface = "FEED"

    def restore_cal_data(self):
        self.query("&cr,m1,m2,raw1,raw2#")
        logging.info(self.client.buffer)

    def clear_cal_data(self):
        self.query("&ca#")
        logging.info(self.client.buffer)
        self.calibrated = False

    def set_backlighting_level(self, value: int):
        """0-95"""
        self.query(f'&o,{int(value)}#', listen=False)
        self.backlighting_level = value

    def set_backlighting_auto_mode(self, value: bool):
        self.query(f"&oa,{int(value)}", listen=False)
        self.backlighting_auto_mode = value

    def set_backlighting_sensitivity(self, value: int):
        """0-7"""
        self.query(f"&os,{int(value)}", listen=False)
        self.backlighting_sensitivity = {True: 'auto', False: 'manual'}

    def set_stylus_detection_message(self, value: bool):
        """
        When disabled (false): %t0 %t1 are not sent
        """
        self.query(f'&sn,{int(value)}')
        if self.client.buffer == f'%sn:{int(value)}#\r':  # NOT WORKING
            if value is True:
                logging.info('Stylus Status Message Enable')
                self.stylus_status_msg = 'Enable'
            else:
                logging.info('Stylus Status Message Disable')
                self.stylus_status_msg = 'Disable'
        else:
            logging.error(f'Stylus status message,  {self.client.buffer}')

    def set_stylus_settling_delay(self, value: int = 1):
        self.query(f"&di,{value}#")
        if self.client.buffer == f"%di:{value}#\r":
            self.stylus_settling_delay = value
            logging.info(f"Stylus settling delay set to {value}")
        else:
            logging.error(f'Settling delay,  {self.client.buffer}')

    def set_stylus_max_deviation(self, value: int):
        self.query(f"&dm,{value}#")
        if self.client.buffer == f"%dm:{value}#\r":
            self.stylus_max_deviation = value
            logging.info(f"Stylus max deviation set to {value}")
        else:
            logging.error(f'Max deviation,  {self.client.buffer}')

    def set_stylus_number_of_reading(self, value: int = 5):
        self.query(f"&dn,{value}#")
        if self.client.buffer == f"%dn:{value}#\r":
            self.number_of_reading = value
            logging.info(f"Number of reading set to {value}")
        else:
            logging.error(f'Number of reading,  {self.client.buffer}')

    def check_calibration_state(self):  # TODO, to be tested
        self.query('&u#')
        if self.client.buffer == '%u:0#\r':
            logging.info('Board is not calibrated.')
            self.calibrated = False
        elif self.client.buffer == '%u:1#\r':
            logging.info('Board is calibrated.')
            self.calibrated = True
        else:
            logging.error(f'Calibration state {self.client.buffer}')

    def set_calibration_points_mm(self, pt: int, pos: int):
        self.query(f'&{pt}mm,{pos}#')
        if self.client.buffer == f'Cal Pt {pt} set to: {pos}\r':
            self.cal_pt[pt - 1] = pos
            logging.info(f'Calibration point {pt} set to {pos} mm')
        else:
            logging.error(f'Calibration point {self.client.buffer}')

    def calibrate(self, pt: int):
        if self.cal_pt[pt - 1] is not None:
            self.query(f"&{pt}r#")
            if self.client.buffer == f'&Xr#: X={pt}\r':
                logging.info(f'Set stylus down for point {pt} ...')
                msg = ""
                while f'&{pt}c' not in msg:
                    self.client.receive()
                    msg += self.client.buffer  # FIXME
                logging.info(f'Point {pt} calibrated.')


class Dcs5Controller(Dcs5Interface):
    """
    """
    def __init__(self):
        Dcs5Interface.__init__(self)
        threading.Thread.__init__(self)

        self.listen_thread: threading.Thread = None
        self.gui_thread: threading.Thread = None

        self.listening: bool = False
        self.keyboard = Controller()

        self.stylus: str = 'pen'  # [finger/pen]
        self.stylus_offset: str = STYLUS_OFFSET['pen']

        self.stylus_entry_mode: str = 'center'  # [top, center, bottom]
        self.stylus_modes_settling_delay: Dict[str: int] = DEFAULT_SETTLING_DELAY
        self.stylus_modes_number_of_reading: Dict[str: int] = DEFAULT_NUMBER_OF_READING
        self.stylus_modes_max_deviation: Dict[str: int] = DEFAULT_MAX_DEVIATION
        self.swipe_triggered: bool = False
        self.swipe_value: str = ''

        self.out_value: str = None

        self.out = None

    def start_listening(self):
        self.listen_thread = threading.Thread(target=self.listen)
        self.listen_thread.start()
        self.listen_thread.join()

    def start_gui(self):
        self.gui_thread = threading.Thread(target=self.gui)
        self.gui_thread.start()
        self.gui_thread.join()

    def listen(self):
        self.set_backlighting_level(95)
        self.set_backlighting_auto_mode(False)
        self.listening = True
        self.client.clear_socket_buffer()
        logging.info('Listening started')
        self.client.socket.settimeout(1)
        while self.listening is True:
            try:
                self.client.receive()
                self.process_board_message()
            except socket.timeout:
                pass
        self.client.socket.settimeout(None)
        logging.info('Listening stopped')
        self.set_backlighting_level(0)

    def stop_listening(self):
        self.listening = False

    def process_board_message(self):
        for msg in self.client.buffer.replace('\r', '').split('#'):
            self.out_value = None
            if msg == "":
                continue
            out = self.decode_board_message(msg)
            if out is None:
                continue

            if out in ['a1', 'a2', 'a3', 'a4', 'a5', 'a6']:
                self.out_value = f'f{out[-1]}'
            elif out in ['b1', 'b2', 'b3', 'b4', 'b5', 'b6']:
                if out == 'b1':
                    self.change_backlighting(1)
                elif out == 'b2':
                    self.change_backlighting(-1)
                else:
                    logging.info(f'{out} not mapped.')
            elif out == 'mode':
                self.change_stylus()
            elif out == 'skip':
                self.out_value = 'space'
            elif out in ['c1']:
                logging.info(f'{out} not mapped.')
            else:
                if isinstance(out, tuple):
                    if out[0] == 's':
                        self.swipe_value = out[1]
                        if out[1] > SWIPE_THRESHOLD:
                            self.swipe_triggered = True
                    if out[0] == 'l':
                        if self.swipe_triggered is True:
                            self.check_for_stylus_swipe(out[1])
                            logging.info(f'Board entry: {self.stylus_entry_mode}.')
                        else:
                            self.out_value = self.map_stylus_length_measure(out[1])
                else:
                    self.out_value = out

            if self.out_value is not None:
                logging.info(f'output value {self.out_value}')
                self.stdout_to_keyboard(self.out_value)

    def decode_board_message(self, value: str):
        if '%t' in value:
            return None
        elif '%l' in value:
            return 'l', self.get_length(value)
        elif '%s' in value:
            return 's', self.get_swipe(value)
        elif 'F' in value:
            return XT_KEY_MAP[value[2:]]

    def check_for_stylus_swipe(self, value: str):
        self.swipe_triggered = False
        if int(value) > 630:
            self.change_stylus_entry_mode('center')
            self.flash_lights(1)
        elif int(value) > 430:
            self.change_stylus_entry_mode('bottom')
            self.flash_lights(1)
        elif int(value) > 230:
            self.change_stylus_entry_mode('top')
            self.flash_lights(1)

    def change_stylus_entry_mode(self, value: str):
        self.stylus_entry_mode = value
        self.set_stylus_settling_delay(DEFAULT_SETTLING_DELAY[value])
        self.set_stylus_number_of_reading(DEFAULT_NUMBER_OF_READING[value])
        self.set_stylus_max_deviation(DEFAULT_MAX_DEVIATION[value])

    def map_stylus_length_measure(self, value: int):
        if self.stylus_entry_mode == 'center':
            return value - self.stylus_offset
        else:
            if value < BOARD_KEY_ZERO:
                return 'space'
            elif value < BOARD_KEY_EXTENT:
                index = int((value - BOARD_KEY_ZERO) / BOARD_KEY_RATIO)
                return BOARD_KEYS_MAP[self.stylus_entry_mode][index]
            elif value < BOARD_KEY_DEL_LAST:
                return 'space'
            else:
                return 'del_last'

    def stdout_to_keyboard(self, value: str):
        if value in KEYBOARD_MAP:
            self.keyboard.tap(KEYBOARD_MAP[value])
        elif value in ['f1', 'f2', 'f3', 'f4', 'f5', 'f6']:
            self.keyboard.tap(Key.__dict__[value])
        elif str(value) in '.0123456789abcdefghijklmnopqrstuvwxyz':
            self.keyboard.tap(value)
        elif isinstance(value, (int, float)):
            self.keyboard.type(str(value))

    def change_stylus(self):
        if self.stylus == 'pen':
            logging.info('Stylus set to finger')
            self.stylus = 'finger'
        else:
            self.stylus = 'pen'
        logging.info(f'Stylus set to {self.stylus}. Stylus offset {self.stylus_offset}')
        self.stylus_offset = STYLUS_OFFSET[self.stylus]

    def flash_lights(self, n):
        current_level = self.backlighting_level
        for i in range(n):
            self.set_backlighting_level(0)
            time.sleep(1)
            self.set_backlighting_level(current_level)

    def change_backlighting(self, value: int):
        if value == 1 and self.backlighting_level < MAX_BACKLIGHTING_LEVEL:
            self.backlighting_level += 15
            if self.backlighting_level > MAX_BACKLIGHTING_LEVEL:
                self.backlighting_level = MAX_BACKLIGHTING_LEVEL
            self.set_backlighting_level(self.backlighting_level)

        if value == -1 and self.backlighting_level > MIN_BACKLIGHTING_LEVEL:
            self.backlighting_level += -15
            if self.backlighting_level < MIN_BACKLIGHTING_LEVEL:
                self.backlighting_level = MIN_BACKLIGHTING_LEVEL
            self.set_backlighting_level(self.backlighting_level)

    @staticmethod
    def get_length(value: str):
        return int(re.findall(r"%l,(\d+)", value)[0])

    @staticmethod
    def get_swipe(value: str):
        return int(re.findall(r"%s,(-*\d+)", value)[0])

    def gui(self):
        sg.theme('DarkAmber')

        layout = [
                  [sg.Text('set settling delay'), sg.Input(f'{self.stylus_settling_delay}', key='-delay_input-', do_not_clear=True, size=(4,1))],
                  [sg.Text('set max deviation'), sg.Input(key='-deviation_input-')]
                  [sg.Button("start listening"), sg.Button("stop listening")],
        # Create the window
        window = sg.Window("DCS5-XT Board Interface", layout, finalize=True)

        while True:
            event, values = window.read(timeout=1)
            # End program if user closes window or
            # presses the OK button
            if event == "start listening":
                self.start_listening()
            if event == 'stop listening':
                self.stop_listening()
            if event == '-delay_input-' + "_Enter":
                if values['-delay_input-'].isnumeric():
                    #self.set_stylus_settling_delay(int(values['delay_input']))
                    print(event)
                    self.stylus_settling_delay = int(values['-delay_input-'])
            if '-delay_input-' in event:
                window['-delay_input-'].update(self.stylus_settling_delay)
                window['-delay_input_text-'].update(self.stylus_settling_delay)

            if event == 'deviation_input' + "_Enter":
                pass
            if event == sg.WIN_CLOSED:
                break


        window.close()


def launch_dcs5_board(scan: bool):

    c = Dcs5Controller()
    address = search_for_dcs5board() if scan is True else DCS5_ADDRESS
    try:
        c.start_client(address, PORT)
        if c.client_connected is True:
            try:
                c.set_default_board_settings()
                #c.start_listening()
                c.start_gui()
            except (bluetooth.BluetoothError, socket.error) as err:
                logging.info(err)
    except (KeyboardInterrupt, SystemExit) as err:
        logging.info(err)
        if c.client_connected is True:
            c.close_client()

    return c


def main(scan: bool = False):
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-v",
        "--verbose",
        nargs=1,
        default="info",
        help=("Provide logging level: [debug, info, warning, error, critical]"),
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

    logging.info('Finished')

    return c


if __name__ == "__main__":
    #c = main()
    c = Dcs5Controller()
    c.start_gui()

