"""

- VerticalSeparator(pad=None)

- Use Popup for printing error. (bt device not found etc)


sg.UserSettings('my_config.ini', use_config_file=True, convert_bools_and_none=True)
sg.user_settings_filename(filename='DaysUntil.json') # NOT NEEDED
theme = sg.user_settings_get_entry('-theme-', 'Dark Gray 13')
sg.user_settings_set_entry('-theme-', my_new_theme)



# TODO Add command to menu button
"""
import os
import sys
from pathlib import Path
import shutil
import logging
import threading
import click

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
    print('Text editor changed')
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

    exit()


def init_dcs5_controller(configs_path: str):
    controller_config_path = Path(configs_path).joinpath(CONTROLLER_CONFIGURATION_FILE_NAME)
    devices_specifications_path = Path(configs_path).joinpath(DEVICES_SPECIFICATION_FILE_NAME)
    control_box_parameters_path = Path(configs_path).joinpath(CONTROL_BOX_PARAMETERS_FILE_NAME)

    if not Path(configs_path).exists():
        create_new_configs()
    else:
        check_config_integrity(
            controller_config_path=controller_config_path,
            devices_specifications_path=devices_specifications_path,
            control_box_parameters_path=control_box_parameters_path
            )

    try:
        return Dcs5Controller(controller_config_path, devices_specifications_path, control_box_parameters_path)
    except ConfigError:
        sg.popup_ok('Error in the configurations files, cannot load configuration files.', title='Error')
        return None


def check_config_integrity(controller_config_path, devices_specifications_path, control_box_parameters_path):
    if not controller_config_path.exists():
        sg.popup_ok(
            f'`controller_config.json` was missing from the directory: {controller_config_path.parent}. One was created.',
            title='Missing file')
        shutil.copyfile(DEFAULT_CONTROLLER_CONFIGURATION_FILE, controller_config_path)
    if not devices_specifications_path.exists():
        sg.popup_ok('`devices_specifications.json` was missing from the directory. One was created.',
                    title='Missing file')
        shutil.copyfile(DEFAULT_DEVICES_SPECIFICATION_FILE, devices_specifications_path)
    if not control_box_parameters_path.exists():
        shutil.copyfile(DEFAULT_CONTROL_BOX_PARAMETERS, control_box_parameters_path)
        sg.popup_ok(
            f'`devices_specifications.json` was missing from the directory {control_box_parameters_path.parent}. One was created.',
            title='Missing file')


