"""

- VerticalSeparator(pad=None)

- Use Popup for printing error. (bt device not found etc)


sg.UserSettings('my_config.ini', use_config_file=True, convert_bools_and_none=True)
sg.user_settings_filename(filename='DaysUntil.json') # NOT NEEDED
theme = sg.user_settings_get_entry('-theme-', 'Dark Gray 13')
sg.user_settings_set_entry('-theme-', my_new_theme)

TODO:
- Layout to display Last Input/Command.
- Menu, Help to show docs
- Test on Windows
"""
import os
from pathlib import Path
import shutil
import logging
import click
import webbrowser

import PySimpleGUI as sg
import pyautogui as pag

from dcs5.logger import init_logging, get_multiline_handler

from dcs5.controller_configurations import ConfigError

from dcs5 import VERSION, \
    SERVER_CONFIGURATION_FILE_NAME, \
    CONTROLLER_CONFIGURATION_FILE_NAME, \
    DEVICES_SPECIFICATION_FILE_NAME, \
    CONTROL_BOX_PARAMETERS_FILE_NAME, \
    DEFAULT_SERVER_CONFIGURATION_FILE, \
    DEFAULT_CONTROLLER_CONFIGURATION_FILE, \
    DEFAULT_DEVICES_SPECIFICATION_FILE, \
    DEFAULT_CONTROL_BOX_PARAMETERS, \
    CONFIG_FILES_PATH

from dcs5.controller import Dcs5Controller

if os.environ.get('EDITOR') == 'EMACS':
    print('Text editor changed.')
    os.environ.update({'EDITOR': 'pluma'})  # FIXME


def scale_font(font_size: int) -> int:
    monitor_width, monitor_height = pag.size()
    return int(font_size * monitor_height / 1080)


SMALL_FONT = f'Courier {scale_font(8)}'

REG_FONT = f'Courier {scale_font(10)}'

TAB_FONT = f'Courier {scale_font(12)}'

HEADER_FONT = f'Courier {scale_font(20)}'

CIRCLE = '\u2B24'

LED_SIZE = f'Courier {scale_font(12)}'

ENABLED_BUTTON_COLOR = ('black', "light blue")
DISABLED_BUTTON_COLOR = ('gray', "light grey")

LOGO = '../static/bigfin_logo.png'
LOADING = '../static/circle-loading-gif.gif'


def main():
    init_logging()
    run()


def init_dcs5_controller(configs_path: str):
    controller_config_path = Path(configs_path).joinpath(CONTROLLER_CONFIGURATION_FILE_NAME)
    devices_specifications_path = Path(configs_path).joinpath(DEVICES_SPECIFICATION_FILE_NAME)
    control_box_parameters_path = Path(configs_path).joinpath(CONTROL_BOX_PARAMETERS_FILE_NAME)

    if not Path(configs_path).exists():
        new_configs_path = create_new_configs()
        sg.user_settings()['configs_path'] = new_configs_path

    else:
        check_config_integrity(
            controller_config_path=controller_config_path,
            devices_specifications_path=devices_specifications_path,
            control_box_parameters_path=control_box_parameters_path
        )

    try:
        controller = Dcs5Controller(controller_config_path, devices_specifications_path, control_box_parameters_path)
        logging.debug('Controller initiated.')
        return controller
    except ConfigError:
        logging.debug('ConfigError while initiating controller.')
        sg.popup_ok(
            'Error in the configurations files.\nConfiguration files not loaded.',
            title='Config Error',
            keep_on_top=True,
        )
        sg.user_settings()['configs_path'] = None
        return None


