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
import curses.textpad
import socket
import bluetooth
import re
from typing import *
import curses  # Terminal Dynamic Printing
import time

SOCKET_METHOD = ['socket', 'bluetooth'][0]
DEVICE_NAME = "BigFinDCS5-E5FE"
PORT = 1

DCS5_ADDRESS = "00:06:66:89:E5:FE"
EXIT_COMMAND = "stop"

ENCODING = 'UTF-8'
BUFFER_SIZE = 4096

DEFAULT_SETTLING_DELAY = 3 # 1  # from 0 to 20 DEFAULT 1
DEFAULT_MAX_DEVIATION = 6  # from 1 to 100 DEFAULT 6
DEFAULT_NUMBER_OF_READING = 5

DEFAULT_BACKLIGHTING_LEVEL = 0
MIN_BACKLIGHTING_LEVEL = 0
MAX_BACKLIGHTING_LEVEL = 95
DEFAULT_BACKLIGHTING_AUTO_MODE = False
DEFAULT_BACKLIGHTING_SENSITIVITY = 0
MIN_BACKLIGHTING_SENSITIVITY = 0
MAX_BACKLIGHTING_SENSITIVITY = 7

DEFAULT_FINGER_STYLUS_OFFSET = -5

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

XT_KEY_TYPES = {'function': tuple(f'a{i}' for i in range(1, 7)),
             'mode_function': tuple(f'b{i}' for i in range(1, 7)),
             'numpad': tuple(f'{i}' for i in range(0, 10)) + ('.', 'enter', 'del', 'skip'),
                }


SWIPE_THRESHOLD = 20


BOARD_KEYS_MAP = {'top': list('abcdefghijklmnopqrstuvwxyz') + [f'{i + 1}B' for i in range(8)],
              'bot': list('1234.56789') + [
                         'view', 'batch', 'tab', 'histo', 'summary', 'dismiss', 'fish', 'sample', 'sex', 'size',
                         'light_bulb', 'scale', 'location', 'pit_pwr', 'settings'
                     ] + [f'{i+1}G' for i in range(8)]}

# pen stylus measure offset = 12 from center to measure.
STYLUS_OFFSET = {'pen': 6, 'finger': 2} # mm -> check calibration procedure. TODO
BOARD_KEY_RATIO = 15.385 #~200/13
BOARD_KEY_DETECTION_RANGE = 2
BOARD_KEY_ZERO = 104 - BOARD_KEY_DETECTION_RANGE
BOARD_KEY_EXTENT = 627 - BOARD_KEY_DETECTION_RANGE
BOARD_KEY_DEL_LAST = 718 - BOARD_KEY_DETECTION_RANGE


def scan_bluetooth_device():
    devices = {}
    print("Scanning for bluetooth devices ...")
    _devices = bluetooth.discover_devices(lookup_names=True, lookup_class=True)
    number_of_devices = len(_devices)
    print(number_of_devices, " devices found")
    for addr, name, device_class in _devices:
        devices[name] = {'address': addr, 'class': device_class}
        print('\n')
        print("Devices:")
        print(f" Name: {name}")
        print(f" MAC Address: {addr}")
        print(f" Class: {device_class}")
        print('\n')
    return devices


