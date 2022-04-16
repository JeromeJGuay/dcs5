"""

bigfin adress: 00:06:66:89:E5:FE



%t means that the stylus has touch the board.


Notes
-----
    Big Fin docs: https://bigfinllc.com/wp-content/uploads/Big-Fin-Scientific-Fish-Board-Integration-Guide-V2_0.pdf?fbclid=IwAR0tJMwvN7jkqxgEhRQABS0W3HLLntpOflg12bMEwM5YrDOwcHStznJJNQM
"""

import socket
import bluetooth
import re
import subprocess
from typing import *

DEVICE_NAME = "BigFinDCS5-E5FE"
PORT = 1
PASSKEY = "1111"  # passkey of the device you want to connect

DCS5_ADRESS = "00:06:66:89:E5:FE"
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
# soclket.settimeout(2)


def scan():
    devices = {}
    print("Scanning for bluetooth devices ...")
    _devices = bluetooth.discover_devices(lookup_names = True, lookup_class = True)
    number_of_devices = len(_devices)
    print(number_of_devices," devices found")
    for addr, name, device_class in _devices:
        devices[name] = {'address': addr, 'class': device_class}
        print('\n')
        print("Devices:")
        print(f" Name: {name}")
        print(f" MAC Address: {addr}")
        print(f" Class: {device_class}")
        print('\n')
    return devices


def search_for_dcs5board()->str:
    devices = scan()
    if DEVICE_NAME in devices:
        print(f'{DEVICE_NAME}, found.')
        return devices[DEVICE_NAME]['address']
    else:
        print(f'{DEVICE_NAME}, not found.')
        return None


class Dcs5Client:
    def __init__(self):
        self.socket = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)
        self.dcs5_address: str = None
        self.port: int = None
        self.msg: str = None

    def connect(self, address: str, port: int):
        if address is not None:
            self.dcs5_address = address
        if port is not None:
            self.port = port

        self.socket.connect((self.dcs5_address, self.port))

    def send(self, command: str):
        self.socket.send(bytes(command, ENCODING))

    def receive(self):
        self.msg = str(self.socket.recv(BUFFER_SIZE).decode(ENCODING))

    def close(self):
        self.socket.close()


