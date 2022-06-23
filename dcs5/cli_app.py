"""
This module contains the code for the cli application.
"""
import logging
import click
import click_shell

from dcs5 import VERSION, DEFAULT_DEVICES_SPECIFICATION_FILE, DEFAULT_CONTROLLER_CONFIGURATION_FILE, \
    XT_BUILTIN_PARAMETERS
from dcs5.logger import init_logging
from dcs5.controller import Dcs5Controller
from dcs5.utils import resolve_relative_path
from dcs5.config import load_config, ConfigError


class StatePrompt:
    def __init__(self):
        self._controller: Dcs5Controller = None
        self._debug_mode = False

    def update_controller(self, new_controller: Dcs5Controller):
        self._controller = new_controller

    def debug_mode(self):
        self._debug_mode = True

    def prompt(self):
        msg = ""
        if self._controller is not None:
            msg += click.style('[', bold=True)
            if self._debug_mode is True:
                msg += click.style(f"Debug Mode", fg='red')
            else:
                if self._controller.client.isconnected:
                    msg += click.style(f"Connected: ", fg='green')
                    msg += click.style(f"true", bold=True)
                else:
                    msg += click.style(f"Connected: ", fg='red')
                    msg += click.style(f"false", bold=True)
                msg += click.style(' | ', bold=True)
                if self._controller.internal_board_state.calibrated:
                    msg += click.style(f"Calibrated: ", fg='green')
                    msg += click.style(f"true", bold=True)
                else:
                    msg += click.style(f"Calibrated: ", fg='red')
                    msg += click.style(f"false", bold=True)
                msg += click.style(' | ', bold=True)
                if self._controller.is_sync:
                    msg += click.style(f"Sync: ", fg='green')
                    msg += click.style(f"true", bold=True)
                else:
                    msg += click.style(f"Sync: ", fg='red')
                    msg += click.style(f"false", bold=True)
                msg += click.style(']\n', bold=True)
                msg += click.style('[', bold=True)
                #msg += click.style(' | ', bold=True)
                msg += click.style(f"Mode: ", fg='white')
                msg += click.style(f"{self._controller.output_mode}", bold=True)
                msg += click.style(' | ', bold=True)
                msg += click.style(f"Units: ", fg='white')
                msg += click.style(f"{self._controller.length_units}", bold=True)
                msg += click.style(' | ', bold=True)
                msg += click.style(f"Stylus: ", fg='white')
                msg += click.style(f"{self._controller.stylus}", bold=True)
                msg += click.style(' | ', bold=True)
                msg += click.style(f"Muted: ", fg='white')
                msg += click.style(f"{str(self._controller.is_muted).lower()}", bold=True)
            msg += click.style(']\n', bold=True)
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


STATE_PROMPT = StatePrompt()
INTRO = f'Dcs5 Controller App. (version {VERSION})'


def close_client(ctx: click.Context):
    if ctx.obj is not None:
        ctx.obj.close_client()


#### CLI APPLICATION STRUCTURE ####
@click_shell.shell(prompt=STATE_PROMPT.prompt, on_finished=close_client)
@click.option("-v", "--verbose", type=click.Choice(['info', 'debug', 'warning', 'error']), default='error')
@click.option("-u", "--user_interface", is_flag=True, default=False)
@click.pass_context
def cli_app(ctx, verbose, user_interface):
    click.secho(INTRO)
    init_logging(stdout_level=verbose.upper(), ui=user_interface)

    ctx.obj = start_dcs5_controller()
    STATE_PROMPT.update_controller(ctx.obj)

    click.secho(f'\nDevice infos :')
    click.secho(f' Name : {ctx.obj.config.client.device_name}')
    click.secho(f' Mac address : {ctx.obj.config.client.mac_address}')
    click.secho('\nConnecting ...', **{'fg': 'red', 'blink': True}, nl=False)
    ctx.obj.start_client()
    click.secho('\rConnecting ... Done', **{'fg': 'green'})

    if ctx.obj.client.isconnected:
        click.secho('\nSyncing Board ...', **{'fg': 'red', 'blink': True}, nl=False)
        ctx.obj.sync_controller_and_board()
        click.secho('\rSyncing Board ... Done', **{'fg': 'green'})
        ctx.obj.start_listening()
    else:
        click.secho('Device not Found.')

    click.echo('')
    click.echo('Type `help` to list commands or `quit` to close the app.')
    click.echo('')


