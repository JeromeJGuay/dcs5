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
DEVICE_NAME = "BigFinDCS5-E5FE"
PORT = 1
DCS5_ADRESS = "00:06:66:89:E5:FE"
EXIT_COMMAND = "stop"

ENCODING = 'UTF-8'
BUFFER_SIZE = 4096

DEFAULT_SETTLING_DELAY = 1  # from 0 to 20
DEFAULT_MAX_DEVIATION = 6  # from 1 to 100
DEFAULT_NUMBER_OF_READING = 5

DEFAULT_BACKLIGHTING_LEVEL = 0
DEFAULT_BACKLIGHTING_AUTO_MODE = False
DEFAULT_BACKLIGHTING_SENSITIVITY = 0

UNSOLICITED_MESSAGES = {
    "%t": r"%t,(d+)#",
    "%l": r"%l,(d+)#",
    "%s": r"%s,(d+)#",
    "%d": r"%d,(d+)#",
}

XT_KEY_MAP = {
    "00": "",
    "01": "",
    "02": "",
    "03": "",
    "04": "",
    "05": "",
    "06": "",
    "07": "",
    "08": "",
    "09": "",
    "10": "",
    "11": "",
    "12": "",
    "13": "",
    "14": "",
    "15": "",
    "16": "",
    "17": "",
    "18": "",
    "19": "",
    "20": "",
    "21": "",
    "22": "",
    "23": "",
    "24": "",
    "25": "",
    "26": "",
    "27": "",
    "28": "",
    "29": "",
    "30": "",
    "31": "",
    "32": "",
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


class Dcs5Board:
    """
    Notes
    -----
    Firmware update command could be added:
        %h,VER,BR#
        see documentations
    """
    def __init__(self):
        self.client: Dcs5Client = Dcs5Client()

        self.sensor_mode: str = None
        self.interface: str = None

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
                print('Connection Failed.')
            else:
                print(error)

    def close_client(self):
        self.client.close()

    def query(self, value: str):
        self.client.send(value)
        self.client.socket.settimeout(5) #FIXME
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
        battery = '/'.join(re.findall(r"%q:(-*)(\d*),(\d*)#", self.client.msg)[0])
        print(f"Battery: {battery}%")

    def reboot(self): # NOT WORKING
        self.query('&rr#')
        if self.client.msg == "%rebooting":
            print(self.client.msg)

    def lmm(self):
        'length_measure_mode'
        self.client.send('&m,0#')
        self.client.receive()
        print(self.client.msg)
        if self.client.msg == 'length mode activated':
            self.sensor_mode = 'lmm'

    def kbm(self):
        """
        FOUR MOD TOTAL:
        2: shortcut mode activated\r
        3: numeric mode activated\r
        """
        'keyboard_mode' #
        self.client.send('&m,1#')
        self.client.receive()
        print(self.client.msg)
        if self.client.msg == 'alpha mode activated\r':
            self.sensor_mode = 'kbm'
        else:
            print('Return Error', self.client.msg)

    def set_interface(self, value: int): # NOT WORKING
        self.query(f"&fm,{value}#")
        if self.client.msg == "DCSLinkstream Interface Active":
            print(self.client.msg)
            self.interface = "DCSLinkstream"
        elif self.client.msg == "FEED Interface Active":
            print(self.client.msg)
            self.interface = "FEED"
        else:
            print('Return Error', self.client.msg)

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
        self.query(f'&o,{value}#')
        print(self.client.msg) # TODO
        self.backlighting_level = value

    def set_backlighting_auto_mode(self, value: bool): # NOT WORKING
        self.query(f"&oa,{int(value)}")
        print(self.client.msg) # TODO No message
        self.backlighting_auto_mode = value

    def set_backlighting_sensitivity(self, value: int): # NOT WORKING
        "0-7"
        self.query(f"&os,{int(value)}")
        print(self.client.msg)
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

    def check_cal_state(self):
        self.query('&u#')
        if self.client.msg == '%u:0#\r': # NOT WOKRING
            print('Board not calibrated.')
            self.calibrated = True
        elif self.client.msg == '%u:1#\r':
            print('Board not calibrated.')
            self.calibrated = False
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
        if pt in [1, 2] and self.cal_pt_1 is not None and self.cal_pt_1 is not None:
            print(f'Calibration for point {pt}. Touch Stylus ...')
            self.query(f"&{pt}r#")
            if self.client.msg == f'&Xr#: X={pt}\r':
                self.client.socket.settimeout(20)
                try:
                    self.client.receive()
                    #CalPt {pt}: touch stylus\r'
                    print(self.client.msg)  # TODO
                except socket.timeout:
                    print('Nothing received')

            self.calibrated = True

    def listen(self):
        self.client.socket.settimeout(10)

        while 1:
            self.client.receive()
            #print(re.findall(r"%l,(\d+)#", self.client.msg))
            print(self.client.msg)


def scan_test():
    address = search_for_dcs5board()
    if address is not None:
        b = Dcs5Board()
        b.start_client(address, PORT)

    return b


def test():
    b = Dcs5Board()
    b.start_client(DCS5_ADRESS, PORT)
    #b.lmm()
    #b.set_stylus_detection_message(True)
    #b.set_stylus_settling_delay(DEFAULT_SETTLING_DELAY)
    #b.set_stylus_max_deviation(DEFAULT_MAX_DEVIATION)
    #b.set_number_of_reading(1)
    #b.set_calibration_points_mm(0, 60)
    #b.calibrate(1)
    #b.calibrate(2)
    return b

if __name__ == "__main__":
    b=test()