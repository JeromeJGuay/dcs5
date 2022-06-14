#!/home/jeromejguay/anaconda3/bin/dcs5/bin/python
import time
import logging
import click
import click_shell
from flask import Flask

from dcs5 import VERSION
from dcs5.logger import init_logging
from dcs5.controller import Dcs5Controller
from dcs5.utils import resolve_relative_path
from dcs5.config import load_config, ConfigError

DEFAULT_CONTROLLER_CONFIGURATION_FILE = "configs/default_configuration.json"
DEFAULT_DEVICES_SPECIFICATION_FILE = "devices_specifications/default_devices_specification.json"
XT_BUILTIN_PARAMETERS = "static/control_box_parameters.json"

flask_app = Flask(__name__)

@flask_app.route("/")
def runserver():
   print('ok')


class StatePrompt:
    def __init__(self):
        self._controller = start_dcs5_controller()
        self._debug_mode = False

    def update_controller(self, new_controller: Dcs5Controller):
        self._controller = new_controller

    def debug_mode(self):
        self._debug_mode = True

    def prompt(self):
        msg = click.style('[', bold=True)
        if self._debug_mode is True:
            msg += click.style(f"Debug Mode", fg='red')
        else:
            msg += click.style(f"Connected: ", fg='red')
            msg += click.style(f"{self._controller.client.isconnected}", bold=True)
            msg += click.style(' | ', bold=True)
            msg += click.style(f"Mode: ", fg='red')
            msg += click.style(f"{self._controller.output_mode}", bold=True)
            msg += click.style(' | ', bold=True)
            msg += click.style(f"Units: ", fg='red')
            msg += click.style(f"{self._controller.length_units}", bold=True)
            msg += click.style(' | ', bold=True)
            msg += click.style(f"Stylus: ", fg='red')
            msg += click.style(f"{self._controller.stylus}", bold=True)
        msg += click.style('] ', bold=True)
        msg += click.style("(help/exit) ")
        msg += click.style(f"dcs5 > ", fg='blue', bold=True)

        return msg


def start_dcs5_controller(
        config_path=DEFAULT_CONTROLLER_CONFIGURATION_FILE,
        devices_specifications_path=DEFAULT_DEVICES_SPECIFICATION_FILE,
        control_box_parameters_path=XT_BUILTIN_PARAMETERS
):
    config_path = resolve_relative_path(config_path, __file__)
    devices_specifications_path = resolve_relative_path(devices_specifications_path, __file__)
    control_box_parameters_path = resolve_relative_path(control_box_parameters_path, __file__)

    return Dcs5Controller(config_path, devices_specifications_path, control_box_parameters_path)


def ui_interface(controller: Dcs5Controller, ctx: click.Context):
    STATE_PROMPT.update_controller(controller)
    ctx.obj = controller

    ctx.obj.reload_configs()

    click.secho(f'Attempting to connect to device ... ')
    click.secho(f' Name : {ctx.obj.config.client.device_name}')
    click.secho(f' Mac address : {ctx.obj.config.client.mac_address}')
    ctx.obj.start_client()

    if ctx.obj.client.isconnected:
        click.secho('Syncing Board ...', **{'fg': 'red'})
        ctx.obj.sync_controller_and_board()
        ctx.obj.start_listening()
    else:
        click.secho('Device not Found.')
    click.echo('')
    click.echo('Type `help` to list commands or `quit` to close the app.')
    click.echo('')


def debug_interface(controller: Dcs5Controller, context: click.Context):
    STATE_PROMPT.update_controller(controller)
    STATE_PROMPT.debug_mode()
    context.obj = controller
    controller.reload_configs()
    controller.start_client()
    if controller.client.isconnected:
        controller.sync_controller_and_board()
        controller.start_listening()


STATE_PROMPT = StatePrompt()


def close_client(ctx: click.Context):
    ctx.obj.close_client()