def make_window():
    device_layout = [[
        sg.Frame(
            'Device', [
                [sg.Text(dotted("Name", 20), pad=(5, 1), font=REG_FONT),
                 sg.Text("N\A", font=REG_FONT, justification='c', background_color='white', size=(20, 1), p=(0, 0),
                         key='-NAME-')
                 ],
                [sg.Text(dotted("MAC address", 20), pad=(5, 1), font=REG_FONT),
                 sg.Text("N\A", font=REG_FONT, justification='c', background_color='white', size=(20, 1), p=(0, 0),
                         key='-MAC-')
                 ],
                [sg.Text(dotted("Port (Bt Channel)", 20), pad=(5, 1), font=REG_FONT),
                 sg.Text("N\A", font=REG_FONT, justification='c', background_color='white', size=(20, 1), p=(0, 0),
                         key='-PORT-')
                 ]
            ],
            font=TAB_FONT
        )
    ]]

    connection_layout = [
        [sg.Text('Connected', font=REG_FONT), sg.Text(CIRCLE, text_color='red', key='-CONNECTED_LED-', font=LED_SIZE)],
        [button('Connect', size=(10, 0), key='-CONNECT-')]]
    activate_layout = [
        [sg.Text('Activated', font=REG_FONT), sg.Text(CIRCLE, text_color='red', key='-ACTIVATED_LED-', font=LED_SIZE)],
        [button('Activate', size=(10, 1), key='-ACTIVATE-')]]
    mute_layout = [
        [sg.Text('Muted', font=REG_FONT), sg.Text(CIRCLE, text_color='red', key='-MUTED_LED-', font=LED_SIZE)],
        [button('Mute', size=(10, 1), key='-MUTE-')]]

    restart_layout = [sg.Push(),
                      sg.Button('Restart', size=(10, 1),
                                font=REG_FONT,
                                pad=(1, 1),
                                button_color=('white', 'red3'),
                                border_width=1,
                                disabled_button_color=DISABLED_BUTTON_COLOR,
                                key='-RESTART-',
                                use_ttk_buttons=True)]
    _status_layout = col([connection_layout, activate_layout, mute_layout])
    status_layout = [[sg.Frame('Status', [_status_layout, restart_layout], font=TAB_FONT, expand_x=True)]]
    ###
    _sync_layout = [
        [sg.Text('Synchronized', font=REG_FONT), sg.Text(CIRCLE, text_color='red', key='-SYNC_LED-', font=LED_SIZE)],
        [button('Synchronize', size=(15, 1), key='-SYNC-'), button('Reload Config', size=(15, 1), key='-RELOAD-')]]
    sync_layout = [[sg.Frame('Synchronize', _sync_layout, font=TAB_FONT)]]
    ###
    _calibration_layout = [
        [sg.Text('Calibrated', font=REG_FONT), sg.Text(CIRCLE, text_color='red', key='-CAL_LED-', font=LED_SIZE)],
        [button('Calibrate', size=(15, 1), key='-CALIBRATE-'),
         button('Set Cal. Pts.', size=(15, 1), key='-CALPTS-')]]  # TODO
    calibration_layout = [[sg.Frame('Calibration', _calibration_layout, font=TAB_FONT)]]
    ###
    _reading_profile_layout = [[sg.Text(dotted('Settling delay', 25), font=REG_FONT),
                                sg.Text("N\A", font=REG_FONT, background_color='white', size=(3, 1), p=(0, 0),
                                        key='-SETTLING-DELAY-')],
                               [sg.Text(dotted('Number of reading', 25), font=REG_FONT),
                                sg.Text("N\A", font=REG_FONT, background_color='white', size=(3, 1), p=(0, 0),
                                        key='-NUMBER-READING-')],
                               [sg.Text(dotted('Max deviation', 25), font=REG_FONT),
                                sg.Text("N\A", font=REG_FONT, background_color='white', size=(3, 1), p=(0, 0),
                                        key='-MAX-DEVIATION-')]]
    reading_profile_layout = [[sg.Frame('Reading Profile', _reading_profile_layout, font=TAB_FONT)]]

    ###
    _backlight_layout = [sg.Slider(orientation='h', key='-BACKLIGHT-', font=SMALL_FONT)]
    backlight_layout = [[sg.Frame('Backlight level', [_backlight_layout], font=REG_FONT)]]
    ###
    _units_layout = [[button('mm', size=(5, 1), key='-UNITS-MM-'), button('cm', size=(5, 1), key='-UNITS-CM-')]]
    units_layout = [[sg.Frame('Units', _units_layout, font=TAB_FONT)]]
    ###
    _mode_layout = [
        [button('Top', size=(8, 1), key='-MODE-TOP-'),
         button('Length', size=(8, 1), key='-MODE-LENGTH-'),
         button('Bottom', size=(8, 1), key='-MODE-BOTTOM-')]]
    mode_layout = [[sg.Frame('Mode', _mode_layout, font=TAB_FONT)]]

    # --- TABS ---#

    logging_tab_layout = [
        [sg.Text("Logging")],
        [sg.Multiline(size=(60, 15), horizontal_scroll=True, pad=(1, 1), font=REG_FONT, expand_x=True, expand_y=True,
                      write_only=True, auto_size_text=True, autoscroll=True, key='-STDOUT-')]]

    # controller_tab_layout = [
    #     col([device_layout, status_layout]),
    #     [sg.HorizontalSeparator()],
    #     col([sync_layout, calibration_layout]),
    #     col([reading_profile_layout, units_layout, mode_layout, backlight_layout]),
    # ]

    controller_tab_layout = [
        col([device_layout]),
        col([status_layout]),
        col([sync_layout]),
        col([calibration_layout]),
        col([reading_profile_layout]),
        col([units_layout, mode_layout]),
        col([backlight_layout]),
    ]

    # --- MENU ---#

    _menu_layout = [['&Dcs5', ['&New',
                               '&Select',
                               '---',
                               '&Exit']],
                    ['&Edit', ['Controller Configuration', 'Devices Specification']]]

    menu_layout = [sg.Menu(_menu_layout, k='-MENU-', p=0, font=REG_FONT, disabled_text_color='grey'), ]

    # --- GLOBAL ---#
    global_layout = [menu_layout]

    global_layout += [[sg.TabGroup([[sg.Tab('Controller', controller_tab_layout),
                                     sg.Tab('Logging', logging_tab_layout)]],
                                   key='-TAB GROUP-', font=REG_FONT)]]

    global_layout += [[sg.Text(f'version: v{VERSION}', font=SMALL_FONT), sg.Push(), sg.Text('Config:', font=SMALL_FONT),
                       sg.Text('No Config Selected', font=SMALL_FONT, key='-CONFIGS-')]]

    window = sg.Window(f'Dcs5 Controller', global_layout, finalize=True, resizable=True, keep_on_top=False)

    return window


