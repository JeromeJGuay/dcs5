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

class Dcs5Client:
    def __init__(self):
        self.socket = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)
        self.dcs5_address: str = None
        self.port: int = None
        self.msg: str = None

    def connect(self, address: str, port: int):
        self.dcs5_address = address
        self.port = port
        self.socket.connect((self.dcs5_address, self.port))
        print(f'Connected to: {self.dcs5_address}.')
        print(f'Socket is connected to port: {self.port}')

    def send(self, command: str):
        self.socket.send(bytes(command, ENCODING))

    def receive(self):
        self.msg = str(self.socket.recv(BUFFER_SIZE).decode(ENCODING))
        return self.msg

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

    def start_client(self, address: str, port: int):
        self.client.connect(address, port)

    def ask(self, command: str):
        self.client.send(command)
        print(self.client.receive())

    def ping(self):
        self.ask('a#')
        if self.client.msg == r'%a:e#\r':
            print('Board communication ok')

    def board_stat(self):
        self.ask('b#')
        print(self.client.msg)

    def board_initialization(self):
        self.ask('&init#')
        if self.client.msg == "Rebooting in 2 seconds...":
            print(self.client.msg)

    def battery(self):
        self.client.send('&q#')
        self.client.receive()
        battery = '/'.join(re.findall(r"%q:(-*)(\d*),(\d*)#", self.client.msg)[0])
        print(f"Battery: {battery}%")

    def reboot(self):
        self.ask('&rr#')
        if self.client.msg == "%rebooting":
            print(self.client.msg)

    def lmm(self):
        'length_measure_mode'
        self.client.send('&m,0#')
        self.client.receive()
        print(self.client.msg)
        if self.client.msg == r'length mode activated\r':
            self.sensor_mode = 'lmm'

    def kbm(self):
        'keyboard_mode'
        self.client.send('&m,1#')
        self.client.receive()
        print(self.client.msg)
        if self.client.msg == r'alpha mode activated\r':
            self.sensor_mode = 'kbm'
        else:
            print('Return Error', self.client.msg)

    def restore_cal_data(self):
        self.ask("&cr,m1,m2,raw1,raw2#")
        print(self.client.msg) # TODO
        # self.calibrated = True

    def clear_cal_data(self):
        self.ask("&ca#")
        print(self.client.msg)  # TODO
        self.calibrated = False

    def set_backlighting_level(self, value: int):
        """0-95"""
        self.ask(f'&o,{value}#')
        print(self.client.msg) # TODO
        self.backlighting_level = value

    def set_backlighting_auto_mode(self, value: bool):
        self.ask(f"&oa,{int(value)}")
        print(self.client.msg) # TODO
        self.backlighting_auto_mode = value

    def set_backlighting_sensitivity(self, value: int):
        "0-7"
        self.ask(f"&os,{int(value)}")
        print(self.client.msg)
        self.backlighting_sensitivity = {True: 'auto', False: 'manual'}


    def set_interface(self, value: int):
        self.ask(f"&fm,{value}#")
        if self.client.msg == "DCSLinkstream Interface Active":
            print(self.client.msg)
            self.interface = "DCSLinkstream"
        elif self.client.msg == "FEED Interface Active":
            print(self.client.msg)
            self.interface = "FEED"
        else:
            print('Return Error', self.client.msg)

    def set_stylus_detection_message(self, value: bool):
        """
        When disabled (false): %t,(\d+)# are not sent
        """
        self.ask(f'&sn,{int(value)}')
        if self.client.msg == fr'%sn,{int(value)}\r':
            if value is True:
                print('Stylus Status Message Enable')
                self.stylus_status_msg = 'Enable'
            else:
                print('Stylus Status Message Disable')
                self.stylus_status_msg = 'Disable'
        else:
            print('Return Error', self.client.msg)

    def set_stylus_settling_delay(self, value: int = 1):
        self.ask(f"&di,{value}#")
        if self.client.msg == f"%di,{value}#":
            self.stylus_settling_delay = value
            print(f"Stylus settling delay set to {value}")
        print('Return Error', self.client.msg)

    def set_stylus_max_deviation(self, value: int):
        self.ask(f"&dm,{value}#")
        if self.client.msg == f"%dm,{value}#":
            self.stylus_max_deviation = value
            print(f"Stylus max deviation set to {value}")
        print('Return Error', self.client.msg)

    def set_number_of_reading(self, value: int = 5):
        self.ask(f"&dn,{value}#")
        if self.client.msg == f"%dn,{value}#":
            self.number_of_reading = value
            print(f"Number of reading set to {value}")
        print('Return Error', self.client.msg)

    def check_cal_state(self):
        self.ask('&u#')
        if self.client.msg == '&u:0#':
            print('Board not calibrated.')
            self.calibrated = True
        elif self.client.msg == '&u:1#':
            print('Board not calibrated.')
            self.calibrated = False
        else:
            print('Return Error', self.client.msg)

    def set_calibration_points_mm(self, cal_pt_1: int = None, cal_pt_2: int = None):
        if cal_pt_1 is not None:
            self.ask(f'&1mm,{cal_pt_1}#')
            if self.client.msg == f'Recognized &1mm,{cal_pt_1}#':
                self.cal_pt_1 = cal_pt_1
                print('Calibration point 1 set. {cal_pt_1} mm')
            else:
                print('Return Error', self.client.msg)
            self.ask(f'&2mm,{cal_pt_2}#')
        if cal_pt_2 is not None:
            if self.client.msg == f'Recognized &2mm,{cal_pt_2}#':
                self.cal_pt_2 = cal_pt_2
                print('Calibration point 2 set. {cal_pt_1} mm')
            else:
                print('Return Error', self.client.msg)

    def calibrate(self, pt: int):
        if pt in [1, 2] and self.cal_pt_1 is not None and self.cal_pt_1 is not None:
            print('Calibration for point {pt}. Touch Stylus ...')
            self.ask("&{pt}r#")
            if self.client.msg == rf'&Xr#: X={pt}\r CalPt {pt}: touch stylus \r':
                self.client.socket.settimeout(10)
                self.client.receive()
                print(self.client.msg)  # TODO

            self.calibrated = True

    def _decode_stylus_status(self):

    def _decode_faceplate_key_pushes(self):



if __name__ == "__main__":
    b = Dcs5Board()
    b.start_client(DCS5_ADRESS, PORT)