def check_config_integrity(controller_config_path, devices_specifications_path, control_box_parameters_path):
    if not controller_config_path.exists():
        sg.popup_ok(
            f'`controller_config.json` was missing from the directory: {controller_config_path.parent}. One was created.',
            title='Missing file', keep_on_top=True)
        shutil.copyfile(DEFAULT_CONTROLLER_CONFIGURATION_FILE, controller_config_path)
    if not devices_specifications_path.exists():
        sg.popup_ok('`devices_specifications.json` was missing from the directory. One was created.',
                    title='Missing file', keep_on_top=True)
        shutil.copyfile(DEFAULT_DEVICES_SPECIFICATION_FILE, devices_specifications_path)
    if not control_box_parameters_path.exists():
        shutil.copyfile(DEFAULT_CONTROL_BOX_PARAMETERS, control_box_parameters_path)
        sg.popup_ok(
            f'`devices_specifications.json` was missing from the directory {control_box_parameters_path.parent}. One was created.',
            title='Missing file', keep_on_top=True)


def load_user_settings():
    sg.user_settings_load()
    logging.debug(f'User Settings: {sg.user_settings()}')
    if 'configs_path' not in sg.user_settings():
        sg.user_settings().update({'configs_path': None}),
    sg.user_settings().update({'previous_config_path': None})


def save_user_settings():
    sg.user_settings().pop('previous_config_path')
    sg.user_settings_save()

DEVICE_LAYOUT_PADDING = 20

