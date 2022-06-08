import argparse
import logging
from dcs5.main import launch_dcs5
from dcs5.logger import init_logging


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-v",
        "--verbose",
        default="info",
        help="Logging level: [debug, info, warning, error, critical]",
    )
    parser.add_argument(
        "-w"
        '--write',
        default=False,
        help='Use this command to write the logging.')

    parser.add_argument(
        "-p"
        "--file_path",
        help="Path to where to write the log.",
    )
    parser.add_argument(
        "--file_level",
        help="File logging level: [debug, info, warning, error, critical]"
    )
    args = parser.parse_args()

    init_logging(verbose=args.verbose, write=args.write, file_path=args.file_path, file_level=args.file_level)

    logging.info('Starting')

    launch_dcs5()


if __name__ == "__main__":
    main()


""" Possible error
ESError
OSError: [Errno 107] Transport endpoint is not connected
"""
