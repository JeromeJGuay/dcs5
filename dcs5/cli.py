import time
import logging
import argparse
from dataclasses import dataclass
from utils import resolve_relative_path, json2dict
from controller import Dcs5Controller
from dcs5 import DEFAULT_SETTINGS_PATH


settings = json2dict(resolve_relative_path('../src_files/default_settings.json', __file__))


CLIENT_SETTINGS = settings['client_settings']
DEVICE_NAME = CLIENT_SETTINGS["DEVICE_NAME"]
PORT = CLIENT_SETTINGS["PORT"]
DCS5_ADDRESS = CLIENT_SETTINGS["DCS5_ADDRESS"]


@dataclass(unsafe_hash=True, init=True)
class BluetoothSetting:
    device_name:str = None
    port: int = None
    mac_address: str = None

    def load_settings(self, filename):
        json2dict(resolve_relative_path(DEFAULT_SETTINGS_PATH, __file__))


def init_logging(verbose: str, log_path: str):
    log_path = str(resolve_relative_path(log_path, __file__)) + \
               "_" + time.strftime("%y%m%dT%H%M%S", time.gmtime()) + ".log"

    logging.basicConfig(
        level=verbose.upper(),
        format="%(asctime)s {%(threadName)s} [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(log_path),
            logging.StreamHandler()
        ]
    )
    logging.info('Starting')


def launch_dcs5_board(port, address):
    controller = Dcs5Controller()
    controller.start_client(address, port)
    if controller.client_isconnected:
        controller.start_listening()
        controller.sync_controller_and_board()
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
        "--logfile",
        default='../logs/dcs5_log',
        help="Filename to print the logs to.",
    )
    parser.add_argument(
        "--address",
        default=DCS5_ADDRESS,
        help="Board Mac Address",
    )
    parser.add_argument(
        "--port",
        default=PORT,
        help="Board Mac Address",
    )
    args = parser.parse_args()


    init_logging(args.verbose, args.logfile)


    controller = launch_dcs5_board(args.port, args.address)

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