def make_window():
    device_layout = [[
        sg.Frame(
            'Device', [
                [sg.Text(dotted(" Name", 18), pad=(0, 0), font=REG_FONT),
                 sg.Text(dotted("N\A ", DEVICE_LAYOUT_PADDING, 'right'), font=REG_FONT, p=(0, 0), key='-NAME-')],
                [sg.Text(dotted(" MAC address", 18), pad=(0, 0), font=REG_FONT),
                 sg.Text(dotted("N\A", DEVICE_LAYOUT_PADDING, 'right'), font=REG_FONT, p=(0, 0), key='-MAC-')],
                [sg.Text(dotted(" Port (Bt Channel)", 18), pad=(0, 0), font=REG_FONT),
                 sg.Text(dotted("N\A ", DEVICE_LAYOUT_PADDING, 'right'), font=REG_FONT, p=(0, 0), key='-PORT-')]
            ],
            font=TAB_FONT
        )
    ]]
    ###
    connection_layout = [
        [sg.Text(' Connected', font=REG_FONT), led(key='-CONNECTED_LED-')],
        [ibutton('Connect', size=(12, 1), key='-CONNECT-')]]
    activate_layout = [
        [sg.Text(' Activated', font=REG_FONT), led(key='-ACTIVATED_LED-')],
        [ibutton('Activate', size=(12, 1), key='-ACTIVATE-')]]
    mute_layout = [
        [sg.Text('  Muted', font=REG_FONT), led(key='-MUTED_LED-')],
        [ibutton('Mute', size=(12, 1), key='-MUTE-')]]

    restart_layout = [sg.Push(),
                      sg.Button('Restart', size=(12, 1),
                                font=REG_FONT,
                                pad=(0, 1),
                                button_color=('white', 'red3'),
                                border_width=1,
                                disabled_button_color=DISABLED_BUTTON_COLOR,
                                key='-RESTART-',
                                )]
    _status_layout = col([connection_layout, activate_layout, mute_layout])
    status_layout = [[sg.Frame('Status', [_status_layout, restart_layout], font=TAB_FONT, expand_x=True)]]
    ###
    _sync_layout = [
        [sg.Text('Synchronized', font=REG_FONT), led(key='-SYNC_LED-')],
        [ibutton('Synchronize', size=(15, 1), key='-SYNC-'), ]]
    sync_layout = [[sg.Frame('Synchronize', _sync_layout, font=TAB_FONT)]]
    ###
    _calibration_layout = [
        [sg.Text('Calibrated', font=REG_FONT), led(key='-CAL_LED-')],
        [ibutton('Calibrate', size=(15, 1), key='-CALIBRATE-'),
         ibutton('Set Cal. Pts.', size=(15, 1), key='-CALPTS-')]]  # TODO
    calibration_layout = [[sg.Frame('Calibration', _calibration_layout, font=TAB_FONT)]]
    ###
    _reading_profile_layout = [[sg.Text(dotted('Settling delay', 25), font=REG_FONT),
                                sg.Text("---", font=REG_FONT + " bold", background_color='white',
                                        size=(3, 1), p=(0, 0),
                                        key='-SETTLING-DELAY-')],
                               [sg.Text(dotted('Number of reading', 25), font=REG_FONT),
                                sg.Text("---", font=REG_FONT + " bold", background_color='white',
                                        size=(3, 1), p=(0, 0),
                                        key='-NUMBER-READING-')],
                               [sg.Text(dotted('Max deviation', 25), font=REG_FONT),
                                sg.Text("---", font=REG_FONT + " bold", background_color='white',
                                        size=(3, 1), p=(0, 0),
                                        key='-MAX-DEVIATION-')]]
    reading_profile_layout = [[sg.Frame('Reading Profile', _reading_profile_layout, font=TAB_FONT)]]

    ###
    _last_command_layout = [[sg.Text('Key'), sg.Text("", font=REG_FONT + " bold", size=(15, 1), p=(0, 1), relief='solid',
                                                     border_width=2, justification='c', background_color='white',
                                                     key="-LAST_KEY-"),
                            sg.Text('Command'), sg.Text("", font=REG_FONT + " bold", size=(15, 1), p=(0, 1), relief='solid',
                                                        border_width=2, justification='c', background_color='white',
                                                        key="-LAST_COMMAND-")]]
    last_command_layout = [[sg.Frame('Last Inputs', _last_command_layout, font=TAB_FONT)]]

    ###
    _backlight_layout = [sg.Slider(orientation='h', key='-BACKLIGHT-', font=SMALL_FONT)]
    backlight_layout = [[sg.Frame('Backlight level', [_backlight_layout], font=REG_FONT)]]
    ###
    _units_layout = [[ibutton('mm', size=(5, 1), key='-UNITS-MM-'), ibutton('cm', size=(5, 1), key='-UNITS-CM-')]]
    units_layout = [[sg.Frame('Units', _units_layout, font=TAB_FONT)]]
    ###
    _mode_layout = [
        [ibutton('Top', size=(8, 1), key='-MODE-TOP-'),
         ibutton('Length', size=(8, 1), key='-MODE-LENGTH-'),
         ibutton('Bottom', size=(8, 1), key='-MODE-BOTTOM-')]]
    mode_layout = [[sg.Frame('Mode', _mode_layout, font=TAB_FONT)]]

    #### --- TABS ---#####
    logging_tab_layout = [
        [sg.Text("Logging")],
        [sg.Multiline(size=(30, 15), horizontal_scroll=True, pad=(1, 1), font=SMALL_FONT, expand_x=True, expand_y=True,
                      write_only=True, auto_size_text=True, autoscroll=True, key='-STDOUT-')]]

    controller_tab_layout = [
        col([device_layout]),
        col([status_layout]),
        col([sync_layout]),
        col([calibration_layout]),
        col([reading_profile_layout]),
        col([units_layout, mode_layout]),
        col([last_command_layout]),
        col([backlight_layout]),
    ]

    # --- MENU ---#

    _menu_layout = [
        ['&Dcs5', [
            '&Configuration',
            '---',
            '&Exit']],
    ]

    menu_layout = [sg.Menu(_menu_layout, k='-MENU-', p=0, font=REG_FONT, disabled_text_color='grey'), ]

    # --- GLOBAL ---#
    global_layout = [menu_layout]

    global_layout += [[sg.TabGroup([[
        sg.Tab('Controller', controller_tab_layout),
        sg.Tab('Logging', logging_tab_layout)
    ]],
        expand_x=True, expand_y=True,
        key='-TAB GROUP-', font=REG_FONT)]]

    global_layout += [[sg.Text(f'version: v{VERSION}', font=SMALL_FONT), sg.Push(), sg.Text('Config:', font=SMALL_FONT),
                       sg.Text('No Configuration Selected', font=SMALL_FONT + ' bold', key='-CONFIGS-')]]

    window = sg.Window(
        f'Dcs5 Controller',
        global_layout,
        margins=(0, 0),
        finalize=True,
        grab_anywhere=True,
        resizable=True,
        keep_on_top=False,
        element_justification='center',
    )
    window.set_min_size(window.size)
    return window