def search_for_dcs5board() -> str:
    devices = scan_bluetooth_device()
    if DEVICE_NAME in devices:
        print(f'{DEVICE_NAME}, found.')
        return devices[DEVICE_NAME]['address']
    else:
        print(f'{DEVICE_NAME}, not found.')
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
        try:
            self.socket.connect((self.dcs5_address, self.port))
        except (bluetooth.BluetoothError, socket.error) as err:
            print(err)
            pass

    def send(self, command: str):
        self.socket.send(bytes(command, ENCODING))

    def receive(self):
        self.buffer = str(self.socket.recv(BUFFER_SIZE).decode(ENCODING))

    def clear_socket_buffer(self):
        self.socket.settimeout(.01)
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
        self.cal_pt: List[int] = [100,600]#[None, None]

        self.backlighting_level: int = None
        self.backlighting_auto_mode: bool = None
        self.backlighting_sensitivity: int = None

        self.feedback_msg: str = None

    def start_client(self, address: str = None, port: int = None):
        try:
            print(f'\nAttempting to connect to board via port {port}.')
            self.client.connect(address, port)
            print('Connection Successful.')
        except OSError as error:
            if '[Errno 112]' in str(error):
                print('\nConnection Failed. Device Not Detected')
            if '[Errno 107]' in str(error):
                print('\nBluetooth not turn on.')
            else:
                print(error)

    def close_client(self):
        self.client.close()

    def set_default_board_settings(self):
        self.set_sensor_mode(0)  # length measuring mode
        self.set_interface(1)  # FEED
        self.set_backlighting_level(DEFAULT_BACKLIGHTING_LEVEL)
        self.set_stylus_detection_message(False)
        self.set_stylus_settling_delay(DEFAULT_SETTLING_DELAY)
        self.set_stylus_max_deviation(DEFAULT_MAX_DEVIATION)
        self.set_number_of_reading(DEFAULT_NUMBER_OF_READING)

    def query(self, value: str, listen: bool = True):
        """Receive message are located in self.client.buffer"""
        self.client.send(value)
        if listen is True:
            self.client.receive()

    def board_initialization(self):
        self.query('&init#')
        if self.client.buffer == "Rebooting in 2 seconds...":
            self.feedback_msg = self.client.buffer

    def reboot(self):  # FIXME NOT WORKING
        self.query('&rr#')
        if self.client.buffer == "%rebooting":
            self.feedback_msg = self.client.buffer

    def ping(self):
        """This could use for something more useful. Like checking at regular interval if the board is still active:
        """
        self.query('a#')
        if self.client.buffer == '%a:e#':
            self.feedback_msg = 'pong'

    def get_board_stats(self):
        self.query('b#')
        self.board_stats = self.client.buffer
        self.feedback_msg = self.client.buffer  # TODO remove

    def get_battery_level(self):
        self.client.send('&q#')
        self.client.receive()
        self.battery_level = re.findall(r'%q:(-*\d*,\d*)#', self.client.buffer)[0]
        self.feedback_msg = f"Battery: {self.battery_level}%"  # TODO remove

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
        elif self.client.buffer == 'alpha mode activated\r':
            self.sensor_mode = 'alpha'
        elif self.client.buffer == 'shortcut mode activated\r':
            self.sensor_mode = 'shortcut'
        elif self.client.buffer == 'numeric mode activated\r':
            self.sensor_mode = 'numeric'
        else:
            self.feedback_msg = f'Return Error,  {self.client.buffer}'

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
        self.feedback_msg = self.client.buffer  # TODO received %a:e#

    def clear_cal_data(self):
        self.query("&ca#")
        self.feedback_msg = self.client.buffer  # TODO
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
                self.feedback_msg = 'Stylus Status Message Enable'
                self.stylus_status_msg = 'Enable'
            else:
                self.feedback_msg = 'Stylus Status Message Disable'
                self.stylus_status_msg = 'Disable'
        else:
            self.feedback_msg = f'Return Error,  {self.client.buffer}'

    def set_stylus_settling_delay(self, value: int = 1):
        self.query(f"&di,{value}#")
        if self.client.buffer == f"%di:{value}#\r":
            self.stylus_settling_delay = value
            self.feedback_msg = f"Stylus settling delay set to {value}"
        else:
            self.feedback_msg = f'Return Error,  {self.client.buffer}'

    def set_stylus_max_deviation(self, value: int):
        self.query(f"&dm,{value}#")
        if self.client.buffer == f"%dm:{value}#\r":
            self.stylus_max_deviation = value
            self.feedback_msg = f"Stylus max deviation set to {value}"
        else:
            self.feedback_msg = f'Return Error,  {self.client.buffer}'

    def set_number_of_reading(self, value: int = 5):
        self.query(f"&dn,{value}#")
        if self.client.buffer == f"%dn:{value}#\r":
            self.number_of_reading = value
            self.feedback_msg = f"Number of reading set to {value}"
        else:
            self.feedback_msg = f'Return Error,  {self.client.buffer}'

    def check_calibration_state(self):  # TODO, to be tested
        self.query('&u#')
        if self.client.buffer == '%u:0#\r':
            self.feedback_msg = 'Board is not calibrated.'
            self.calibrated = False
        elif self.client.buffer == '%u:1#\r':
            self.feedback_msg = 'Board is calibrated.'
            self.calibrated = True
        else:
            self.feedback_msg = f'Return Error,  {self.client.buffer}'

    def set_calibration_points_mm(self, pt: int, pos: int):
        self.query(f'&{pt}mm,{pos}#')
        if self.client.buffer == f'Cal Pt {pt + 1} set to: {pos}\r':
            self.cal_pt[pt] = pos
            self.feedback_msg = f'Calibration point {pt + 1} set to {pos} mm'
        else:
            self.feedback_msg = f'Return Error,  {self.client.buffer}'

    def calibrate(self, pt: int):
        if self.cal_pt[pt] is not None:
            self.feedback_msg = f'entered calibrate function {pt+1}'
            self.query(f"&{pt + 1}r#")
            self.feedback_msg = f'Calibrating point {pt + 1}: {self.cal_pt[pt]} mm. Touch Stylus ...'
            self.feedback_msg = self.client.buffer
            time.sleep(5)
            if self.client.buffer == f'&Xr#: X={pt + 1}\r':
                msg = ""
                while 'c' not in msg:
                    self.client.receive()
                    msg += self.client.buffer  # FIXME


