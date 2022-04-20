"""
TODO
----
Class to handle interfacing error.



Notes
-----


References
----------
    https://bigfinllc.com/wp-content/uploads/Big-Fin-Scientific-Fish-Board-Integration-Guide-V2_0.pdf?fbclid=IwAR0tJMwvN7jkqxgEhRQABS0W3HLLntpOflg12bMEwM5YrDOwcHStznJJNQM

"""

import socket
import bluetooth
import re
from typing import *
import curses  # Terminal Dynamic Printing

SOCKET_METHOD = ['socket', 'bluetooth'][0]
DEVICE_NAME = "BigFinDCS5-E5FE"
PORT = 1

DCS5_ADDRESS = "00:06:66:89:E5:FE"
EXIT_COMMAND = "stop"

ENCODING = 'UTF-8'
BUFFER_SIZE = 4096

DEFAULT_SETTLING_DELAY = 1  # from 0 to 20
DEFAULT_MAX_DEVIATION = 6  # from 1 to 100
DEFAULT_NUMBER_OF_READING = 5

DEFAULT_BACKLIGHTING_LEVEL = 0
MIN_BACKLIGHTING_LEVEL = 0
MAX_BACKLIGHTING_LEVEL = 95
DEFAULT_BACKLIGHTING_AUTO_MODE = False
DEFAULT_BACKLIGHTING_SENSITIVITY = 0
MIN_BACKLIGHTING_SENSITIVITY = 0
MAX_BACKLIGHTING_SENSITIVITY = 7

UNSOLICITED_MESSAGES = {
    "%t": r"%t,(d+)#",
    "%l": r"%l,(d+)#",
    "%s": r"%s,(d+)#",
    "%d": r"%d,(d+)#",
}

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

KEY_TYPES = {'function': tuple(f'a{i}' for i in range(1, 7)),
             'mode_function': tuple(f'b{i}' for i in range(1, 7)),
             'numpad': tuple(f'{i}' for i in range(1, 9)) + ('.', 'enter', 'del', 'skip'),
             }

SWIPE_THRESHOLD = 30


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
        self.cal_pt: List[int] = [None, None]

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

    def set_default_parameters(self):
        self.set_sensor_mode(0)  # length measuring mode
        self.set_interface(1)  # FEED
        self.set_backlighting_level(DEFAULT_BACKLIGHTING_LEVEL)
        self.set_stylus_detection_message(False)
        self.set_stylus_settling_delay(DEFAULT_SETTLING_DELAY)
        self.set_stylus_max_deviation(DEFAULT_MAX_DEVIATION)
        self.set_number_of_reading(DEFAULT_NUMBER_OF_READING)

    def query(self, value: str, listen: bool = True):
        """Receive message are locatedin self.client.msg"""
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
        # self.calibrated = True

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
        if self.client.buffer == f'Cal Pt {pt + 1} set to: {pos}\r':
            self.cal_pt[pt] = pos
            self.feedback_msg = f'Calibration point {pt + 1} set to {pos} mm'
        else:
            self.feedback_msg = f'Return Error,  {self.client.buffer}'

    def calibrate(self, pt: int):
        if self.cal_pt[pt] is not None:
            self.feedback_msg = f'Calibration for point {pt + 1}: {self.cal_pt[pt]} mm. Touch Stylus ...'
            self.query(f"&{pt + 1}r#")
            if self.client.buffer == f'&Xr#: X={pt + 1}\r':
                msg = ""
                while 'c' not in msg:
                    self.client.receive()
                    msg += self.client.buffer  # FIXME

            self.calibrated = True

            self.feedback_msg = 'Calibration done.'