def run():
    sg.theme('lightgrey')
    sg.theme_border_width(.2)
    sg.set_options(
        icon=LOGO,
        auto_size_buttons=True,
        use_ttk_buttons=True,
    )

    window = make_window()

    logger = logging.getLogger()
    logger.addHandler(get_multiline_handler(window=window, key="-STDOUT-", level='DEBUG'))
    logger.propagate = True

    window.metadata = {
        'is_connecting': False,
        'previous_config_path': None,
    }

    load_user_settings()

    controller = None
    if sg.user_settings()['configs_path'] is not None:
        controller = init_dcs5_controller(sg.user_settings()['configs_path'])

    refresh_layout(window, controller)

    loop_run(window, controller)

    save_user_settings()


def loop_run(window, controller):
    while True:
        event, values = window.read(timeout=.01)

        if event != "__TIMEOUT__" and event is not None:
            logging.info(f'{event}, {values}')

        match event:
            case sg.WIN_CLOSED | 'Exit':
                break
            case "-CONNECT-":
                window.metadata['is_connecting'] = True
                window.perform_long_operation(controller.start_client, end_key='-END_CONNECT-')
            case "-END_CONNECT-":
                window.metadata['is_connecting'] = False
            case "-ACTIVATE-":
                controller.start_listening()
            case "-RESTART-":
                window.metadata['is_connecting'] = True
                window.perform_long_operation(controller.start_client, end_key='-END_CONNECT-')
            case '-SYNC-':
                logging.debug('sync not mapped')
            case "-CALPTS-":
                logging.debug('Calpts not mapped')
            case "-CALIBRATE-":
                logging.debug('Calibrate not mapped')
            case 'Configuration':
                popup_window_select_config(controller=controller)
            case '-UNITS-MM-':
                controller.change_length_units_mm()
            case '-UNITS-CM-':
                controller.change_length_units_cm()
            case '-MODE-TOP-':
                controller.change_board_output_mode('top')
            case '-MODE-LENGTH-':
                controller.change_board_output_mode('length')
            case '-MODE-BOTTOM-':
                controller.change_board_output_mode('bottom')
            case '-MUTE-':
                if controller.is_muted:
                    controller.unmute_board()
                    window['-MUTE-'].update(text='Mute')
                else:
                    controller.mute_board()
                    window['-MUTE-'].update(text='Unmute')

        refresh_layout(window, controller)

    window.close()


def refresh_layout(window, controller):
    if (configs_path := sg.user_settings()['configs_path']) is not None:
        window['-CONFIGS-'].update(Path(configs_path).stem)
    else:
        window['-CONFIGS-'].update('No Config Selected')

    if controller is not None:
        _controller_refresh_layout(window, controller)
    else:
        for key in ['-CONNECT-', '-ACTIVATE-',
                    '-RESTART-', '-MUTE-',
                    '-SYNC-', '-CALIBRATE-',
                    '-CALPTS-', '-BACKLIGHT-',
                    '-UNITS-MM-', '-UNITS-CM-',
                    '-MODE-TOP-', '-MODE-BOTTOM-',
                    '-MODE-LENGTH-']:
            window[key].update(disabled=True)
        for key in ['-CONNECTED_LED-', '-ACTIVATED_LED-', '-SYNC_LED-', '-MUTED_LED-', '-CAL_LED-']:
            window[key].update(text_color='Red')