class Dcs5Controller(Dcs5Interface):
    """
    TODO
    ----
        - Reserve a1 - a2 to map andes F1-F6 action.
        - add a measured function that can be called from andes.
        - Add command to change stylus, change finger stylus offset.


    """

    def __init__(self):
        Dcs5Interface.__init__(self)

        self.is_awake: bool = False
        self.interactive: bool = True
        self.stdscr: CliWindow = None

        self.stylus: str = 'pen'  # [finger/pen]
        self.stylus_offset: str = STYLUS_OFFSET['pen']

        self.board_entry_mode: str = 'center'  # [top, center, bot]
        self.swipe_triggered: bool = False
        self.swipe_value: str = ''

        self.mode_key_activated: bool = False

        self.numpad_storing_mode: bool = False
        self.number_of_numpad_entry: int = ''
        self.selected_command: str = ''
        self.board_setting: bool = False

        self.numpad_buffer: str = ''
        self.numpad_memory: list = []

        self.last_entry: str = ''
        self.out_value: str = None

        self.out = None

    def clear_numpad_buffer(self):
        self.numpad_buffer = ''

    def clear_numpad_memory(self):
        self.numpad_memory = []

    def wake_up_board(self, interactive: bool = True):
        self.interactive = interactive
        self.set_backlighting_level(95)
        self.set_backlighting_auto_mode(False)
        self.is_awake = True

        if self.interactive is True:
            self.feedback_msg = ''
            self.stdscr = CliWindow()
        self.stdscr.update_window(self)

        self.client.clear_socket_buffer()
        while self.is_awake is True:
            self.client.receive()
            self.process_board_output()
            if self.interactive is True:
                self.stdscr.update_window(self)
            self.feedback_msg = ''
            self.out_value = ''

        if self.interactive is True:
            curses.endwin()

    def silence_board(self):
        self.is_awake = False
        self.set_backlighting_level(0)

    def process_board_output(self):
        for msg in self.client.buffer.replace('\r', '').split('#'):
            if msg == "":
                continue
            out = self.decode_buffer(msg)
            self.last_entry = out
            if out is None:
                continue

            if out == 'mode':
                self.trigger_mode_key()
                # DO something with the arrow for lights.

            elif self.mode_key_activated is True:
                if out in XT_KEY_TYPES['mode_function']:
                    self.select_board_setting(out)
                else:
                    if out == 'c1':
                        self.change_stylus()
                    elif out == 'a6':
                        self.silence_board()
                self.trigger_mode_key()

            elif out in XT_KEY_TYPES['function']:
                self.out_value = 'function'+out[1]

            if out in XT_KEY_TYPES['numpad']:
                if self.numpad_storing_mode is True:
                    if self.number_of_numpad_entry > 0:
                        self.process_numpad_entry(out)
                    if self.number_of_numpad_entry == 0:
                        self.numpad_storing_mode = False
                        self.board_setting = True
                else:
                    self.out_value = out

            if self.board_setting is True:
                self.set_board_setting()

            if isinstance(out, tuple):
                if out[0] == 's':
                    self.swipe_value = out[1]
                    if out[1] > SWIPE_THRESHOLD:
                        self.swipe_triggered = True
                if out[0] == 'l':
                    if self.swipe_triggered is True:
                        self.check_for_board_entry_swipe(out[1])
                    else:
                        self.map_board_entry(out[1])

    def trigger_mode_key(self):
        self.mode_key_activated = not self.mode_key_activated

    def select_board_setting(self, value: str):
        # TODO
        self.selected_command = ''
        if value == 'b1':
            self.selected_command = 'set calibration point'
            self.number_of_numpad_entry = 2
            self.clear_numpad_buffer()
            self.clear_numpad_memory()
            self.numpad_storing_mode = True
        if value == 'b2':
            self.number_of_numpad_entry = 0
            self.selected_command = 'calibrate'
            self.board_setting = True
        if self.interactive is True:
            self.stdscr.update_window(self)

    def set_board_setting(self):
        if self.selected_command == 'set calibration point':
            for i in [0, 1]:
                self.set_calibration_points_mm(i, int(self.numpad_memory[i]))
                if self.interactive is True:
                    self.stdscr.update_window(self)
            self.clear_numpad_memory()
        elif self.selected_command == 'calibrate':
            self.client.clear_socket_buffer()
            for i in [0, 1]:
                if self.interactive is True:
                    self.stdscr.update_window(self)
                self.calibrate(i)
        self.board_setting = False
        self.selected_command = ''

    def process_numpad_entry(self, value: str):
        if value == 'enter':
            if len(self.numpad_buffer) == 0:
                self.numpad_buffer = '0'
            self.load_numpad_buffer_to_memory()
            self.number_of_numpad_entry -= 1
        if value == 'del' and len(self.numpad_buffer) > 0:
            self.numpad_buffer = self.numpad_buffer[:-1]
        if value in '.0123456789':
            self.numpad_buffer += value

    def load_numpad_buffer_to_memory(self):
        if '.' in self.numpad_buffer:
            self.numpad_memory.append(float(self.numpad_buffer))
        else:
            self.numpad_memory.append(int(self.numpad_buffer))
        self.clear_numpad_buffer()

    def check_for_board_entry_swipe(self, value: str):
        self.swipe_triggered = False
        if int(value) > 630:
            self.board_entry_mode = 'center'
        elif int(value) > 430:
            self.board_entry_mode = 'bot'
        elif int(value) > 230:
            self.board_entry_mode = 'top'

    def map_board_entry(self, value: int):
        if self.board_entry_mode == 'center':
            self.out_value = value - self.stylus_offset
        else:
            if value < BOARD_KEY_ZERO:
                self.out_value = 'space'
            elif value < BOARD_KEY_EXTENT:
                index = int((value - BOARD_KEY_ZERO) / BOARD_KEY_RATIO)
                self.out_value = BOARD_KEYS_MAP[self.board_entry_mode][index]
            elif value < BOARD_KEY_DEL_LAST:
                self.out_value = 'space'
            else:
                self.out_value = 'del_last'

    def decode_buffer(self, value: str):
        if '%t' in value:
            return None
        elif '%l' in value:
            return 'l', self.get_length(value)
        elif '%s' in value:
            return 's', self.get_swipe(value)
        elif 'F' in value:
            return XT_KEY_MAP[value[2:]]

    def change_stylus(self):
        if self.stylus == 'pen':
            self.stylus = 'finger'
        else:
            self.stylus = 'pen'
        self.stylus_offset = STYLUS_OFFSET[self.stylus]

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

    def raw_output_test(self):
        self.is_awake = True
        while self.is_awake is True:
            self.client.receive()
            if self.client.buffer == 'F,06#\r':
                self.is_awake = False
            print(self.client.buffer)