class Dcs5Controller(Dcs5Interface):
    """
    TODO
    ----
        -Use a1 - a2 to map andes F1-F6 action.
        -numpad, arrows, del enter should be always seeding entry to andes except when mode key is used.
        - mode + key b1 - b6 to change parameters. Change the numpad+arrows+enter+del action mode.
        - add a measured function that can be called from andes.
        - class key into categories.
        - swipe to change from length to character or number or option. The position of the swipe could indicate the mode.
    """

    def __init__(self):
        Dcs5Interface.__init__(self)

        self.active: bool = False

        self.stylus: str = 'pen'  # [finger/pen]
        self.stylus_offset: str = 0

        self.board_entry_mode: str = 'length'  # [top, length, bot]
        self.swipe_triggered: bool = False
        self.swipe_value: str = ''

        self.mode_key_activated: bool = False

        self.numpad_storing_mode: bool = False
        self.number_of_numpad_entry: int = None
        self.selected_setting: str = None

        self.numpad_buffer: str = ''
        self.numpad_memory: list = []

        self.last_entry: str = ''

        self.out = None

    def clear_numpad_buffer(self):
        self.numpad_buffer = ''

    def clear_numpad_memory(self):
        self.numpad_memory = []

    def activate_board(self, interactive: bool = True):
        print('Activating board.')
        self.client.clear_socket_buffer()
        self.active = True
        self.set_backlighting_level(95)
        self.set_backlighting_auto_mode(False)
        stdscr: curses.window = None
        if interactive is True:
            self.feedback_msg = "Board Ready"
            stdscr = curses.initscr()
        while self.active is True:
            if interactive is True:
                interactive_board(stdscr, self)
            self.client.receive()
            self.process_board_output()
        if interactive is True:
            curses.endwin()

    def deactivate_board(self):
        print('Board deactivated')
        self.active = False
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
                if out in KEY_TYPES['mode_function']:
                    self.select_board_setting(out)
                elif out == 'a6':
                    self.deactivate_board()
                else:
                    self.mode_key_activated = False

            elif out in KEY_TYPES['function']:
                #    print('Function out: ', out)
                continue

            if out in KEY_TYPES['numpad']:
                if self.numpad_storing_mode is True:
                    self.process_numpad_entry(out)
                    #        print('Numpad entry: ', out)
                    if self.number_of_numpad_entry == 0:
                        self.set_board_setting()
                else:
                    #        print('numpad out ', out)
                    continue

            elif isinstance(out, tuple):
                if out[0] == 's':
                    self.swipe_value = out[1]
                    if out[1] > SWIPE_THRESHOLD:
                        self.swipe_triggered = True
                if out[0] == 'l':
                    if self.swipe_triggered is True:
                        self.check_for_board_entry_swipe(out[1])
                    else:
                        if self.board_entry_mode == 'length':
                            pass
                        #                print('Board entry', out[1])
                        else:
                            self.map_board_entry(out[1])

            else:
                continue
            #    print('simple out', out)

    def trigger_mode_key(self):
        # print('key mode active')
        if self.mode_key_activated is True:
            self.mode_key_activated = False
            self.numpad_storing_mode = False
            self.selected_setting = None
        else:
            self.mode_key_activated = True

    def select_board_setting(self, value):
        # TODO
        self.clear_numpad_buffer()
        self.clear_numpad_memory()
        self.numpad_storing_mode = True

        if value == 'b1':
            self.number_of_numpad_entry = 2
            self.selected_setting = 'test_setting'

    def set_board_setting(self):
        if self.selected_setting == 'test_setting':
            pass
        #   print(self.numpad_memory)
        self.clear_numpad_memory()
        self.mode_key_activated = False
        self.numpad_storing_mode = False

    def process_numpad_entry(self, value):
        if value == 'enter':
            if len(self.numpad_buffer) == 0:
                self.numpad_buffer = '0'
            self.load_numpad_buffer_to_memory()
        if value == 'del' and len(self.numpad_buffer) > 0:
            self.numpad_buffer = self.numpad_buffer[:-1]
        if value in '.0123456789':
            self.numpad_buffer += value

    def load_numpad_buffer_to_memory(self):
        self.numpad_memory.append(float(self.numpad_buffer))
        self.clear_numpad_buffer()
        self.number_of_numpad_entry -= 1

    def check_for_board_entry_swipe(self, value):
        self.swipe_triggered = False
        if int(value) > 630:
            self.board_entry_mode = 'length'
        elif int(value) > 430:
            self.board_entry_mode = 'bot'
        elif int(value) > 230:
            self.board_entry_mode = 'top'

    def map_board_entry(self, value):
        # TODO
        pass

    def decode_buffer(self, value: str):
        if '%t' in value:
            return None
        elif '%l' in value:
            return 'l', self.get_length(value)
        elif '%s' in value:
            return 's', self.get_swipe(value)
        elif 'F' in value:
            return XT_KEY_MAP[value[2:]]

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
        return re.findall(r"%l,(\d+)", value)[0]

    @staticmethod
    def get_swipe(value: str):
        return int(re.findall(r"%s,(-*\d+)", value)[0])

    def raw_output_test(self):
        self.active = True
        while self.active is True:
            self.client.receive()
            if self.client.buffer == 'F,06#\r':
                self.active = False
            print(self.client.buffer)


def interactive_board(stdscr: curses.window, dcs5_controller: Dcs5Controller):
    sections = ['BACKLIGHT', 'STYLUS', '', '', 'META', 'NUMPAD']
    cols_width = [18, 25, 40]
    lines = [
    [('Level', dcs5_controller.backlighting_level), ('Auto', dcs5_controller.backlighting_auto_mode),
     ("Sensitivity", dcs5_controller.backlighting_sensitivity)],
    [('Mode', dcs5_controller.sensor_mode), ('Type', dcs5_controller.stylus), ('Offset', dcs5_controller.stylus_offset)],
    [('Entry', dcs5_controller.board_entry_mode), ('', ''), ('', '')],
    [('Setting Delay', dcs5_controller.stylus_settling_delay), ('Max Deviation', dcs5_controller.stylus_max_deviation),
     ('Number of reading', dcs5_controller.number_of_reading)],
    [('Status', dcs5_controller.mode_key_activated), ('Command', dcs5_controller.selected_setting),
     ('# values', dcs5_controller.number_of_numpad_entry)],
    [('Storing', dcs5_controller.numpad_storing_mode), ('Buffer', dcs5_controller.numpad_buffer), ('Memory', dcs5_controller.numpad_memory)]
        ]

    state_print = f"Mac Address: {dcs5_controller.client.dcs5_address}\n" \
                  + f"Port: {dcs5_controller.client.port}\n" \
                  + f"Device active: {dcs5_controller.active}\n"

    for s, line in zip(sections, lines):
        out = ""
        for col, w in zip(line, cols_width):
            if col[0] == '':
                out += (w + 4) * '-' + " | "
            else:
                out += col[0] + ": [" + (str(col[1])).rjust(w - len(col[0])) + "] | "
        state_print += s.ljust(10) + "| " + out + '\n'
    state_print += f'Last entry: {dcs5_controller.last_entry}' + '\n'
    state_print += f'\n{dcs5_controller.feedback_msg}'

    stdscr.addstr(0, 0, state_print)
    stdscr.refresh()



def test(scan: bool = False):
    c = Dcs5Controller()

    address = search_for_dcs5board() if scan is True else DCS5_ADDRESS
    c.start_client(address, PORT)
    c.set_default_parameters()
    return c


if __name__ == "__main__":
    c = test()

    c.activate_board()
