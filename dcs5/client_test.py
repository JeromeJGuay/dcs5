import socket
import logging
import json

# PUT THIS SOMEWHERE ELSE
AUTH_KEY = "99991"
HOST = "127.0.0.1"  # The server's hostname or IP address
PORT = 9999  # The port used by the server

ENCODING = 'UTF-8'
BUFFER_SIZE = 1024

logging.getLogger().setLevel('DEBUG')


class Dcs5Client:

    def __init__(self, host: str, port: int, auth_key: str):
        self.socket: socket.socket = None
        self.host = host
        self.port = port
        self.auth_key = auth_key

    def connect(self, timeout=.05):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.settimeout(timeout)

    def close(self):
        self.socket.close()

    def query(self, command):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.connect((self.host, self.port))
        self.socket.sendall(
            json.dumps({
                'auth': AUTH_KEY,
                'command': command,
            }).encode(ENCODING)
        )
        json_data = json.loads(self.socket.recv(BUFFER_SIZE).decode(ENCODING))
        state = None
        if json_data['auth'] == 1:
            logging.debug('Dcs5Client: Auth Successful')
            if json_data['command'] == 1:
                logging.debug('Dcs5Client: Command Valid')
                self.close()
            state = json_data['state']
        self.socket.close()
        return state

    def ping_server(self):
        return self.query("ping")

    def c_units_mm(self):
        return self.query('units_mm')

    def c_units_cm(self):
        return self.query("units_cm")

    def c_stylus_pen(self):
        return self.query('stylus_pen')

    def c_stylus_finger(self):
        return self.query('stylus_finger')

    def c_mode_top(self):
        return self.query('mode_top')

    def c_mode_length(self):
        return self.query('mode_length')

    def c_mode_bottom(self):
        return self.query('mode_bot')

    def c_mute(self):
        return self.query('mute')

    def c_unmute(self):
        return self.query('unmute')


if __name__ == "__main__":
    client = Dcs5Client(HOST, PORT, AUTH_KEY)
    try:
        print(client.ping_server())
        print(client.c_units_mm())
        print(client.c_units_cm())
        print(client.c_mode_bottom())
        print(client.c_mode_top())
        print(client.c_mode_length())
        print(client.c_stylus_pen())
        print(client.c_stylus_finger())
        print(client.c_mute())
        print(client.c_unmute())
    except Exception as err:
        logging.debug(err)
    finally:
        client.close()