def run():
    sg.theme('lightgrey')
    sg.theme_border_width(.2)
    sg.set_options(
        icon=LOGO,
        auto_size_buttons=True,
    )

    window = make_window()

    logger = logging.getLogger()
    logger.addHandler(get_multiline_handler(window=window, key="-STDOUT-", level='DEBUG'))
    logger.propagate = True

    window.metadata = {
        'is_connecting': False,
    }

    load_user_settings()

    controller = None
    if sg.user_settings()['configs_path'] is not None:
        controller = init_dcs5_controller(sg.user_settings()['configs_path'])

    refresh_layout(window, controller)

    _run(window, controller)


def _run(window, controller):
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
            case "-RELOAD-":
                reload_controller_config(controller)
            case "Controller Configuration":
                edit(CONTROLLER_CONFIGURATION_FILE_NAME)
                reload_controller_config(controller)
            case "Devices Specification":
                edit(DEVICES_SPECIFICATION_FILE_NAME)
                reload_controller_config(controller)
            case 'New':
                create_new_configs()
                reload_controller_config(controller)
            case 'Select':
                select_configs_folder()
                reload_controller_config(controller)
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
        _refresh_layout(window, controller)
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


def _refresh_layout(window: sg.Window, controller: Dcs5Controller):
    window['-NAME-'].update(controller.config.client.device_name)
    window['-MAC-'].update(controller.config.client.mac_address)

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
        # TODO make a function to activate buttons on connect
        window["-CONNECTED_LED-"].update(text_color='Green')
        window["-CONNECT-"].update(disabled=True)
        window["-RESTART-"].update(disabled=False)

        window['-PORT-'].update(dotted("Port (Bt Channel)", controller.client.port or "N/A", 50))
        window['-SYNC-'].update(disabled=False)
        window['-CALIBRATE-'].update(disabled=False)
        window['-CALPTS-'].update(disabled=False)

        if controller.is_listening:
            window["-ACTIVATED_LED-"].update(text_color='Green')
            window["-ACTIVATE-"].update(disabled=True)

            window['-BACKLIGHT-'].update(disabled=False,
                                         value=controller.internal_board_state.backlighting_level or None)
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

        if window.metadata['is_connecting']:
            window["-CONNECTED_LED-"].update(text_color='orange')
            window["-CONNECT-"].update(disabled=True)
            window["-RESTART-"].update(disabled=True)

        else:
            window["-CONNECTED_LED-"].update(text_color='red')
            window["-CONNECT-"].update(disabled=False)
            window["-RESTART-"].update(disabled=False)


def load_user_settings():
    sg.user_settings_load()
    logging.debug(f'User Settings: {sg.user_settings()}')
    if 'configs_path' not in sg.user_settings():
        select_configs_folder()