class Dcs5ClientV2:
    def __init__(self):
        self.socket = bluetooth.BluetoothSocket(bluetooth.RFCOMM)
        self.dcs5_address: str = None
        self.port: int = None
        self.msg: str = None

      #  subprocess.call("kill -9 `pid bluetooth-agent`", shell=True)
      # status = subprocess.call("bluetooth-agent " + PASSKEY + " &", shell=True)

    def connect(self, address: str, port: int):
        if address is not None:
            self.dcs5_address = address
        if port is not None:
            self.port = port
        try:
            self.socket.connect((self.dcs5_address, self.port))
        except bluetooth.BluetoothError as err:
            print(err)
            pass

    def send(self, command: str):
        self.socket.send(bytes(command, ENCODING))

    def receive(self):
        self.msg = str(self.socket.recv(BUFFER_SIZE).decode(ENCODING))

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
        self.client: Dcs5Client = Dcs5ClientV2()

        self.sensor_mode: str = None
        self.stylus_status_msg: str = None
        self.stylus_settling_delay: int = None
        self.stylus_max_deviation: int = None
        self.number_of_reading: int = None

        self.calibrated: bool = None
        self.cal_pt_1: int = None
        self.cal_pt_2: int = None

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
        self.client.send(value)
        if listen is True:
            self.client.receive()

    def ping(self):
        self.query('a#')
        if self.client.msg == '%a:e#':
            print('pong')

    def board_stat(self):
        self.query('b#')
        print(self.client.msg)

    def board_initialization(self):
        self.query('&init#')
        if self.client.msg == "Rebooting in 2 seconds...":
            print(self.client.msg)

    def battery(self):
        self.client.send('&q#')
        self.client.receive()
        battery = re.findall(r"%q:(-*\d*,\d*)#", self.client.msg)[0]
        print(f"Battery: {battery}%")

    def reboot(self): # NOT WORKING
        self.query('&rr#')
        if self.client.msg == "%rebooting":
            print(self.client.msg)

    def set_sensor_mode(self, value):
        """
        0 -> length (length measure mode)
        1 -> alpha (keyboard)
        2 -> shortcut 'shortcut mode activated\r'
        3 -> numeric 'numeric mode activated\r'
        """

        self.client.send(f'&m,{int(value)}#')
        self.client.receive()
        print(self.client.msg)
        if self.client.msg == 'length mode activated\r':
            self.sensor_mode = 'length'
        elif self.client.msg == 'alpha mode activated\r':
            self.sensor_mode = 'alpha'
        elif self.client.msg == 'shortcut mode activated\r':
            self.sensor_mode = 'shortcut'
        elif self.client.msg == 'numeric mode activated\r':
            self.sensor_mode = 'numeric'
        else:

            print('Return Error', self.client.msg)

    def set_interface(self, value: int):
        '''
        FEED seems to enable box key strokes.
        '''
        self.query(f"&fm,{value}#", listen=False)
        if value == 0:
            self.interface = "DCSLinkstream"
        elif value == 1:
            self.interface = "FEED"

    def restore_cal_data(self):
        self.query("&cr,m1,m2,raw1,raw2#")
        print(self.client.msg) # TODO received %a:e#
        # self.calibrated = True

    def clear_cal_data(self):
        self.query("&ca#")
        print(self.client.msg)  # TODO
        self.calibrated = False

    def set_backlighting_level(self, value: int): # NOT WORKING
        """0-95"""
        self.query(f'&o,{value}#', listen=False)
        self.backlighting_level = value

    def set_backlighting_auto_mode(self, value: bool): # NOT WORKING
        self.query(f"&oa,{int(value)}", listen=False)
        self.backlighting_auto_mode = value

    def set_backlighting_sensitivity(self, value: int): # NOT WORKING
        "0-7"
        self.query(f"&os,{int(value)}", listen=False)
        self.backlighting_sensitivity = {True: 'auto', False: 'manual'}

    def set_stylus_detection_message(self, value: bool):
        """
        When disabled (false): %t,(\d+)# are not sent
        """
        self.query(f'&sn,{int(value)}')
        if self.client.msg == f'%sn:{int(value)}#\r': # NOT WORKING
            if value is True:
                print('Stylus Status Message Enable')
                self.stylus_status_msg = 'Enable'
            else:
                print('Stylus Status Message Disable')
                self.stylus_status_msg = 'Disable'
        else:
            print('Return Error', self.client.msg)

    def set_stylus_settling_delay(self, value: int = 1):
        self.query(f"&di,{value}#")
        if self.client.msg == f"%di:{value}#\r":
            self.stylus_settling_delay = value
            print(f"Stylus settling delay set to {value}")
        else:
            print('Return Error', self.client.msg)

    def set_stylus_max_deviation(self, value: int):
        self.query(f"&dm,{value}#")
        if self.client.msg == f"%dm:{value}#\r":
            self.stylus_max_deviation = value
            print(f"Stylus max deviation set to {value}")
        else:
            print('Return Error', self.client.msg)

    def set_number_of_reading(self, value: int = 5):
        self.query(f"&dn,{value}#")
        if self.client.msg == f"%dn:{value}#\r":
            self.number_of_reading = value
            print(f"Number of reading set to {value}")
        else:
            print('Return Error', self.client.msg)

    def check_cal_state(self): # TODO, to be tested
        self.query('&u#')
        if self.client.msg == '%u:0#\r':
            print('Board is not calibrated.')
            self.calibrated = False
        elif self.client.msg == '%u:1#\r':
            print('Board is calibrated.')
            self.calibrated = True
        else:
            print('Return Error', self.client.msg)

    def set_calibration_points_mm(self, cal_pt_1: int = None, cal_pt_2: int = None):
        if cal_pt_1 is not None:
            self.query(f'&1mm,{cal_pt_1}#')
            if self.client.msg == f'Cal Pt 1 set to: {cal_pt_1}\r':
                self.cal_pt_1 = cal_pt_1
                print(f'Calibration point 1 set to {cal_pt_1} mm')
            else:
                print('Return Error', self.client.msg)
            self.query(f'&2mm,{cal_pt_2}#')
        if cal_pt_2 is not None:
            if self.client.msg == f'Cal Pt 2 set to: {cal_pt_2}\r':
                self.cal_pt_2 = cal_pt_2
                print(f'Calibration point 2 set to {cal_pt_2} mm')
            else:
                print('Return Error', self.client.msg)

    def calibrate(self, pt: int):
        pos = {1:self.cal_pt_1, 2:self.cal_pt_2}
        if pt in [1, 2] and self.cal_pt_1 is not None and self.cal_pt_1 is not None:
            print(f'Calibration for point {pt}: {pos[pt]} mm. Touch Stylus ...')
            self.query(f"&{pt}r#")
            if self.client.msg == f'&Xr#: X={pt}\r':
                msg = ""
                while 'c' not in msg:
                    self.client.receive()
                    msg += self.client.msg  # FIXME

            self.calibrated = True

            print('Calibration done.')


