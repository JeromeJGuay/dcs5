"""
June 2022, JeromeJGuay

This module is the entry point for the bash command (dsc5).
From here you can either start the interactive cli app or start the server.
"""
import sys
import argparse

from dcs5.cli_app import cli_app
from dcs5.logger import init_logging
from dcs5.server import start_server



def main():
    parser = argparse.ArgumentParser()
    parent_parser = argparse.ArgumentParser(add_help=False)

    parser.add_argument('-v', '--verbose', type=str, choices=['debug', 'info', 'warning', 'error'], default='error',
                        help='Cli app verbose.')
    parser.add_argument('-w', '--write-log', action='store_true', default=False, help="Flag to save log to dcs5/logs/")

    subparser = parser.add_subparsers(dest='cmd', title='positional arguments')

    cli_parser = subparser.add_parser('cli', parents=[parent_parser])

    cli_parser.add_argument('-c', '--connect', action='store_true', default=False, help='Connect on launch.')

    server_parser = subparser.add_parser('server', parents=[parent_parser])
    server_parser.add_argument('--test', action='store_true', default=False, help='Only run the server.')
    server_parser.add_argument('--host', type=str, default=None, help='Change the host address.')
    server_parser.add_argument('--port', type=int, default=None, help='Change the port.')

    args = parser.parse_args(sys.argv[1:])

    log_path = None

    try:
        if args.cmd == "cli":
            log_path = init_logging(stdout_level=args.verbose, write=args.write_log)
            sys.argv = ['cli_app']
            if args.connect:
                sys.argv += ['-c']
            cli_app()
        elif args.cmd == "server":
            if args.verbose != 'debug':
                log_path = init_logging(stdout_level='info', write=args.write_log)
            else:
                log_path = init_logging(stdout_level='debug', write=args.write_log)
            start_server(start_controller=not args.test, host=args.host, port=args.port)
        else:
            parser.print_help()
    finally:
        if log_path is not None:
            print(f'Log file saved at `{log_path}`')


if __name__ == '__main__':
    main()
