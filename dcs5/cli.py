import argparse
import logging
import sys

from dcs5.logger import init_logging
from dcs5.starter import start_dcs5_controller

VALID_COMMANDS = ['stop', 'help', 'restart', 'mute', 'unmute', 'cm', 'mm', 'top','bottom',
                  'length', 'calpt1', 'calpt2', 'calibrate']


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-v",
        "--verbose",
        default="info",
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

    init_logging(stdout_level=args.verbose,
                 write=args.write,
                 file_path=args.file_path,
                 file_level=args.file_verbose,
                 )

    logging.info('Starting dcs5 controller')

    try:
        cli_app()
    except KeyError as err:
        print(err)
        sys.exit()

    logging.info("Exiting")


def cli_app():
    controller = start_dcs5_controller()

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
        elif command == "top":
            controller.change_board_output_mode('top')
        elif command == "bottom":
            controller.change_board_output_mode('bottom')
        elif command == "length":
            controller.change_board_output_mode('length')
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

if __name__ == "__main__":
    main()

