import time
import logging
import argparse
import pathlib
from dataclasses import dataclass
from utils import resolve_relative_path, json2dict
from controller import Dcs5Controller
from dcs5 import DEFAULT_SETTINGS_PATH


CLIENT_SETTINGS = json2dict(resolve_relative_path(DEFAULT_SETTINGS_PATH, __file__))['bluetooth']
DEVICE_NAME = CLIENT_SETTINGS["DEVICE_NAME"]
PORT = CLIENT_SETTINGS["PORT"]
DCS5_ADDRESS = CLIENT_SETTINGS["MAC_ADDRESS"]


@dataclass(unsafe_hash=True, init=True)
class BluetoothSetting:
    device_name:str = None
    port: int = None
    mac_address: str = None

    def load_settings(self, filename: str = None):
        settings = json2dict(resolve_relative_path(DEFAULT_SETTINGS_PATH, __file__))['bluetooth']
        if filename is not None:
            if pathlib.Path(filename).exists():
                settings = json2dict(filename) #FIXME
        self.device_name = settings['DEVICE_NAME']
        self.port = settings['PORT']
        self.mac_address = settings['MAC_ADDRESS']


def init_logging(verbose: str, log_path: str, save_log=False):
    log_path = str(resolve_relative_path(log_path, __file__)) + \
               "_" + time.strftime("%y%m%dT%H%M%S", time.gmtime()) + ".log"
    handlers = [logging.StreamHandler()]
    if save_log is True:
        handlers.append(logging.FileHandler(log_path))
    logging.basicConfig(
        level=verbose.upper(),
        format="%(asctime)s {%(threadName)s} [%(levelname)s] %(message)s",
        handlers=handlers
    )
    logging.info('Starting')


def launch_dcs5_board(address):
    controller = Dcs5Controller()
    controller.start_client(address)
    if controller.client_isconnected:
        controller.sync_controller_and_board()
        controller.start_listening()
    return controller


def main(scan: bool = False):
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-v",
        "--verbose",
        default="info",
        help="Provide logging level: [debug, info, warning, error, critical]",
    )
    parser.add_argument(
        '--save_log',
        default=False,
        help='Use this command to save the logging. Use --logfile to specify a path/to/file')

    parser.add_argument(
        "--logfile",
        default='../logs/dcs5_log',
        help="Filename to print the logs to.",
    )
    parser.add_argument(
        "--address",
        default=DCS5_ADDRESS,
        help="Board Mac Address",
    )
    args = parser.parse_args()

    init_logging(args.verbose, args.logfile)

    controller = launch_dcs5_board(args.address)

    return controller


if __name__ == "__main__":
    #    try:
    c = main(scan=False)
#        while True:
#            pass
#    except (KeyboardInterrupt, SystemExit):
#        pass
#    finally:
#        c.close_client()


""" Possible error
ESError
OSError: [Errno 107] Transport endpoint is not connected
"""