def _controller_refresh_layout(window: sg.Window, controller: Dcs5Controller):
    window['-NAME-'].update(dotted(controller.config.client.device_name + " ", DEVICE_LAYOUT_PADDING, 'right'))
    window['-MAC-'].update(dotted(controller.config.client.mac_address + " ", DEVICE_LAYOUT_PADDING, 'right'))

    window['-SETTLING-DELAY-'].update(controller.internal_board_state.stylus_settling_delay)
    window['-NUMBER-READING-'].update(controller.internal_board_state.number_of_reading)
    window['-MAX-DEVIATION-'].update(controller.internal_board_state.stylus_max_deviation)

    window['-MODE-TOP-'].update(disabled=not controller.output_mode != 'top')
    window['-MODE-LENGTH-'].update(disabled=not controller.output_mode != 'length')
    window['-MODE-BOTTOM-'].update(disabled=not controller.output_mode != 'bottom')

    window['-UNITS-MM-'].update(disabled=controller.length_units == 'mm')
    window['-UNITS-CM-'].update(disabled=controller.length_units == 'cm')

    window['-MUTED_LED-'].update(text_color='Green' if controller.is_muted else 'Red')
    window['-MUTE-'].update(disabled=False)

    window['-BACKLIGHT-'].update(
        range=(0, controller.control_box_parameters.max_backlighting_level)
    )

    if controller.client.isconnected:
        window["-CONNECTED_LED-"].update(text_color='Green')
        window["-CONNECT-"].update(disabled=True)
        window["-RESTART-"].update(disabled=False)

        window['-PORT-'].update(dotted(controller.client.port + " " or "N/A ", DEVICE_LAYOUT_PADDING, 'right'))
        window['-SYNC-'].update(disabled=False)
        window['-CALIBRATE-'].update(disabled=False)
        window['-CALPTS-'].update(disabled=False)

        if controller.is_listening:
            window["-ACTIVATED_LED-"].update(text_color='Green')
            window["-ACTIVATE-"].update(disabled=True)

            window['-BACKLIGHT-'].update(disabled=False,
                                         value=controller.internal_board_state.backlighting_level or None)
            window['-LAST_KEY-'].update('< '+controller.socket_listener.last_key+' >')
            window['-LAST_COMMAND-'].update('< '+controller.socket_listener.last_command+' >')
        else:
            window["-ACTIVATED_LED-"].update(text_color='Red')
            window["-ACTIVATE-"].update(disabled=False)

            window['-BACKLIGHT-'].update(disabled=True, value=None)

        if controller.is_sync:
            window["-SYNC_LED-"].update(text_color='Green')
        else:
            window["-SYNC_LED-"].update(text_color='Red')

        if controller.internal_board_state.calibrated is True:
            window["-CAL_LED-"].update(text_color='Green')
        else:
            window["-CAL_LED-"].update(text_color='Red')

    else:
        window['-BACKLIGHT-'].update(disabled=True, value=None)

        window["-SYNC_LED-"].update(text_color='Red')
        window['-SYNC-'].update(disabled=True)

        window["-CAL_LED-"].update(text_color='Red')
        window['-CALIBRATE-'].update(disabled=True)
        window['-CALPTS-'].update(disabled=True)

        window['-ACTIVATE-'].update(disabled=True)

        window['-LAST_KEY-'].update('-')
        window['-LAST_COMMAND-'].update('-')

        if window.metadata['is_connecting']:
            window["-CONNECTED_LED-"].update(text_color='orange')
            window["-CONNECT-"].update(disabled=True)
            window["-RESTART-"].update(disabled=True)

        else:
            window["-CONNECTED_LED-"].update(text_color='red')
            window["-CONNECT-"].update(disabled=False)
            window["-RESTART-"].update(disabled=False)


