import argparse
from dcs5.cli_app import cli_app


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--server', action='store_true', default=False, help='start server.')
    parser.add_argument('--test-server', action='store_true', default=False, help='start server.')
    parser.add_argument('--cli', action='store_true', default=False, help='start cli interface.')

    args, unknownargs = parser.parse_known_args()

    if args.cli is True:
        cli_app(unknownargs)
    elif args.server is True:
        from dcs5.server import start_server
        start_server()
    elif args.test_server is True:
        from dcs5.server import start_server
        start_server(start_controller=False)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
