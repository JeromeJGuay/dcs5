"""
June 2022, JeromeJGuay

This module is the entry point for the bash command (dsc5).
From here you can either start the interactive cli app or start the server.
"""
import argparse

from dcs5.cli_app import cli_app
from dcs5.logger import init_logging
from dcs5.server import start_server
import sys


def main():
    parser = argparse.ArgumentParser()
    parent_parser = argparse.ArgumentParser(add_help=False)

    # parser.add_argument('cli', default=False, help='start cli interface.')
    # parser.add_argument('server', action='store_true', default=False, help='start server and connects to the board.')
    # parser.add_argument('test-server', action='store_true', default=False, help='start server.')

    subparser = parser.add_subparsers(dest='cmd', title='positional arguments')

    cli_parser = subparser.add_parser('cli', parents=[parent_parser])
    cli_parser.add_argument('-v', '--verbose', type=str, choices=['debug', 'info', 'warning', 'error'], default='error', help='Cli app verbose.')
    cli_parser.add_argument('-u', '--user-interface', action='store_true', default=False, help='Only run the server.')
    cli_parser.add_argument('-w', '--write-log', action='store_true', default=False, help='Writes logs')
    #cli_parser.add_argument('-r', '--reconnect', action='store_true', default=False, help='Attempts to reconnects if board is shutdown.')

    server_parser = subparser.add_parser('server', parents=[parent_parser])
    server_parser.add_argument('--test', action='store_true', default=False, help='Only run the server.')
    server_parser.add_argument('--host', type=str, default=None, help='Change the host address.')
    server_parser.add_argument('--port', type=int, default=None, help='Change the port.')

    args = parser.parse_args(sys.argv[1:])

    init_logging(stdout_level=args.verbose, ui=args.user_interface, write=args.write_log)

    if args.cmd == "cli":
        cli_app([])
    elif args.cmd == "server":
        start_server(start_controller=not args.test, host=args.host, port=args.port)
    else:
        parser.print_help()

if __name__ == '__main__':
    main()