class Dcs5Controller(Dcs5Interface):
    def __init__(self):
        Dcs5Interface.__init__(self)

        self.listening: bool = False

        self.wait_for_numpad: bool = False
        self.current_command: str = None
        self.mode_setting: bool = False      
        self.board_command: bool = False
        self.meta_command: bool = False

        self.buffer = ''
        self.numpad_memory: float = 0

        self.previous_command: str = ''

        self.out = None

    def clear_buffer(self):
        self.buffer = ''

    def reset_numpad_memory(self):
        self.numpad_memory = 0

    def start_listening(self):
        self.client.receive() # FIX TO EMPTY SOCKET BUFFER. First stroke is not gonna come in.
        self.listening = True
        self.listen_to_all()

    def listen_to_all(self):
        print('listening...')
        while self.listening is True:
            self.client.receive()

            values = self.client.msg.replace('\r', '').split('#')

            for value in values:
                if value == "":
                    continue
                out = self.decode(value)
                if out is None:
                    continue

                self.check_for_board_command(out)
                if self.board_command is True:
                    self.board_command = False
                elif isinstance(out, tuple):
                    print(out)
                elif self.current_command == 'mode':
                    self.set_mode(out)
                else:
                    self.check_for_meta_command(out)

            self.previous_command = self.client.msg # DEBUG HELP

    def check_for_board_command(self, key):
        self.board_command = True
        if key == 'a6':
            self.listening = False
        elif key == 'a1':
            self.change_backlighting(1)
        elif key == 'b1':
            self.change_backlighting(-1)
        elif key == 'a2':
            print('Sensor Mode: ', self.sensor_mode)
        elif key == 'a3':
            print(self.previous_command)
        else:
            self.board_command = False

    def check_for_meta_command(self, key):
        if key == 'c1':
            print('[Cancel]')
            self.cancel_command()
        elif key == 'mode':
            print('[mode]')
            self.current_command = 'mode'
            self.wait_for_numpad = True
            print('mode setting: Enter a value between 0 and 3.')
        else:
            print('command not used: ', key)

    def cancel_command(self):
        print('Command Cancelled.')
        self.current_command = None
        self.buffer = ""
        self.wait_for_numpad = False
        self.numpad_memory = 0

    def set_mode(self, value):
        self.listen_to_numpad(value)
        if self.wait_for_numpad is False:
            if self.numpad_memory in [0, 1, 2, 3]:
                self.set_sensor_mode(self.numpad_memory)
                self.mode_setting = False
            else:
                print('Error: Mode value must be between 0 and 3.')
              
    def listen_to_numpad(self, value: str):
        if value in '.0123456789':
            self.buffer += value
            print(self.buffer)

        elif value == 'enter' and value != "":
            print('[enter]')
            self.numpad_memory = float(self.buffer)
            self.clear_buffer()
            self.wait_for_numpad = False
            self.mode_setting = False

    def decode(self, value: str):
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









def scan_test():
    address = search_for_dcs5board()
    if address is not None:
        b = Dcs5Interface()
        b.start_client(address, PORT)

    return b


def test():

    #c.start_client(DCS5_ADRESS, PORT)
    #address = search_for_dcs5board()
    #if address is not None:
    c = Dcs5Controller()
#    c.start_client(address, PORT)
    c.start_client(DCS5_ADRESS, PORT)
    c.set_sensor_mode(1)
    c.set_interface(1)
    c.set_backlighting_level(DEFAULT_BACKLIGHTING_LEVEL)
    c.set_stylus_detection_message(False)
    c.set_stylus_settling_delay(10)#DEFAULT_SETTLING_DELAY)
    c.set_stylus_max_deviation(DEFAULT_MAX_DEVIATION)
    c.set_number_of_reading(DEFAULT_NUMBER_OF_READING)

    c.start_listening()



    #b.listen()
    #b.set_calibration_points_mm(0, 600)
    #b.calibrate(1)
    #b.calibrate(2)



if __name__ == "__main__":
    b=test()