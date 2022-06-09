#!/home/jeromejguay/anaconda3/bin/dcs5/bin/python
import sys
import click
import click_shell

from dcs5.logger import init_logging
from dcs5.controller import Dcs5Controller
from utils import resolve_relative_path

DEFAULT_CONTROLLER_CONFIGURATION_FILE = "configs/default_configuration.json"
DEFAULT_DEVICES_SPECIFICATION_FILE = "devices_specifications/default_devices_specification.json"
XT_BUILTIN_PARAMETERS = "static/control_box_parameters.json"


def start_dcs5_controller(
        config_path=resolve_relative_path(DEFAULT_CONTROLLER_CONFIGURATION_FILE, __file__),
        devices_specifications_path=resolve_relative_path(DEFAULT_DEVICES_SPECIFICATION_FILE, __file__),
        control_box_parameters_path=resolve_relative_path(XT_BUILTIN_PARAMETERS, __file__)
):
    return Dcs5Controller(
        config_path=config_path,
        devices_specifications_path=devices_specifications_path,
        control_box_parameters_path=control_box_parameters_path
    )


CONTROLLER = start_dcs5_controller()

INTRO = "DCS-5 Controller"


def prompt():
    msg = click.style('[', bold=True)
    msg += click.style(f" Mode: ", fg='red')
    msg += click.style(f"{CONTROLLER.output_mode}", bold=True)
    msg += click.style(' | ', bold=True)
    msg += click.style(f" Units: ", fg='red')
    msg += click.style(f"{CONTROLLER.length_units}", bold=True)
    msg += click.style(' | ', bold=True)
    msg += click.style(f" Stylus: ", fg='red')
    msg += click.style(f"{CONTROLLER.stylus}", bold=True)
    msg += click.style(' ] ', bold=True)
    msg += click.style(f"dcs5 >", fg='blue')

    # return f"(Mode: [{CONTROLLER.output_mode}], Units: [{CONTROLLER.length_units}], Stylus: [{CONTROLLER.stylus}]) dcs5 > "
    return msg


@click_shell.shell(prompt=prompt, intro=INTRO)
@click.option("-v", "--verbose", is_flag=True, default=False)
def main(verbose):
    level = "ERROR"
    if verbose is True:
        level = "DEBUG"
    init_logging(stdout_level=level)
    CONTROLLER.start_client()
    if CONTROLLER.client.isconnected:
        CONTROLLER.reload_configs()
        CONTROLLER.sync_controller_and_board()
        CONTROLLER.start_listening()
    else:
        sys.exit()


@main.command('quit', help='Exits (same as exit)')
def _quit():
    CONTROLLER.close_client()


@main.group('units', help='Change output units.')
def units():
    pass


@units.command('mm', help="To mm.")
def mm():
    CONTROLLER.change_length_units_mm()


@units.command('cm', help="To cm.")
def cm():
    CONTROLLER.change_length_units_cm()


@main.command('restart')
def restart():
    CONTROLLER.restart_client()


@main.command('mute')
def mute():
    CONTROLLER.mute_board()


@main.command("unmute")
def unmute():
    CONTROLLER.unmute_board()


@main.group('mode')
def mode():
    pass


@mode.command("top")
def top():
    CONTROLLER.change_board_output_mode('top')


@mode.command("bottom")
def bottom():
    CONTROLLER.change_board_output_mode('bottom')


@mode.command('length')
def length():
    CONTROLLER.change_board_output_mode('length')


@main.group('calpts')
def calpts():
    pass


@calpts.command('1')
@click.argument('value', type=click.INT, nargs=1)
def calpt1(value):
    CONTROLLER.c_set_calibration_points_mm(1, value)


@calpts.command('2')
@click.argument('value', type=click.INT, nargs=1)
def calpt2(value):
    CONTROLLER.c_set_calibration_points_mm(1, value)


@main.command('calibrate')
def calibrate():
    CONTROLLER.calibrate(1)
    CONTROLLER.calibrate(2)


@main.command('reload_configs')
def reload_config():
    CONTROLLER.reload_configs()


if __name__ == "__main__":
    main()
    CONTROLLER.close_client()
