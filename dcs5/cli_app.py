"""
This module contains the code for the cli application.



TODO: catch error if board dcs

OSError: [Errno 107] Transport endpoint is not connected


"""
import click
import click_shell

from dcs5 import VERSION, DEFAULT_DEVICES_SPECIFICATION_FILE, DEFAULT_CONTROLLER_CONFIGURATION_FILE, \
    XT_BUILTIN_PARAMETERS
from dcs5.controller import Dcs5Controller
from dcs5.utils import resolve_relative_path
from dcs5.config import ConfigError
import time


class StatePrompt:
    def __init__(self):
        self._controller: Dcs5Controller = None
        self._debug_mode = False

    def refresh(self, new_controller: Dcs5Controller):
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
                if self._controller.is_listening:
                    msg += click.style(f"Active: ", fg='green')
                    msg += click.style(f"true", bold=True)
                else:
                    msg += click.style(f"Active: ", fg='red')
                    msg += click.style(f"false", bold=True)
                msg += click.style(' | ', bold=True)
                if self._controller.is_sync:
                    msg += click.style(f"Sync: ", fg='green')
                    msg += click.style(f"true", bold=True)
                else:
                    msg += click.style(f"Sync: ", fg='red')
                    msg += click.style(f"false", bold=True)
                msg += click.style(' | ', bold=True)
                if self._controller.internal_board_state.calibrated:
                    msg += click.style(f"Calibrated: ", fg='green')
                    msg += click.style(f"true", bold=True)
                else:
                    msg += click.style(f"Calibrated: ", fg='red')
                    msg += click.style(f"false", bold=True)
                msg += click.style(']\n', bold=True)
                msg += click.style('[', bold=True)
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


def init_dcs5_controller():
    config_path = resolve_relative_path(DEFAULT_CONTROLLER_CONFIGURATION_FILE, __file__)
    devices_specifications_path = resolve_relative_path(DEFAULT_DEVICES_SPECIFICATION_FILE, __file__)
    control_box_parameters_path = resolve_relative_path(XT_BUILTIN_PARAMETERS, __file__)

    return Dcs5Controller(config_path, devices_specifications_path, control_box_parameters_path)


def start_client(controller: Dcs5Controller):
    click.secho('\nConnecting ...', **{'fg': 'red', 'blink': True}, nl=False)
    controller.start_client()
    if controller.client.isconnected:
        click.secho('\rConnecting ... Done', **{'fg': 'green'})
    else:
        click.secho('\rConnecting ... Failed', **{'fg': 'red'})
        click.secho('Device not Found. Check if Bluetooth and the board are turned on.')


def restart_client(controller: Dcs5Controller):
    click.secho('\nRestarting Controller ...', **{'fg': 'red', 'blink': True}, nl=False)
    controller.restart_client()
    if controller.client.isconnected:
        click.secho('\rRestarting Controller ... Done', **{'fg': 'green'})
    else:
        click.secho('\rRestarting Controller ... Failed', **{'fg': 'red'})


def sync_controller(controller: Dcs5Controller):
    click.secho('\nSyncing Board ...', **{'fg': 'red', 'blink': True}, nl=False)
    controller.sync_controller_and_board()
    if controller.is_sync:
        click.secho('\rSyncing Board ... Done', **{'fg': 'green'})
    else:
        click.secho('\rSyncing Board ... Failed', **{'fg': 'red'})


STATE_PROMPT = StatePrompt()
INTRO = f'Dcs5 Controller App. (version {VERSION})'


def close_client(ctx: click.Context):
    if ctx.obj is not None:
        ctx.obj.close_client()


###################################
#### CLI APPLICATION STRUCTURE ####
###################################
@click_shell.shell(prompt=STATE_PROMPT.prompt, on_finished=close_client)
@click.pass_context
def cli_app(ctx: click.Context):
    click.secho(INTRO)

    try:
        ctx.obj = init_dcs5_controller()
    except ConfigError as err:
        click.secho(f'Config Error: {err}', **{'fg': 'red'})
        click.secho(
            f'Configfile\n: {resolve_relative_path(DEFAULT_CONTROLLER_CONFIGURATION_FILE, __file__)}',
            **{'fg': 'white'}
        )
        ctx.abort()

    STATE_PROMPT.refresh(ctx.obj)

    click.secho(f'\nDevice infos :')
    click.secho(f' Name : {ctx.obj.config.client.device_name}')
    click.secho(f' Mac address : {ctx.obj.config.client.mac_address}')

    start_client(ctx.obj)

    if ctx.obj.client.isconnected:
        sync_controller(ctx.obj)
        ctx.obj.start_listening()

    click.echo('')
    click.echo('Type `help` to list commands or `quit` to close the app.')
    click.echo('')

    return ctx.obj


@cli_app.command('activate', help='Use this command if the controller is not active but is connected.')
@click.pass_obj
def activate(obj):
    if obj.client.isconnected:
        obj.start_listening()
    else:
        click.secho('Device not connected', **{'fg': 'red'})


@cli_app.group('units', help='Change output units ...')
def units():
    pass


@units.command('mm', help="to mm.")
@click.pass_obj
def mm(obj: Dcs5Controller):
    obj.change_length_units_mm()


@units.command('cm', help="to cm.")
@click.pass_obj
def cm(obj: Dcs5Controller):
    obj.change_length_units_cm()


@cli_app.command('connect', help='To start the controller and connect the board.')
@click.pass_obj
def connect(obj: Dcs5Controller):
    if not obj.client.isconnected:
        start_client(obj)

    if obj.client.isconnected:
        sync_controller(obj)
        obj.start_listening()