class CliWindow():
    def __init__(self):
        self.window = curses.initscr()
        curses.nocbreak()
        self.window.keypad(False)
        curses.echo()

    def update_window(self, dcs5_controller: Dcs5Controller):
        sections = ['BACKLIGHT', 'STYLUS', '', '', 'META', 'NUMPAD']
        cols_width = [18, 30, 40]
        lines = [
            [('Level', dcs5_controller.backlighting_level), ('Auto', dcs5_controller.backlighting_auto_mode),
             ("Sensitivity", dcs5_controller.backlighting_sensitivity)],
            [('Mode', dcs5_controller.sensor_mode), ('Type', dcs5_controller.stylus),
             ('Offset', dcs5_controller.stylus_offset)],
            [('Entry', dcs5_controller.board_entry_mode), ('', ''), ('', '')],
            [('Setting Delay', dcs5_controller.stylus_settling_delay),
             ('Max Deviation', dcs5_controller.stylus_max_deviation),
             ('Number of reading', dcs5_controller.number_of_reading)],
            [('Status', dcs5_controller.mode_key_activated), ('Command', dcs5_controller.selected_command),
             ('# values', dcs5_controller.number_of_numpad_entry)],
            [('Storing', dcs5_controller.numpad_storing_mode), ('Buffer', dcs5_controller.numpad_buffer),
             ('Memory', dcs5_controller.numpad_memory)]
        ]

        state_print = f"Mac Address: {dcs5_controller.client.dcs5_address}\n" \
                      + f"Port: {dcs5_controller.client.port}\n" \
                      + f"Device active: {dcs5_controller.is_awake}\n"

        for s, line in zip(sections, lines):
            out = ""
            for col, w in zip(line, cols_width):
                if col[0] == '':
                    out += (w + 2) * ' ' + " | "
                else:
                    out += col[0] + ": " + (str(col[1])).rjust(w - len(col[0])) + " | "
            state_print += s.ljust(10) + "| " + out + '\n'
        state_print += f'Last entry: {dcs5_controller.last_entry}'
        state_print += f'\nLast Board Message: {dcs5_controller.feedback_msg}'
        state_print += f'\nOut_value: {dcs5_controller.out_value}'

        self.window.clear()
        self.window.addstr(state_print)
        self.window.refresh()


def test(scan: bool = False):
    c = Dcs5Controller()
    address = search_for_dcs5board() if scan is True else DCS5_ADDRESS
    c.start_client(address, PORT)
    c.set_default_board_settings()
    c.set_calibration_points_mm(0, 100)
    c.set_calibration_points_mm(0, 600)
    c.wake_up_board()
    return c


if __name__ == "__main__":
    c = test()
    c.close_client()