def config_window():
    if (current_config := get_current_config()) is None:
        current_config = 'No configuration loaded.'

    select_layout = [
        [sg.Text('Current:', font=REG_FONT, justification='left', pad=(0, 0)),
         sg.Text(current_config, font=REG_FONT + ' bold', key='-CONFIGURATION-', background_color='white', pad=(0, 0))],
        [],
        [sg.Listbox(
            values=list_configs(),
            select_mode='single', key='-CONFIG-', size=(24, 6),
            expand_y=True,
            expand_x=True,
            font=REG_FONT,
            pad=(0, 0),
            enable_events=True,
        )],
        [
            button('New', size=(6, 1), button_color=('black', "orange")),
            ibutton('Load', size=(6, 1), button_color=('white', "dark green"), disabled=True),
            ibutton('Delete', size=(6, 1), button_color=('white', "red3"), disabled=True)
        ]
    ]

    edit_layout = [
        [sg.Text('Files', font=REG_FONT, justification='left')],
        [
            sg.Listbox(
                values=['Controller Configuration', 'Devices Specification'],
                select_mode='single', key='-EDIT-', size=(25, 2),
                expand_y=True,
                expand_x=True,
                font=REG_FONT,
                pad=(0, 0),
                enable_events=True,
                disabled=True
            ),
            ibutton('Edit', size=(4, 1), button_color=('black', "orange"), disabled=True),
        ],

    ]

    layout = [[sg.Column(select_layout, vertical_alignment='top'), sg.VSeperator(pad=(10, 20)),
               sg.Column(edit_layout, vertical_alignment='top')],
              [button('Close', size=(6, 1), button_color=ENABLED_BUTTON_COLOR)]]

    window = sg.Window('Configurations', layout, finalize=True, element_justification='center', auto_close=True)

    return window


def popup_window_select_config(controller: Dcs5Controller):
    current_config = get_current_config()

    window = config_window()

    while True:
        event, value = window.read()

        if event in ['Close', sg.WIN_CLOSED]:
            break

        if event == 'New':
            _ = create_new_configs()

            window['-CONFIG-'].update(values=list_configs(), set_to_index=[])
            window['Load'].update(disabled=True)
            window['Delete'].update(disabled=True)
            window['-EDIT-'].update(disabled=True)
            window['Edit'].update(disabled=True)

        elif value is not None:
            if value['-CONFIG-'] is not None:
                if len(value['-CONFIG-']) != 0:
                    window['Load'].update(disabled=False)
                    window['Delete'].update(disabled=False)
                    window['-EDIT-'].update(disabled=False)
                    if len(value['-EDIT-']) != 0:
                        window['Edit'].update(disabled=False)

                    if event == 'Load':
                        selected_config_path = str(Path(CONFIG_FILES_PATH).joinpath(value['-CONFIG-'][0]))

                        sg.user_settings()['previous_config_path'] = sg.user_settings()['configs_path']
                        sg.user_settings()['configs_path'] = selected_config_path

                        if controller is None:
                            controller = init_dcs5_controller(sg.user_settings()['configs_path'])
                        else:
                            reload_controller_config(controller)

                        current_config = get_current_config()

                    if event == 'Delete':
                        if value['-CONFIG-'][0] == current_config:
                            sg.popup_ok('Cannot delete the configuration currently in use.', title='Deletion error')
                        elif sg.popup_yes_no(f"Are you sure you want to delete `{value['-CONFIG-'][0]}`") == 'Yes':
                            shutil.rmtree(str(Path(CONFIG_FILES_PATH).joinpath(value['-CONFIG-'][0])))

                            window['-CONFIG-'].update(list_configs(), set_to_index=[])
                            window['Load'].update(disabled=True)
                            window['Delete'].update(disabled=True)
                            window['-EDIT-'].update(disabled=True)
                            window['Edit'].update(disabled=True)

                    if event == 'Edit':
                        config_path = Path(CONFIG_FILES_PATH).joinpath(value['-CONFIG-'][0])
                        match value['-EDIT-'][0]:
                            case 'Controller Configuration':
                                click.edit(filename=str(config_path.joinpath(CONTROLLER_CONFIGURATION_FILE_NAME)))
                            case 'Devices Specification':
                                click.edit(filename=str(config_path.joinpath(DEVICES_SPECIFICATION_FILE_NAME)))

                        if value['-CONFIG-'][0] == current_config:
                            sg.user_settings()['previous_config_path'] = current_config + '*'
                            if sg.popup_yes_no('Do you want to reload the configuration ?') == 'Yes':
                                reload_controller_config(controller)

                if (current_config := get_current_config()) is not None:
                    window['-CONFIGURATION-'].update()
                else:
                    window['-CONFIGURATION-'].update('No Config Selected')

    window.close()


def get_current_config():
    return Path(sg.user_settings()['configs_path']).stem if sg.user_settings()['configs_path'] is not None else None