@cli_app.command('restart', help='To restart the controller and connect the board.')
@click.pass_obj
def restart(obj: Dcs5Controller):
    restart_client(obj)
    if obj.client.isconnected:
        sync_controller(obj)
        obj.start_listening()


@cli_app.command('mute', help='To mute the board output.')
@click.pass_obj
def mute(obj: Dcs5Controller):
    obj.mute_board()


@cli_app.command("unmute", help='To mute the board output.')
@click.pass_obj
def unmute(obj: Dcs5Controller):
    obj.unmute_board()


@cli_app.command('sync', help='To sync the controller and the board internal state.')
@click.pass_obj
def sync(obj: Dcs5Controller):
    if obj.client.isconnected:
        sync_controller(obj)
    else:
        click.secho('Syncing impossible, device not Connected.', **{'fg': 'red'})


@cli_app.command('calibrate', help='To calibrate the board. Use the calpts command first to set the calibration points')
@click.pass_obj
def calibrate(obj: Dcs5Controller):
    if obj.client.isconnected:
        if obj.internal_board_state.cal_pt_1 is not None and obj.internal_board_state.cal_pt_2 is not None:
            click.secho(f'\nSet stylus down for point 1: {obj.internal_board_state.cal_pt_1} mm ...', nl=False)
            if obj.calibrate(1) == 1:
                click.secho(f'\rSet stylus down for point 1: {obj.internal_board_state.cal_pt_1} mm ... Successful')
            else:
                click.secho(f'\rSet stylus down for point 1 {obj.internal_board_state.cal_pt_1} mm ... Failed')
            click.secho(f'\nSet stylus down for point 2: {obj.internal_board_state.cal_pt_2}', nl=False)
            if obj.calibrate(2) == 1:
                click.secho(f'\rSet stylus down for point 2 {obj.internal_board_state.cal_pt_2} mm ... Successful')
            else:
                click.secho(f'\rSet stylus down for point 2 {obj.internal_board_state.cal_pt_2} mm ... Failed')
        else:
            click.echo()
            click.secho('Cannot perform calibration, calibration points not set.', **{'fg': 'red'})
    else:
        click.secho('Cannot perform calibration, device not Connected.', **{'fg': 'red'})


@cli_app.command('reload_configs', help='Use to reload the controller configurations.')
@click.pass_obj
def reload_config(obj: Dcs5Controller):
    click.secho('\nReloading Config ...', **{'fg': 'red', 'blink': True}, nl=False)
    try:
        obj.reload_configs()
        click.secho('\rReloading Config ... Done', **{'fg': 'green'})
    except ConfigError as err:
        click.secho('\rReloading Config ... Failed', **{'fg': 'red'})
        click.secho(f'Config Error\n: {err}', **{'fg': 'red'})
        click.secho(f'Configfile\n: {obj.config_path}', **{'fg': 'white'})


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

@cli_app.group('stylus', help='Change stylus ...')
@click.pass_obj
def stylus(obj):
    pass


@stylus.command("finger", help='to finger.')
@click.pass_obj
def finger(obj: Dcs5Controller):
    obj.change_stylus('finger')


@stylus.command("pen", help='to pen.')
@click.pass_obj
def pen(obj: Dcs5Controller):
    obj.change_stylus('pen')


# --- MODE GROUP --- #

@cli_app.group('mode', help='Change input mode ...')
@click.pass_obj
def mode(obj):
    pass


@mode.command("top", help='to top.')
@click.pass_obj
def top(obj: Dcs5Controller):
    obj.change_board_output_mode('top')


@mode.command("bot", help='bottom.')
@click.pass_obj
def bottom(obj: Dcs5Controller):
    obj.change_board_output_mode('bottom')


@mode.command('len', help='to length.')
@click.pass_obj
def length(obj: Dcs5Controller):
    obj.change_board_output_mode('length')


# --- CALPTS GROUP--- #

@cli_app.group('calpts')
def calpts():
    pass


@calpts.command('1', help='To set calibration point 1 values in mm.')
@click.argument('value', type=click.INT, nargs=1)
@click.pass_obj
def calpt1(obj: Dcs5Controller, value):
    if obj.is_listening:
        obj.c_set_calibration_points_mm(1, value)
        time.sleep(0.25)
        click.secho(f'Calibration point 1: {obj.internal_board_state.cal_pt_1} mm', **{'fg': 'green'})
    else:
        click.echo('Cannot calibration points, controller is not active/connected.')
        click.secho('Cannot set calibration points, controller not active/connected', **{'fg': 'red'})


@calpts.command('2', help='To set calibration point 2 values in mm.')
@click.argument('value', type=click.INT, nargs=1)
@click.pass_obj
def calpt2(obj: Dcs5Controller, value):
    if obj.is_listening:
        obj.c_set_calibration_points_mm(2, value)
        time.sleep(0.25)
        click.secho(f'Calibration point 2: {obj.internal_board_state.cal_pt_2} mm', **{'fg': 'green'})
    else:
        click.secho('Cannot set calibration points, controller not active/connected', **{'fg': 'red'})



# --- EDITS GROUP--- #

@cli_app.group('edit', help='To edit the ...')
def edit():
    pass


@edit.command('config', help='controller configuration file.')
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

    reload_config()

    if obj.client.isconnected:
        if click.confirm(click.style(f"Sync Board", fg='blue'), default=True):
            sync_controller(obj)


