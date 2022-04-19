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
import time

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
             'setting': tuple(f'b{i}' for i in range(1, 7)),
             'numpad': tuple(f'{i}' for i in range(1, 9)) + ('.', 'enter', 'del', 'skip'),
             }


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
        self.buffer = str(self.socket.recv(BUFFER_SIZE).decode_buffer(ENCODING))

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
        self.board_stats: str = None
        self.board_interface: str = None

        self.calibrated: bool = None
        self.cal_pt: List[int] = [None, None]

        self.backlighting_level: int = None
        self.backlighting_auto_mode: bool = None
        self.backlighting_sensitivity: int = None

    def start_client(self, address: str = None, port: int = None):
        print('\n')
        try:
            print(f'Attempting to connect to board via port {port}.')
            self.client.connect(address, port)
            print('Connection Successful.')
        except OSError as error:
            if '[Errno 112]' in str(error):
                print('Connection Failed. Device Not Detected')
            if '[Errno 107]' in str(error):
                print('Bluetooth not turn on.')
            else:
                print(error)

    def close_client(self):
        self.client.close()

    def query(self, value: str, listen: bool = True):
        """Receive message are locatedin self.client.msg"""
        self.client.send(value)
        if listen is True:
            self.client.receive()

    def board_initialization(self):
        self.query('&init#')
        if self.client.buffer == "Rebooting in 2 seconds...":
            print(self.client.buffer)

    def reboot(self):  # FIXME NOT WORKING
        self.query('&rr#')
        if self.client.buffer == "%rebooting":
            print(self.client.buffer)

    def ping(self):
        """This could use for something more useful. Like checking at regular interval if the board is still active:
        """
        self.query('a#')
        if self.client.buffer == '%a:e#':
            print('pong')

    def get_board_stats(self):
        self.query('b#')
        self.board_stats = self.client.buffer
        print(self.client.buffer)  # TODO remove

    def get_battery_level(self):
        self.client.send('&q#')
        self.client.receive()
        self.battery_level = re.findall(r'%q:(-*\d*,\d*)#', self.client.buffer)[0]
        print(f"Battery: {self.battery_level}%")  # TODO remove

    def set_sensor_mode(self, value):
        """
        0 -> length (length measure mode)
        1 -> alpha (keyboard)
        2 -> shortcut 'shortcut mode activated\r'
        3 -> numeric 'numeric mode activated\r'
        """

        self.client.send(f'&m,{int(value)}#')
        self.client.receive()
        print(self.client.buffer)
        if self.client.buffer == 'length mode activated\r':
            self.sensor_mode = 'length'
        elif self.client.buffer == 'alpha mode activated\r':
            self.sensor_mode = 'alpha'
        elif self.client.buffer == 'shortcut mode activated\r':
            self.sensor_mode = 'shortcut'
        elif self.client.buffer == 'numeric mode activated\r':
            self.sensor_mode = 'numeric'
        else:

            print('Return Error', self.client.buffer)

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
        print(self.client.buffer)  # TODO received %a:e#
        # self.calibrated = True

    def clear_cal_data(self):
        self.query("&ca#")
        print(self.client.buffer)  # TODO
        self.calibrated = False

    def set_backlighting_level(self, value: int):  # NOT WORKING
        """0-95"""
        self.query(f'&o,{value}#', listen=False)
        self.backlighting_level = value

    def set_backlighting_auto_mode(self, value: bool):  # NOT WORKING
        self.query(f"&oa,{int(value)}", listen=False)
        self.backlighting_auto_mode = value

    def set_backlighting_sensitivity(self, value: int):  # NOT WORKING
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
                print('Stylus Status Message Enable')
                self.stylus_status_msg = 'Enable'
            else:
                print('Stylus Status Message Disable')
                self.stylus_status_msg = 'Disable'
        else:
            print('Return Error', self.client.buffer)

    def set_stylus_settling_delay(self, value: int = 1):
        self.query(f"&di,{value}#")
        if self.client.buffer == f"%di:{value}#\r":
            self.stylus_settling_delay = value
            print(f"Stylus settling delay set to {value}")
        else:
            print('Return Error', self.client.buffer)

    def set_stylus_max_deviation(self, value: int):
        self.query(f"&dm,{value}#")
        if self.client.buffer == f"%dm:{value}#\r":
            self.stylus_max_deviation = value
            print(f"Stylus max deviation set to {value}")
        else:
            print('Return Error', self.client.buffer)

    def set_number_of_reading(self, value: int = 5):
        self.query(f"&dn,{value}#")
        if self.client.buffer == f"%dn:{value}#\r":
            self.number_of_reading = value
            print(f"Number of reading set to {value}")
        else:
            print('Return Error', self.client.buffer)

    def check_calibration_state(self):  # TODO, to be tested
        self.query('&u#')
        if self.client.buffer == '%u:0#\r':
            print('Board is not calibrated.')
            self.calibrated = False
        elif self.client.buffer == '%u:1#\r':
            print('Board is calibrated.')
            self.calibrated = True
        else:
            print('Return Error', self.client.buffer)

    def set_calibration_points_mm(self, pt: int, pos: int):
        if self.client.buffer == f'Cal Pt {pt + 1} set to: {pos}\r':
            self.cal_pt[pt] = pos
            print(f'Calibration point {pt + 1} set to {pos} mm')
        else:
            print('Return Error', self.client.buffer)

    def calibrate(self, pt: int):
        if self.cal_pt[pt] is not None:
            print(f'Calibration for point {pt + 1}: {self.cal_pt[pt]} mm. Touch Stylus ...')
            self.query(f"&{pt + 1}r#")
            if self.client.buffer == f'&Xr#: X={pt + 1}\r':
                msg = ""
                while 'c' not in msg:
                    self.client.receive()
                    msg += self.client.buffer  # FIXME

            self.calibrated = True

            print('Calibration done.')


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

        - make print

           Mac Address :
           Port :
           Device Status : [Awake/Asleep]

           ///------------------------------------------------------------------------------------
           | BACKLIGHT : | Level [50]          | Mode [manual/auto] | Sensitivity [0]            |
           | STYLUS    : | Mode [alpha/length] | Type [finger/pen]  |  Offset [0]                |
           |             | Entry [top/mid/bot] |                    |                            |
           |             | Setting Delay [ 1]  | Max Deviation [06] | Number Of Reading [20]     |
           | META      : | Status [ON/]        | Parameter []       | Values [x/#RequiredValued] |
           | NUMPAD    : | Mode [lock/unlock]  | Buffer [xxxxxxxxx] | Memory [         0]        |
           ------------------------------------------------------------------------------------///
           [Last key stroke], [Board Setting Instruction]


    """

    def __init__(self):
        Dcs5Interface.__init__(self)

        self.active: bool = False

        self.stylus: str = 'pen'  # [finger/pen]
        self.stylus_offset: str = 0

        self.board_entry_mode: str = 'length'  # [top, length, bot]
        self.swipe_triggered: bool = False
        self.swipe_value: str = ''

        self.numpad_storing_mode: bool = False
        self.board_setting_mode: bool = False
        self.number_of_numpad_entry: int = None
        self.selected_setting: str = None

        self.numpad_buffer: str = ''
        self.numpad_memory: list = []

        self.previous_command: str = ''

        self.out = None

    def clear_numpad_buffer(self):
        self.numpad_buffer = ''

    def clear_numpad_memory(self):
        self.numpad_memory = []

    def activate_board(self):
        self.client.clear_socket_buffer()
        self.active = True
        print('The Board is Active')
        while self.active is True:
            self.client.receive()
            self.process_board_output()
            self.previous_command = self.client.buffer  # DEBUG HELP

    def process_board_output(self):
        for msg in self.client.buffer.replace('\r', '').split('#'):
            if msg == "":
                continue
            out = self.decode_buffer(msg)
            if out is None:
                continue

            if out == 'mode':
                self.trigger_board_setting_mode()
                # DO something with the arrow for lights.

            elif out in KEY_TYPES['function']:
                print('Function out: ', out)

            elif out in KEY_TYPES['setting']:
                if self.board_setting_mode is True:
                    self.select_board_setting(out)
                    print('Board setting', out)

            elif out in KEY_TYPES['numpad']:
                if self.numpad_storing_mode is True:
                    self.process_numpad_entry(out)
                    print('Numpad entry: ', out)
                    if self.number_of_numpad_entry == 0:
                        self.set_board_setting()
                else:
                    print('numpad out ', out)
            elif isinstance(out, tuple):
                if out[0] == 's':
                    print('Swipe value', out[1])
                    self.swipe_value = out[1]
                    if out[1] > 0:
                        self.swipe_triggered = True
                if out[0] == 'l':
                    if self.swipe_triggered is True:
                        self.check_for_board_entry_swipe(out[1])
                    else:
                        if self.board_entry_mode == 'length':
                            print('Board entry', out[1])
                        else:
                            self.map_board_entry(out[1])

            else:
                print('simple out', out)

    def trigger_board_setting_mode(self):
        if self.board_setting_mode is True:
            self.board_setting_mode = False
            self.numpad_storing_mode = False
        else:
            self.board_setting_mode = True

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
            print(self.numpad_memory)
        self.clear_numpad_memory()
        self.board_setting_mode = False
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
        # TODO
        self.swipe_triggered = False
        print('Swipe position: ', value)
        self.board_entry_mode = 'length'  # TODO

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
            print('BackLighting increased')
        if value == -1 and self.backlighting_level > MIN_BACKLIGHTING_LEVEL:
            self.backlighting_level += -15
            if self.backlighting_level < MIN_BACKLIGHTING_LEVEL:
                self.backlighting_level = MIN_BACKLIGHTING_LEVEL
            self.set_backlighting_level(self.backlighting_level)
            print('BackLighting decreased')

    @staticmethod
    def get_length(value: str):
        return re.findall(r"%l,(\d+)", value)[0]

    @staticmethod
    def get_swipe(value: str):
        return int(re.findall(r"%s,(-*\d+)", value)[0])


def test(scan: bool = False):
    c = Dcs5Controller()

    address = search_for_dcs5board() if scan is True else DCS5_ADDRESS

    c.start_client(address, PORT)
    c.set_sensor_mode(1)
    c.set_interface(1)
    c.set_backlighting_level(DEFAULT_BACKLIGHTING_LEVEL)
    c.set_stylus_detection_message(True)
    c.set_stylus_settling_delay(50)  # DEFAULT_SETTLING_DELAY)
    c.set_stylus_max_deviation(DEFAULT_MAX_DEVIATION)
    c.set_number_of_reading(DEFAULT_NUMBER_OF_READING)

    c.activate_board()

    return c

    # b.listen()
    # b.set_calibration_points_mm(0, 0)
    # b.set_calibration_points_mm(1, 600)
    # b.calibrate(0)
    # b.calibrate(1)


if __name__ == "__main__":
    c = test()
