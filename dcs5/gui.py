"""

- VerticalSeparator(pad=None)

- Use Popup for printing error. (bt device not found etc)


sg.UserSettings('my_config.ini', use_config_file=True, convert_bools_and_none=True)
sg.user_settings_filename(filename='DaysUntil.json') # NOT NEEDED
theme = sg.user_settings_get_entry('-theme-', 'Dark Gray 13')
sg.user_settings_set_entry('-theme-', my_new_theme)



# TODO Add command to menu button
"""
from pathlib import Path
import shutil
import logging
import threading


import PySimpleGUI as sg
import pyautogui as pag

from dcs5.logger import init_logging

#from dcs5.controller_configurations import ConfigError

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


def scale_font(font_size: int)->int:
    monitor_width, monitor_height = pag.size()
    return int(font_size * monitor_height/1080)

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
    init_logging(stdout_level='info', write=False)

    run()

    exit(0)


def init_dcs5_controller():
    config_path = CONTROLLER_CONFIGURATION_FILE
    devices_specifications_path = DEVICES_SPECIFICATION_FILE
    control_box_parameters_path = CONTROL_BOX_PARAMETERS

    return Dcs5Controller(config_path, devices_specifications_path, control_box_parameters_path)


def make_window():
    header_layout = [[sg.Image(LOGO)]]

    device_layout = [[
        sg.Frame(
            'Device', [
                [sg.Text(dotted("Name", "N/A", 50), justification='c', pad=(5, 0), font=REG_FONT, key='-NAME-')],
                [sg.Text(dotted("MAC address", "N/A", 50), justification='c', pad=(5, 0), font=REG_FONT, key='-MAC-')],
                [sg.Text(dotted("Port (Bt Channel)", "N/A", 50), justification='c', pad=(5, 0), font=REG_FONT, key='-PORT-')]
            ],
            font=TAB_FONT
        )
    ]]

    connection_layout = [[sg.Text('Connected', font=REG_FONT), sg.Text(CIRCLE, text_color='red', key='-C_LED-', font=LED_SIZE)],
                         [button('Connect', size=(10, 0), key='-CONNECT-')]]
    activate_layout = [[sg.Text('Activated', font=REG_FONT), sg.Text(CIRCLE, text_color='red', key='-A_LED-', font=LED_SIZE)],
                       [button('Activate', size=(10, 1), key='-ACTIVATE-')]]
    mute_layout = [[sg.Text('Muted', font=REG_FONT), sg.Text(CIRCLE, text_color='red', key='-M_LED-', font=LED_SIZE)],
                   [button('Muted', size=(10, 1), key='-MUTED-')]]

    _status_layout = col([connection_layout, activate_layout, mute_layout])

    status_layout = [[sg.Frame('Status', [_status_layout], font=TAB_FONT, expand_x=True)]]

    _sync_layout = [[button('Synchronize', size=(15, 1), key='-SYNC-'), button('Reload Config', size=(15, 1), key='-RELOAD-')]]
    sync_layout = [[sg.Frame('Synchronize', _sync_layout, font=TAB_FONT)]]

    _calibration_layout = [[button('Calibrate', size=(15, 1), key='-CALIBRATE-'), button('Set Cal. Pts.', size=(15, 1), key='-CALPTS-')]] #TODO
    calibration_layout = [[sg.Frame('Calibration', _calibration_layout, font=TAB_FONT)]]

    _reading_profile_layout = [[sg.Text(dotted('Settling delay', "", 25),font=REG_FONT), sg.Text("N\A", font=REG_FONT, background_color='white', size=(3,1), key='-SD-')],
                               [sg.Text(dotted('Number of reading', "", 25),font=REG_FONT), sg.Text("N\A", font=REG_FONT, background_color='white', size=(3,1), key='-NR-')],
                               [sg.Text(dotted('Max deviation', "", 25),font=REG_FONT), sg.Text("N\A", font=REG_FONT, background_color='white', size=(3,1), key='-MD-')]]
    reading_profile_layout = [[sg.Frame('Reading Profile', _reading_profile_layout, font=TAB_FONT)]]

    #--- TABS ---#

    logging_tab_layout = [
        [sg.Text("Logging")],
        [sg.Multiline(size=(60, 15), font=SMALL_FONT, expand_x=True, expand_y=True, write_only=True,
                      reroute_stdout=True, reroute_stderr=True, echo_stdout_stderr=True, reroute_cprint=True,
                      autoscroll=True, key='-STDOUT-')]]

    controller_tab_layout = [
        col([device_layout, status_layout]),
        col([sync_layout, calibration_layout]),
        col([reading_profile_layout]),
        [button('Restart', size=(10, 1), key='-RESTART-')]
    ]

    # --- MENU ---#

    _menu_layout = [['&Dcs5', ['Load', 'Connect', 'Activate', 'Synchronize', 'Restart', 'Exit']], ['&Edit', ['controller configuration', 'device specification']]]
    menu_layout = [sg.Menu(_menu_layout, k='-MENU-', p=0, font=REG_FONT)]

    # --- GLOBAL ---#
    global_layout = [menu_layout]

    global_layout += [[sg.TabGroup([[sg.Tab('Controller', controller_tab_layout),
                                     sg.Tab('Logging', logging_tab_layout)]],
                                   key='-TAB GROUP-', expand_x=True, expand_y=True, font=REG_FONT)]]

    global_layout += [[sg.Text(f'version: v{VERSION}', font=SMALL_FONT)]]

    #global_layout[-1].append(sg.Sizegrip())

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

    for key in ['-ACTIVATE-', '-RESTART-', '-MUTED-', '-SYNC-', '-CALIBRATE-', '-CALPTS-']:
        window[key].update(disabled=True)

    controller = init_dcs5_controller()

    # UPDATE with new CONFIG
    window['-NAME-'].update(dotted("Name", controller.config.client.device_name or "N/A", 50))
    window['-MAC-'].update(dotted("MAC address", controller.config.client.mac_address or "N/A", 50))

    window['-SD-'].update(controller.internal_board_state.stylus_settling_delay)
    window['-NR-'].update(controller.internal_board_state.number_of_reading)
    window['-MD-'].update(controller.internal_board_state.stylus_max_deviation)

    while True:
        event, values = window.read(timeout=1)

        if event != "__TIMEOUT__" and event is not None:
            logging.info(f'{event}, {values}')

        match event:
            case sg.WIN_CLOSED | 'Exit':
                break
            case "-CONNECT-" | "Connect":
                window["-CONNECT-"].update(disabled=True)
                window["-C_LED-"].update(text_color='orange')
                window.perform_long_operation(controller.start_client, end_key='-END_CONNECT-')
            case "-END_CONNECT-":
                window["-C_LED-"].update(text_color='red')
                sg.PopupAnimated(None)
                window["-CONNECT-"].update(disabled=False)
            case "-ACTIVATE-" | "Activate":
                window["-ACTIVATE-"].update(disabled=True)
            case "-RESTART-" | "Restart":
                window["-RESTART-"].update(disabled=True)
            case '-SYNC-' | "Synchronize":
                print('sync not mapped')
            case "-CALPTS-":
                print('Calpts not mapped')
            case "-CALIBRATE-":
                print('Calibrate not mapped')
            case "controller configuration":
                sg.execute_editor(sg.user_settings()['configs_path']+'/controller_configuration.json')
            case "devices specifications":
                pass #TODO
            case 'Load':
                _load_settings()


        if controller.client.isconnected:
            # TODO make a function to activate buttons on connect
            window["-C_LED-"].update(text_color='Green')
            window["-ACTIVATE-"].update(disabled=False)
            window['-PORT-'].update(dotted("Port (Bt Channel)", controller.client.port or "N/A", 50))

    window.close()


def _load_settings():
    sg.user_settings().update({'configs_path': sg.popup_get_folder('Select config folder.', default_path=CONFIG_FILES_PATH)})
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
                     pad=(1,1),
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
                overwrite_files=True #FIXME
            if overwrite_files:
                shutil.copyfile(df, lf)
                print(f'Writing file: {lf}')


if __name__ == "__main__":
    main()
