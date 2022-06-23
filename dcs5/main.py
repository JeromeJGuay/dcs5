"""
June 2022, JeromeJGuay

This module is the entry point for the bash command (dsc5).
From here you can either start the interactive cli app or start the server.
"""
import argparse
from dcs5.cli_app import cli_app
import sys


def main():
    parser = argparse.ArgumentParser()
    parent_parser = argparse.ArgumentParser(add_help=False)

    # parser.add_argument('cli', default=False, help='start cli interface.')
    # parser.add_argument('server', action='store_true', default=False, help='start server and connects to the board.')
    # parser.add_argument('test-server', action='store_true', default=False, help='start server.')

    subparser = parser.add_subparsers(dest='cmd', title='positional arguments')

    cli_parser = subparser.add_parser('cli', parents=[parent_parser])
    cli_parser.add_argument('-v', '--verbose', nargs=1, type=str, choices=['info', 'debug', 'warning', 'error'], default='error', help='Cli app verbose.')
    cli_parser.add_argument('-u', '--user-interface', action='store_true', default=False, help='Only run the server.')

    server_parser = subparser.add_parser('server', parents=[parent_parser])
    server_parser.add_argument('--test', action='store_true', default=False, help='Only run the server.')
    server_parser.add_argument('--host', nargs=1, type=str, default=None, help='Change the host address.')
    server_parser.add_argument('--port', nargs=1, type=int, default=None, help='Change the port.')

    args = parser.parse_args(sys.argv[1:])

    if args.cmd == "cli":
        cli_args = ['-v',  args.verbose] + ['-u'] if args.user_interface else []
        cli_app(cli_args)
    elif args.cmd == "server":
        from dcs5.server import start_server
        start_server(start_controller=not args.test, host=args.host, port=args.port)
    else:
        parser.print_help()

if __name__ == '__main__':
    main()