def list_configs():
    return [x.stem for x in Path(CONFIG_FILES_PATH).glob('**/*') if x.is_dir()]


def create_new_configs():
    folder_name = sg.popup_get_text('Enter a configuration name:', default_text='', font=REG_FONT, keep_on_top=True)
    if folder_name is not None:
        new_configs_path = CONFIG_FILES_PATH.joinpath(folder_name)
        new_configs_path.mkdir(parents=True, exist_ok=True)

        local_files = [
            new_configs_path.joinpath(SERVER_CONFIGURATION_FILE_NAME),
            new_configs_path.joinpath(CONTROLLER_CONFIGURATION_FILE_NAME),
            new_configs_path.joinpath(DEVICES_SPECIFICATION_FILE_NAME),
            new_configs_path.joinpath(CONTROL_BOX_PARAMETERS_FILE_NAME)
        ]
        default_files = [
            DEFAULT_SERVER_CONFIGURATION_FILE, DEFAULT_CONTROLLER_CONFIGURATION_FILE,
            DEFAULT_DEVICES_SPECIFICATION_FILE, DEFAULT_CONTROL_BOX_PARAMETERS
        ]

        logging.debug('\n\n')
        overwrite_files = None
        for lf, df in zip(local_files, default_files):
            if not Path(lf).exists():
                shutil.copyfile(df, lf)
            else:
                if overwrite_files is None:
                    overwrite_files = True  # FIXME
                if overwrite_files:
                    shutil.copyfile(df, lf)
                    logging.debug(f'Writing file: {lf}')
        return new_configs_path

    else:
        sg.popup_ok('Not name provided. Aborted')
        return None


def reload_controller_config(controller: Dcs5Controller):
    update_controller_config_paths(controller)
    try:
        controller.reload_configs()
        logging.debug('Controller reloaded.')
        if controller.client.isconnected:
            if sg.popup_yes_no('Do you want to synchronize board ?'):
                controller.init_controller_and_board()
        sg.user_settings()['configs_path'] = sg.user_settings()['configs_path'].strip('*')

    except ConfigError:
        logging.debug('ConfigError while loading config files.')
        sg.popup_ok('Could not load the configuration files.\n'
                    ' Error in the configurations files. ')
        sg.user_settings().update({'configs_path': sg.user_settings()['previous_config_path']})


def update_controller_config_paths(controller: Dcs5Controller):
    configs_path = sg.user_settings()['configs_path'].strip('*')
    controller.config_path = Path(configs_path).joinpath(CONTROLLER_CONFIGURATION_FILE_NAME)
    controller.devices_specifications_path = Path(configs_path).joinpath(DEVICES_SPECIFICATION_FILE_NAME)
    controller.control_box_parameters_path = Path(configs_path).joinpath(CONTROL_BOX_PARAMETERS_FILE_NAME)
    logging.debug('Config files path updated.')


### gui element functions ###


def dotted(value, length=50, justification='left'):
    ndots = length - len(value)
    if justification =='left':
        return value + ' ' + '.' * ndots
    elif justification =='right':
        return '.' * ndots + ' ' + value


def led(key=None):
    return sg.Text(CIRCLE, key=key, text_color='red3', font=LED_SIZE)


def ibutton(label, size, key=None, button_color=ENABLED_BUTTON_COLOR, disabled=False):
    return sg.Button(label, size=size,
                     font=REG_FONT,
                     pad=(1, 1),
                     button_color=button_color,
                     border_width=1,
                     disabled_button_color=DISABLED_BUTTON_COLOR,
                     key=key or label,
                     disabled=disabled
                     )


def button(label, button_color, size, key=None):
    return sg.Button(label,
                     size=size,
                     font=REG_FONT,
                     pad=(1, 1),
                     button_color=button_color,
                     border_width=1,
                     disabled_button_color=DISABLED_BUTTON_COLOR,
                     key=key,
                     )


def col(cols_layout):
    return [sg.Col(c, p=0) for c in cols_layout]


if __name__ == "__main__":
    main()
