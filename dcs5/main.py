import argparse
from dcs5.cli_app import cli_app
from dcs5.server import start_server


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--server', action='store_true', default=False, help='Start cli app')
    parser.add_argument('--cli', action='store_true', default=False, help='start server')

    args, unknownargs = parser.parse_known_args()

    if args.cli is True:
        cli_app(unknownargs)
    elif args.server is True:
        start_server()
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