def select_configs_folder():
    current_config = None
    if user_settings := sg.user_settings():
        if config := user_settings['configs_path']:
            current_config = Path(config).stem

    config_path = None
    if (selected_config := popup_window_select_config(default_config=current_config)) is not None:
        config_path = str(Path(CONFIG_FILES_PATH).joinpath(selected_config))

    sg.user_settings().update({
        'configs_path': config_path
    })

    sg.user_settings_save()


def popup_window_select_config(default_config: str):
    layout = [[sg.Text('Select configuration', size=(20, 1), font='Lucida', justification='left')],
              [sg.Listbox(values=[x.stem for x in Path(CONFIG_FILES_PATH).glob('**/*') if x.is_dir()],
                          default_values=[default_config],
                          select_mode='single', key='-CONFIG-', size=(30, 6),
                          expand_y=True)],
              [sg.Button('Select', font=REG_FONT), sg.Button('Delete', font=REG_FONT), sg.Button('Cancel', font=REG_FONT)]]

    window = sg.Window('Select configuration', layout)

    event, value = window.read()

    window.close()

    selected_config = default_config
    if value['-CONFIG-']:
        if event == 'Select':
            selected_config = value['-CONFIG-'][0]
        if event == 'Delete':
            if default_config == value['-CONFIG-'][0]:
                sg.popup_ok('Cannot delete the configuration currently in use.')
            else:
                if sg.popup_yes_no(f"Are you sure you want to delete `{value['-CONFIG-'][0]}`"):
                    shutil.rmtree(str(Path(CONFIG_FILES_PATH).joinpath(value['-CONFIG-'][0])))

    return selected_config


def create_new_configs():
    folder_name = sg.popup_get_text('Enter a name for the configuration:', default_text='', font=REG_FONT)
    if folder_name is not None:
        new_configs_path = CONFIG_FILES_PATH.joinpath(folder_name)
        new_configs_path.mkdir(parents=True, exist_ok=True)

        sg.user_settings()['configs_path'] = new_configs_path

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
    else:
        sg.popup_ok('Not name provided. Aborted')


def update_controller_config_paths(controller):
    configs_path = sg.user_settings()['configs_path']
    controller.controller_config_path = Path(configs_path).joinpath(CONTROLLER_CONFIGURATION_FILE_NAME)
    controller.devices_specifications_path = Path(configs_path).joinpath(DEVICES_SPECIFICATION_FILE_NAME)
    controller.control_box_parameters_path = Path(configs_path).joinpath(CONTROL_BOX_PARAMETERS_FILE_NAME)
    logging.debug('Config files path updated.')


def reload_controller_config(controller):
    if controller is not None:
        update_controller_config_paths(controller)
        controller.reload_configs()
        logging.debug('Controller reloaded.')

        if controller.client.isconnected:
            if sg.popup_yes_no('Do you want to synchronize board ?'):
                controller.init_controller_and_board()
    else:
        controller = init_dcs5_controller(sg.user_settings()['configs_path'])

    return controller


def edit(filename):
    if sg.user_settings()['configs_path'] is not None:
        click.edit(filename=str(Path(sg.user_settings()['configs_path']).joinpath(filename)))
    else: # This should never happen tho... I think.
        sg.popup_ok("No config is selected.")


def dotted(value, length=50):
    ndots = length - len(value)
    return value + ' ' + '.' * ndots


def led(color, key=None, font=None):
    return sg.Text(CIRCLE, text_color=color, key=key, font=font)


def button(label, size, key):
    return sg.Button(label, size=size,
                     font=REG_FONT,
                     pad=(1, 1),
                     button_color=ENABLED_BUTTON_COLOR,
                     border_width=1,
                     disabled_button_color=DISABLED_BUTTON_COLOR,
                     key=key,
                     use_ttk_buttons=True)


def col(cols_layout):
    return [sg.Col(c, p=0) for c in cols_layout]


if __name__ == "__main__":
    main()
