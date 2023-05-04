import logging
import platform
import socket
import threading
import time

MONITORING_DELAY = 2  # WINDOWS ONLY
BOARD_MSG_ENCODING = 'UTF-8'
BUFFER_SIZE = 1024


class BluetoothClient:
    """RFCOMM ports goes from 1 to 30."""
    min_port = 1
    max_port = 30
    reconnection_delay = 5

    def __init__(self):
        self.mac_address: str = None
        self.port: int = None
        self.socket: socket.socket = None
        self.default_timeout = 0.1
        self._is_connected = False
        self.error_msg = ""
        self.errors = {
            0: 'Socket timeout',
            1: 'No available ports',
            2: 'Device not found',
            3: 'Bluetooth turned off',
            4: 'Connection broken',
            5: 'Device Unavailable',
            6: 'Client closed',
            99: 'Unknown Error',
        }

        self._socket_spam_thread: threading.Thread = None

    @property
    def socket_timeout(self):
        return self.socket.gettimeout()

    @property
    def is_connected(self):
        return self._is_connected

    def set_timeout(self, value: int):
        self.socket.settimeout(value)

    def connect(self, mac_address: str = None, timeout: int = None):
        self.mac_address = mac_address
        timeout = timeout or self.default_timeout
        logging.debug(f'Attempting to connect to board. Timeout: {timeout} seconds')

        for port in range(self.min_port, self.max_port + 1):  # check for all available ports
            self.socket = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)
            self.socket.settimeout(timeout)
            try:
                logging.debug(f'port: {port}')
                self.socket.connect((self.mac_address, port))
                self.port = port
                self._is_connected = True
                logging.debug(f'Connected to port {self.port}')
                logging.debug(f'Socket name: {self.socket.getsockname()}')

                if platform.system() == 'Windows':
                    self.start_connection_spam_thread()
                break

            except PermissionError:
                logging.debug('Client.connect: PermissionError')
                self.error_msg = 'Permission error'
                pass
            except OSError as err:
                if (err_code := self._process_os_error_code(err)) == 1:
                    if port == self.max_port:
                        logging.error('No available ports were found.')
                        self.error_msg = self.errors[err_code]
                else:
                    self.error_msg = self.errors[err_code]
                    break

        self.socket.settimeout(self.default_timeout)

    def send(self, command: str):
        try:
            self.socket.sendall(command.encode(BOARD_MSG_ENCODING))
        except OSError as err:
            logging.debug(f'OSError on sendall')
            self.error_msg = self.errors[self._process_os_error_code(err)]
            self.close()

    def receive(self):
        try:
            return self.socket.recv(BUFFER_SIZE).decode(BOARD_MSG_ENCODING)
        except OSError as err:
            if err_code := self._process_os_error_code(err) != 0:
                self.error_msg = self.errors[err_code]
                self.close()
            return ""

    def clear(self):
        while self.receive() != "":
            continue

    def close(self):
        self.socket.close()
        self._is_connected = False

    def start_connection_spam_thread(self):
        self._socket_spam_thread = threading.Thread(target=self._spam_socket, name='spam', daemon=True)
        self._socket_spam_thread.start()

    def _spam_socket(self):
        """This is to raise a connection OSError if the connection is lost."""
        while self._is_connected:
            self.send(" ")  # A Space is not a recognized command. Thus nothing is return.
            time.sleep(MONITORING_DELAY)

    def _process_os_error_code(self, err) -> int:
        """
        Parameters
        ----------
        err : OS error code.

        Returns
        -------
        0: Socket timeout
        1: Port Unavailable
        2: Device not Found
        3: Bluetooth turned off
        4: Connection broken
        5: Device Unavailable
        6: Client closed.
        99: Unknown Error

        """
        match err.errno:
            case None:
                return 0
            case 9:
                logging.error(f'Bad file descriptor. (err{err.errno})')
                return 6
            case 16:
                logging.error(f'Port unavailable. (err{err.errno})')
                return 1
            case 22:
                logging.error(f'Port does not exist. (err{err.errno})')
                return 1
            case 77:
                logging.error(f'Bad file descriptor. (err{err.errno})')
                return 6
            case 111:
                logging.error(f'Device unavailable. (err{err.errno})')
                return 5
            case 112:
                logging.error(f'Device not found. (err{err.errno})')
                return 2
            case 104:
                logging.error(f'Connection broken. (err{err.errno})')
                return 4
            case 110:
                logging.error(f'Connection broken. (err{err.errno})')
                return 4
            case 112:
                logging.error(f'Device not found. (err{err.errno})')
                return 2
            case 113:
                logging.error(f'Bluetooth turned off. (err{err.errno})')
                return 3
            case 10022:
                logging.error(f'Bluetooth turned off. (err{err.errno})')
                return 3
            case 10038:
                logging.error(f'Bad file descriptor. (err{err.errno})')
                return 6
            case 10048:
                logging.error(f'Device unavailable. (Maybe) (err{err.errno})')
                return 5
            case 10049:
                logging.error(f'Port does not exist. (err{err.errno})')
                return 1
            case 10050:
                logging.error(f'Bluetooth turned off. (err{err.errno})')
                return 3
            case 10053:
                logging.error(f'Connection broken. (err{err.errno})')
                return 4
            case 10060:
                logging.error(f'Device not found. (err{err.errno})')
                return 2
            case 10064:
                logging.error(f'Port {self.port} unavailable. (err{err.errno})')
                return 1
            case _:
                logging.error(f'OSError (new): {err.errno}')
                return 99