@cli_app.group('units', help='Change output units.')
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


@cli_app.command('restart')
@click.pass_obj
def restart(obj):
    click.secho('\nRestarting Controller ...', **{'fg': 'red', 'blink': True}, nl=False)
    obj.restart_client()
    click.secho('\rRestarting Controller ... Done', **{'fg': 'green'})


@cli_app.command('mute')
@click.pass_obj
def mute(obj: Dcs5Controller):
    obj.mute_board()


@cli_app.command("unmute")
@click.pass_obj
def unmute(obj: Dcs5Controller):
    obj.unmute_board()


@cli_app.command("")
@click.pass_obj
def unmute(obj: Dcs5Controller):
    obj.unmute_board()


@cli_app.command('sync')
@click.pass_obj
def sync(obj: Dcs5Controller):
    if obj.client.isconnected:
        click.secho('Syncing Board ...', **{'fg': 'red', 'blink': True}, nl=False)
        obj.sync_controller_and_board()
        click.secho('\rSyncing Board ... Done', **{'fg': 'green'})
    else:
        click.echo('Device not Connected.')


@cli_app.command('calibrate')
@click.pass_obj
def calibrate(obj: Dcs5Controller):
    click.secho('Set stylus down for point 1 ...', nl=False)
    if obj.calibrate(1) == 1:
        click.secho('\rSet stylus down for point 1 ... Successful', nl=False)
    else:
        click.secho('\rSet stylus down for point 1 ... Failed', nl=False)
    click.secho('Set stylus down for point 2.', nl=False)
    if obj.calibrate(2) == 1:
        click.secho('\rSet stylus down for point 2 ... Successful', nl=False)
    else:
        click.secho('\rSet stylus down for point 2 ... Failed', nl=False)


@cli_app.command('reload_configs')
@click.pass_obj
def reload_config(obj: Dcs5Controller):
    click.secho('\nReloading Config ...', **{'fg': 'red', 'blink': True}, nl=False)
    obj.reload_configs()
    click.secho('\rReloading Config ... Done', **{'fg': 'green'})


# @cli_app.command('change_configs')
# @click.argument('filename', type=click.Path(exists=True), nargs=1, help='Path to controller_config')
# @click.pass_obj
# def change_config(obj: Dcs5Controller, filename):
#     try:
#         load_config(filename)
#         obj.config_path = filename
#         obj.reload_configs()
#     except ConfigError:
#         click.echo('Invalid Config')
#
#     if obj.client.isconnected:
#         if click.confirm(click.style(f"Sync Board", fg='blue'), default=True):
#             obj.sync_controller_and_board()

# --- Stylus GROUP --- #

@cli_app.group('stylus')
@click.pass_obj
def stylus(obj):
    pass


@stylus.command("finger")
@click.pass_obj
def finger(obj: Dcs5Controller):
    obj.change_stylus('finger')


@stylus.command("pen")
@click.pass_obj
def pen(obj: Dcs5Controller):
    obj.change_stylus('pen')


# --- MODE GROUP --- #

@cli_app.group('mode')
@click.pass_obj
def mode(obj):
    pass


@mode.command("top")
@click.pass_obj
def top(obj: Dcs5Controller):
    obj.change_board_output_mode('top')


@mode.command("bot")
@click.pass_obj
def bottom(obj: Dcs5Controller):
    obj.change_board_output_mode('bottom')


@mode.command('len')
@click.pass_obj
def length(obj: Dcs5Controller):
    obj.change_board_output_mode('length')


# --- CALPTS GROUP--- #

@cli_app.group('calpts')
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

@cli_app.group('edit')
def edit():
    pass


@edit.command('config')
@click.option('-e', '--editor', type=click.STRING, nargs=1, default=None,
              help='Text Editor the use. Otherwise, uses system default.')
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
            click.secho('\nSyncing Board ...', **{'fg': 'red', 'blink': True}, nl=False)
            obj.sync_controller_and_board()
            click.secho('\rSyncing Board ... Done', **{'fg': 'green'})
