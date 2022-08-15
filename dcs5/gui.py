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
from pathlib import Path
import shutil
import logging
import threading
import click

import PySimpleGUI as sg
import pyautogui as pag

from dcs5.logger import init_logging

from dcs5.controller_configurations import ConfigError

from dcs5 import VERSION, \
    SERVER_CONFIGURATION_FILE, \
    CONTROLLER_CONFIGURATION_FILE, \
    DEVICES_SPECIFICATION_FILE, \
    CONTROL_BOX_PARAMETERS, \
    DEFAULT_SERVER_CONFIGURATION_FILE, \
    DEFAULT_CONTROLLER_CONFIGURATION_FILE, \
    DEFAULT_DEVICES_SPECIFICATION_FILE, \
    DEFAULT_CONTROL_BOX_PARAMETERS, \
    CONFIG_FILES_PATH

from dcs5.controller import Dcs5Controller


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
LOADING_GIF = '../static/circle-loading-gif.gif'
CANADA_GIF = '../static/canada-flag-icon-animation.gif'


def main():
    init_logging(stdout_level='debug', write=False)

    run()

    exit(0)


def init_dcs5_controller():
    controller_config_path = CONTROLLER_CONFIGURATION_FILE
    devices_specifications_path = DEVICES_SPECIFICATION_FILE
    control_box_parameters_path = CONTROL_BOX_PARAMETERS

    try:
        Dcs5Controller(controller_config_path, devices_specifications_path, control_box_parameters_path)
    except ConfigError:
        print('Error in the config file. Loading default')

    return Dcs5Controller(DEFAULT_CONTROLLER_CONFIGURATION_FILE, DEFAULT_DEVICES_SPECIFICATION_FILE,
                          DEFAULT_CONTROL_BOX_PARAMETERS)


