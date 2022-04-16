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

    def query(self, value: str, listen: bool = True):
        self.client.send(value)
        #self.client.socket.settimeout(5) #FIXME
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

    def set_mode(self, value:int):
        self.client.send(f'&m,{int}#')
        print(self.client.msg)

    def set_interface(self, value: int):
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

    def change_backlighting(self, value: int):
        if value == 1 and self.backlighting_level < MAX_BACKLIGHTING_LEVEL:
            self.backlighting_level += 15
            if self.backlighting_level > MAX_BACKLIGHTING_LEVEL:
                self.backlighting_level = MIN_BACKLIGHTING_LEVEL
            self.set_backlighting_level(self.backlighting_level)
        if value == -1 and self.backlighting_level > MIN_BACKLIGHTING_LEVEL:
            self.backlighting_level += -15
            if self.backlighting_level < MIN_BACKLIGHTING_LEVEL:
                self.backlighting_level = MIN_BACKLIGHTING_LEVEL
            self.set_backlighting_level(self.backlighting_level)

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

    def listen(self):
        self.client.receive()
        while 1:
            self.client.receive()
            msg_list = self.client.msg.split('#')
            for raw_msg in msg_list:
                msg = raw_msg
                if '%l' in raw_msg:
                    if self.sensor_mode == 'lmm':
                        msg = re.findall(r"%l,(\d+)", raw_msg)[0]
                    elif self.sensor_mode == 'kbm':
                        print(raw_msg)

                elif '%s' in raw_msg:
                    msg = 'swipe ' + raw_msg #FIXME
                elif 'F' in raw_msg:
                    msg = XT_KEY_MAP[raw_msg[2:]]
                    entry = msg
                    if msg == 'a1':
                        self.change_backlighting(1)
                    elif entry == 'b1':
                        self.change_backlighting(-1)
                    elif entry == 'mode':
                        if self.sensor_mode == 'kbm':
                            self.lmm()
                        else:
                            self.kbm()

                    elif msg == 'a6':
                        break




                print(msg)


def scan_test():
    address = search_for_dcs5board()
    if address is not None:
        b = Dcs5Board()
        b.start_client(address, PORT)

    return b


def test():
    b = Dcs5Board()
    b.start_client(DCS5_ADRESS, PORT)
    b.kbm()
    b.set_interface(1)
    b.set_backlighting_level(DEFAULT_BACKLIGHTING_LEVEL)
    b.set_stylus_detection_message(False)
    b.set_stylus_settling_delay(DEFAULT_SETTLING_DELAY)
    b.set_stylus_max_deviation(DEFAULT_MAX_DEVIATION)
    b.set_number_of_reading(DEFAULT_NUMBER_OF_READING)
    b.listen()
    #b.set_calibration_points_mm(0, 600)
    #b.calibrate(1)
    #b.calibrate(2)
    return b

if __name__ == "__main__":
    b=test()