#### CLI APPLICATION STRUCTURE ####
@click_shell.shell(prompt=STATE_PROMPT.prompt, on_finished=close_client)
@click.option("-v", "--verbose", type=click.Choice(['info', 'debug', 'warning', 'error']), default='error')
@click.option("-u", "--user_interface", is_flag=True, default=False)
@click.option("-s", "--server", is_flag=True, default=False)
@click.pass_context
def main(ctx, verbose, user_interface, server):
    click.echo(f'Dcs5 Controller App. (version {VERSION})\n')

    init_logging(stdout_level=verbose.upper(), ui=user_interface)

    controller = start_dcs5_controller()

    if server is True:
        runserver()
    elif verbose != "error":
        debug_interface(controller, ctx)
    else:
        ui_interface(controller, ctx)


@main.group('units', help='Change output units.')
def units():
    pass


@units.command('mm', help="Change value output to mm.")
@click.pass_obj
def mm(obj: Dcs5Controller):
    obj.change_length_units_mm()


@units.command('cm', help="Change value output to cm.")
@click.pass_obj
def cm(obj: Dcs5Controller):
    obj.change_length_units_cm()


@main.command('restart')
@click.pass_obj
def restart(obj):
    obj.restart_client()


@main.command('mute')
@click.pass_obj
def mute(obj: Dcs5Controller):
    obj.mute_board()


@main.command("unmute")
@click.pass_obj
def unmute(obj: Dcs5Controller):
    obj.unmute_board()


@main.command('sync')
@click.pass_obj
def sync(obj: Dcs5Controller):
    if obj.client.isconnected:
        obj.sync_controller_and_board()
    else:
        click.echo('Device not Connected.')


@main.command('calibrate')
@click.pass_obj
def calibrate(obj: Dcs5Controller):
    obj.calibrate(1)
    obj.calibrate(2)


@main.command('reload_configs')
@click.pass_obj
def reload_config(obj: Dcs5Controller):
    obj.reload_configs()


@main.command('change_configs')  # TODO group for each configs
@click.argument('filename', type=click.Path(exists=True), nargs=1)
@click.pass_obj
def change_config(obj: Dcs5Controller, filename):
    try:
        load_config(filename)
        obj.config_path = filename
        obj.reload_configs()
    except ConfigError:
        click.echo('Invalid Config')

    if obj.client.isconnected:
        if click.confirm(click.style(f"Sync Board", fg='blue'), default=True):
            obj.sync_controller_and_board()


# --- MODE GROUP --- #

@main.group('mode')
@click.pass_obj
def mode(obj):
    pass


@mode.command("top")
@click.pass_obj
def top(obj: Dcs5Controller):
    obj.change_board_output_mode('top')


@mode.command("bottom")
@click.pass_obj
def bottom(obj: Dcs5Controller):
    obj.change_board_output_mode('bottom')


@mode.command('length')
@click.pass_obj
def length(obj: Dcs5Controller):
    obj.change_board_output_mode('length')


# --- CALPTS GROUP--- #

@main.group('calpts')
def calpts():
    pass


@calpts.command('1')
@click.argument('value', type=click.INT, nargs=1)
@click.pass_obj
def calpt1(obj: Dcs5Controller, value):
    obj.c_set_calibration_points_mm(1, value)


@calpts.command('2')
@click.argument('value', type=click.INT, nargs=1)
@click.pass_obj
def calpt2(obj: Dcs5Controller, value):
    obj.c_set_calibration_points_mm(1, value)


# --- EDITS GROUP--- #

@main.group('edit')
def edit():
    pass


@edit.command('config')
@click.option('-e', '--editor', type=click.STRING, nargs=1, default=None)
@click.pass_obj
def edit_config(obj: Dcs5Controller, editor):
    if editor is not None:
        try:
            click.edit(filename=obj.config_path, editor=editor)
        except click.ClickException:
            click.echo(f'{editor} not found. ')
    else:
        click.edit(filename=obj.config_path)

    try:
        obj.reload_configs()
    except ConfigError:
        logging.info('Invalid Config')

    if obj.client.isconnected:
        if click.confirm(click.style(f"Sync Board", fg='blue'), default=True):
            obj.sync_controller_and_board()


if __name__ == "__main__":
    main()
