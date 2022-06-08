import argparse
import logging
from dcs5.main import launch_dcs5
from dcs5.logger import init_logging

VALID_COMMANDS = ['stop', 'help', 'restart', 'mute', 'unmute', 'cm', 'mm', 'calpt1', 'calpt2', 'calibrate']


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-v",
        "--verbose",
        default="DEBUG",
        help="Logging level: [debug, info, warning, error, critical]",
    )
    parser.add_argument(
        "-w",
        '--write',
        default=False,
        help='Use this command to write the logging.',
        action='store_true'
    )

    parser.add_argument(
        "-p",
        "--file_path",
        help="Path to where to write the log.",
    )
    parser.add_argument(
        "--file_verbose",
        default="DEBUG",
        help="File logging level: [debug, info, warning, error, critical]"
    )
    args = parser.parse_args()

    init_logging(stdout_level=args.verbose, write=args.write, file_path=args.file_path, file_level=args.file_verbose)

    logging.info('Starting')

    controller = launch_dcs5()

    print('\n\n')
    while 1:
        command = input("(Type `help` to list the commands or `stop` to exit). Enter a command: ")
        if command == "stop":
            controller.close_client()
            break
        elif command == "help":
            print(f"Commands: {VALID_COMMANDS}")
        elif command == "restart":
            controller.restart_client()
        elif command == "mute":
            controller.mute_board()
        elif command == "unmute":
            controller.unmute_board()
        elif command == "cm":
            controller.change_length_units_cm()
        elif command == "mm":
            controller.change_length_units_mm()
        elif command == "calpt1":
            value = input('Enter cal pt 1 value in mm:')
            if value.isnumeric():
                controller.c_set_calibration_points_mm(1, int(value))
            else:
                print('Invalid')
        elif command == "calpt2":
            value = input('Enter cal pt 2 value in mm:')
            if value.isnumeric():
                controller.c_set_calibration_points_mm(1, int(value))
            else:
                print('Invalid')
        elif command == 'calibrate':
            controller.calibrate(1)
            controller.calibrate(2)
        else:
            print(f'Invalid command. Commands: {VALID_COMMANDS}')

    logging.info("Exiting")


if __name__ == "__main__":
    main()

""" Possible error
ESError
OSError: [Errno 107] Transport endpoint is not connected
"""