def make_window():
    header_layout = [[sg.Image(LOGO)]]

    device_layout = [[
        sg.Frame(
            'Device', [
                [sg.Text(dotted("Name", "N/A", 40), justification='c', pad=(5, 0), font=REG_FONT, key='-NAME-')],
                [sg.Text(dotted("MAC address", "N/A", 40), justification='c', pad=(5, 0), font=REG_FONT, key='-MAC-')],
                [sg.Text(dotted("Port (Bt Channel)", "N/A", 40), justification='c', pad=(5, 0), font=REG_FONT,
                         key='-PORT-')]
            ],
            font=TAB_FONT
        )
    ]]

    connection_layout = [
        [sg.Text('Connected', font=REG_FONT), sg.Text(CIRCLE, text_color='red', key='-C_LED-', font=LED_SIZE)],
        [button('Connect', size=(10, 0), key='-CONNECT-')]]
    activate_layout = [
        [sg.Text('Activated', font=REG_FONT), sg.Text(CIRCLE, text_color='red', key='-A_LED-', font=LED_SIZE)],
        [button('Activate', size=(10, 1), key='-ACTIVATE-')]]
    mute_layout = [[sg.Text('Muted', font=REG_FONT), sg.Text(CIRCLE, text_color='red', key='-M_LED-', font=LED_SIZE)],
                   [button('Muted', size=(10, 1), key='-MUTED-')]]
    #restart_layout = [sg.Push(), button('Restart', size=(10, 1), key='-RESTART-')]
    restart_layout = [sg.Push(),
                      sg.Button('Restart', size=(10,1),
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
    _sync_layout = [[sg.Text('Synchronized', font=REG_FONT), sg.Text(CIRCLE, text_color='red', key='-S_LED-', font=LED_SIZE)],
        [button('Synchronize', size=(15, 1), key='-SYNC-'), button('Reload Config', size=(15, 1), key='-RELOAD-')]]
    sync_layout = [[sg.Frame('Synchronize', _sync_layout, font=TAB_FONT)]]
    ###
    _calibration_layout = [[sg.Text('Calibrated', font=REG_FONT), sg.Text(CIRCLE, text_color='red', key='-CAL_LED-', font=LED_SIZE)],
                           [button('Calibrate', size=(15, 1), key='-CALIBRATE-'),
                            button('Set Cal. Pts.', size=(15, 1), key='-CALPTS-')]]  # TODO
    calibration_layout = [[sg.Frame('Calibration', _calibration_layout, font=TAB_FONT)]]
    ###
    _reading_profile_layout = [[sg.Text(dotted('Settling delay', "", 25), font=REG_FONT),
                                sg.Text("N\A", font=REG_FONT, background_color='white', size=(3, 1), key='-SD-')],
                               [sg.Text(dotted('Number of reading', "", 25), font=REG_FONT),
                                sg.Text("N\A", font=REG_FONT, background_color='white', size=(3, 1), key='-NR-')],
                               [sg.Text(dotted('Max deviation', "", 25), font=REG_FONT),
                                sg.Text("N\A", font=REG_FONT, background_color='white', size=(3, 1), key='-MD-')]]
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
        [sg.Text("Logging (Not Wokring)")],
        [sg.Multiline(size=(60, 15), font=SMALL_FONT, expand_x=True, expand_y=True, write_only=True,
                      reroute_stdout=True, reroute_stderr=True, echo_stdout_stderr=True, reroute_cprint=True,
                      autoscroll=True, key='-STDOUT-')]]

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

    _menu_layout = [['&Dcs5', ['Load', 'Connect', 'Activate', 'Synchronize', 'Restart', 'Exit']],
                    ['&Edit', ['controller configuration', 'devices specification']]]
    menu_layout = [sg.Menu(_menu_layout, k='-MENU-', p=0, font=REG_FONT)]

    # --- GLOBAL ---#
    global_layout = [menu_layout]

    global_layout += [[sg.TabGroup([[sg.Tab('Controller', controller_tab_layout),
                                     sg.Tab('Logging', logging_tab_layout)]],
                                   key='-TAB GROUP-', font=REG_FONT)]]

    global_layout += [[sg.Text(f'version: v{VERSION}', font=SMALL_FONT)]]

    # global_layout[-1].append(sg.Sizegrip())

    window = sg.Window(f'Dcs5 Controller', global_layout, finalize=True, resizable=True, keep_on_top=False)

    return window


def run():
    sg.theme('lightgrey')
    sg.theme_border_width(.2)
    sg.set_options(
        icon=LOGO,
        auto_size_buttons=True,
    )

    load_settings()

    window = make_window()
    window.metadata = {'is_connecting': False}

    # TODO DISABLE BUTTONS IN UPDATE
    # for key in ['-ACTIVATE-', '-MUTED-', '-SYNC-', '-CALIBRATE-', '-CALPTS-']:
    #     window[key].update(disabled=True)

    controller = init_dcs5_controller()

    window['-BACKLIGHT-'].update(
        range = (0, controller.control_box_parameters.max_backlighting_level)
    )

    while True:
        event, values = window.read(timeout=1)

        if event != "__TIMEOUT__" and event is not None:
            logging.info(f'{event}, {values}')

        match event:
            case sg.WIN_CLOSED | 'Exit':
                break
            case "-CONNECT-" | "Connect":
                window.metadata['is_connecting'] = True
                window.perform_long_operation(controller.start_client, end_key='-END_CONNECT-')
            case "-END_CONNECT-":
                window.metadata['is_connecting'] = False
            case "-ACTIVATE-" | "Activate":
                controller.start_listening()
            case "-RESTART-" | "Restart":
                window.metadata['is_connecting'] = True
                window.perform_long_operation(controller.restart_client, end_key='-END_CONNECT-')
            case '-SYNC-' | "Synchronize":
                print('sync not mapped')
            case "-CALPTS-":
                print('Calpts not mapped')
            case "-CALIBRATE-":
                print('Calibrate not mapped')
            case "controller configuration":
                click.edit(sg.user_settings()['configs_path'] + '/controller_configuration.json')
                if controller.client.isconnected:
                    if sg.popup_yes_no('Do you want to synchronize board ?'):
                        controller.reload_configs()
                        controller.init_controller_and_board()

            case "devices specification":
                click.edit(sg.user_settings()['configs_path'] + '/devices_specification.json')
                if controller.client.isconnected:
                    if sg.popup_yes_no('Do you want to synchronize board ?'):
                        controller.reload_configs()
                        controller.init_controller_and_board()
            case 'Load':
                _load_settings()
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

        _refresh_layout(window, controller)

    window.close()


def _refresh_layout(window: sg.Window, controller: Dcs5Controller):
    window['-NAME-'].update(dotted("Name", controller.config.client.device_name or "N/A", 40))
    window['-MAC-'].update(dotted("MAC address", controller.config.client.mac_address or "N/A", 40))

    window['-SD-'].update(controller.internal_board_state.stylus_settling_delay)
    window['-NR-'].update(controller.internal_board_state.number_of_reading)
    window['-MD-'].update(controller.internal_board_state.stylus_max_deviation)

    window['-MODE-TOP-'].update(disabled=not controller.output_mode != 'top')
    window['-MODE-LENGTH-'].update(disabled=not controller.output_mode != 'length')
    window['-MODE-BOTTOM-'].update(disabled=not controller.output_mode != 'bottom')

    window['-UNITS-MM-'].update(disabled=controller.length_units == 'mm')
    window['-UNITS-CM-'].update(disabled=controller.length_units == 'cm')

    if controller.client.isconnected:
        # TODO make a function to activate buttons on connect
        window["-C_LED-"].update(text_color='Green')
        window['-PORT-'].update(dotted("Port (Bt Channel)", controller.client.port or "N/A", 50))
        window['-SYNCHRONIZE-'].update(disabled=False)
        if controller.is_listening:
            window["-ACTIVATE-"].update(disabled=True)
            window["-A_LED-"].update(text_color='Green')
            window['-BACKLIGHT-'].update(disabled=False, value=controller.internal_board_state.backlighting_level or None)
        else:
            window["-ACTIVATE-"].update(disabled=False)
            window['-BACKLIGHT-'].update(disabled=True, value=None)
            window["-A_LED-"].update(text_color='Red')
        if controller.is_sync:
            window["-S_LED-"].update(text_color='Green')
        if controller.internal_board_state.calibrated is True:
            window["-CAL_LED-"].update(text_color='Green')
    else:
        window['-BACKLIGHT-'].update(disabled=True, value=None)
        sg.Slider()
        if window.metadata['is_connecting']:
            window["-RESTART-"].update(disabled=True)
            window["-CONNECT-"].update(disabled=True)
            window["-C_LED-"].update(text_color='orange')
        else:
            window["-CONNECT-"].update(disabled=False)
            window["-RESTART-"].update(disabled=False)
            window["-C_LED-"].update(text_color='red')
            window["-S_LED-"].update(text_color='Red')
            window["-CAL_LED-"].update(text_color='Red')


def _load_settings():
    sg.user_settings().update(
        {'configs_path': sg.popup_get_folder('Select config folder.', default_path=CONFIG_FILES_PATH)})
    sg.user_settings_save()


def load_settings():
    sg.user_settings_load()
    print(f'User Settings: {sg.user_settings()}')
    if not sg.user_settings():
        _load_settings()


def dotted(key, value, length=50):
    dots = length - len(key) - len(value) - 2
    return key + ' ' + '.' * dots + ' ' + value


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


def create_local_files():
    local_files = [
        SERVER_CONFIGURATION_FILE, CONTROLLER_CONFIGURATION_FILE,
        DEVICES_SPECIFICATION_FILE, CONTROL_BOX_PARAMETERS
    ]
    default_files = [
        DEFAULT_SERVER_CONFIGURATION_FILE, DEFAULT_CONTROLLER_CONFIGURATION_FILE,
        DEFAULT_DEVICES_SPECIFICATION_FILE, DEFAULT_CONTROL_BOX_PARAMETERS
    ]

    print('\n\n')
    overwrite_files = None
    for lf, df in zip(local_files, default_files):
        if not Path(lf).exists():
            shutil.copyfile(df, lf)
        else:
            if overwrite_files is None:
                overwrite_files = True  # FIXME
            if overwrite_files:
                shutil.copyfile(df, lf)
                print(f'Writing file: {lf}')


if __name__ == "__main__":
    main()
