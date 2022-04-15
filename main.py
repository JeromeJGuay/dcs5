"""

bigfin adress: 00:06:66:89:E5:FE

"""

import socket
import bluetooth
import re

PORT = 1
DCS5_ADRESS = "00:06:66:89:E5:FE"
EXIT_COMMAND = "stop"

ENCODING = 'UTF-8'
BUFFER_SIZE = 4096


# soclket.settimeout(2)


class Dcs5Board:
    pass


class Dcs5Client:
    def __init__(self):
        self._socket = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)
        self.dcs5_address: str = None
        self.port: int = None
        self.sensor_mode: str = None
        self.msg: str = None

        self.stylus_status_msg: str = None
        self.stylus_settling_delay: int = None
        self.stylus_max_deviation: int = None
        self.number_of_reading: int = None

    def connect(self, address: str, port: int):
        self.dcs5_address = address
        self.port = port
        self._socket.connect((self.dcs5_address, self.port))
        print(f'Connected to: {self.dcs5_address}.')
        print(f'Socket is connected to port: {self.port}')

    def send(self, command: str):
        self._socket.send(bytes(command, ENCODING))

    def receive(self):
        self.msg = str(self._socket.recv(BUFFER_SIZE).decode(ENCODING))
        return self.msg

    def ask(self, command: str):
        self.send(command)
        print(self.receive())

    def close(self):
        self._socket.close()

    def battery(self):
        self.send('&q#')
        self.receive()
        battery = '/'.join(re.findall(r"%q:(-*)(\d*),(\d*)#", self.msg)[0])
        print(f"Battery: {battery}%")

    def lmm(self):
        'length_measure_mode'
        self.send('&m,0#')
        self.receive()
        print(self.msg)
        if self.msg == r'length mode activated\r':
            self.sensor_mode = 'lmm'

    def kbm(self):
        'keyboard_mode'
        self.send('&m,1#')
        self.receive()
        print(self.msg)
        if self.msg == r'alpha mode activated\r':
            self.sensor_mode = 'kbm'
        else:
            print('Return Error', self.msg)

    def set_stylus_detection(self, value: bool):
        self.ask(f'&sn,{int(value)}')
        if self.msg == fr'%sn,{int(value)}\r':
            if value is True:
                print('Stylus Status Message Enable')
                self.stylus_status_msg = 'Enable'
            else:
                print('Stylus Status Message Disable')
                self.stylus_status_msg = 'Disable'
        else:
            print('Return Error', self.msg)

    def set_stylus_settling_delay(self, value: int = 1):
        self.ask(f"&di,{value}#")
        if self.msg == f"%di,{value}#":
            self.stylus_settling_delay = value
        print('Return Error', self.msg)

    def set_stylus_max_deviation(self, value):
        self.ask(f"&dm,{value}#")
        if self.msg == f"%dm,{value}#":
            self.stylus_max_deviation = value
        print('Return Error', self.msg)


if __name__ == "__main__":
    c = Dcs5Client()
    c.connect(DCS5_ADRESS, PORT)
