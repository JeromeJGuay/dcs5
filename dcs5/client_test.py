# echo-client.py
import socket
import time

ENCODING = 'UTF-8'
BUFFER_SIZE = 1024

HOST = "127.0.0.1"  # The server's hostname or IP address
PORT = 65432  # The port used by the server


class Client:
    def __init__(self):
        self.socket: socket.socket = None
        self.default_timeout = 5
        self.buffer = ""

    def connect(self, host, port):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.connect((host, port))

    def send(self, command: str):
        self.socket.sendall(command.encode(ENCODING))

    def receive(self):
        try:
            self.buffer = self.socket.recv(BUFFER_SIZE).decode(ENCODING)
        except socket.timeout:
            pass

    def chat(self, msg):
        self.send(msg)
        print(self.receive())

    def ping_server(self):
        self.send('hello board')
        self.receive()
        if self.buffer == "hello andes":
            print('Andes said hello.')
            pass

    def say_goodbye(self):
        self.send('goodbye')

    def close(self):
        self.socket.close()


if __name__ == "__main__":
    c = Client()
    # c.connect(HOST, PORT)
    # c.ping_server()
#   # c.say_goodbye()
#   # c.close()
