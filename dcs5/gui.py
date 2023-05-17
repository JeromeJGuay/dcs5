"""
"""
import logging

import os
import shutil
import sys
import time
import traceback
import webbrowser
from pathlib import Path
from typing import *

import PySimpleGUI as sg
import click
import pyautogui as pag

from dcs5 import VERSION, LOCAL_FILE_PATH, CONFIG_FILES_PATH
from dcs5.controller import Dcs5Controller
from dcs5.controller_configurations import ConfigError
from dcs5.logger import init_logging
from dcs5.utils import resolve_relative_path, update_json_value


# This is a fix for my computer. Should not influence anything.
if os.environ.get('EDITOR') == 'EMACS':
    print('Text editor changed.')
    os.environ.update({'EDITOR': 'pluma'})

# CONFIGS FILENAMES
CONTROLLER_CONFIGURATION_FILE_NAME = 'controller_configuration.json'
XT_CONTROLLER_CONFIGURATION_FILE_NAME = 'xt_controller_configuration.json'
MICRO_CONTROLLER_CONFIGURATION_FILE_NAME = 'micro_controller_configuration.json'

DEVICES_SPECIFICATION_FILE_NAME = 'devices_specification.json'
XT_DEVICES_SPECIFICATION_FILE_NAME = 'xt_devices_specification.json'
MICRO_DEVICES_SPECIFICATION_FILE_NAME = 'micro_devices_specification.json'

# PATHS
DEFAULT_CONFIG_PATH = "default_configs/"

XT_DEFAULT_CONTROLLER_CONFIGURATION_FILE = str(
    resolve_relative_path(DEFAULT_CONFIG_PATH + XT_CONTROLLER_CONFIGURATION_FILE_NAME, __file__))
MICRO_DEFAULT_CONTROLLER_CONFIGURATION_FILE = str(
    resolve_relative_path(DEFAULT_CONFIG_PATH + MICRO_CONTROLLER_CONFIGURATION_FILE_NAME, __file__))

XT_DEFAULT_DEVICES_SPECIFICATION_FILE = str(
    resolve_relative_path(DEFAULT_CONFIG_PATH + XT_DEVICES_SPECIFICATION_FILE_NAME, __file__))
MICRO_DEFAULT_DEVICES_SPECIFICATION_FILE = str(
    resolve_relative_path(DEFAULT_CONFIG_PATH + MICRO_DEVICES_SPECIFICATION_FILE_NAME, __file__))

#USER_GUIDE_FILE_FRANÇAIS = str(resolve_relative_path('static/user_guide_fr.pdf', __file__))
#if not Path(USER_GUIDE_FILE_FRANÇAIS).exists():
#    USER_GUIDE_FILE_FRANÇAIS = str(resolve_relative_path('../user_guide_fr.html', __file__))
USER_GUIDE_FILE_ENGLISH = str(resolve_relative_path('user_guide_en.html', __file__))
if not Path(USER_GUIDE_FILE_ENGLISH).exists():
    USER_GUIDE_FILE_ENGLISH = str(resolve_relative_path('../user_guide_en.html', __file__))


if sys.platform in ("linux", "linux2"):
    LOGO_PATH = str(resolve_relative_path('static/bigfin_logo.png', __file__))

elif sys.platform == "win32":
    LOGO_PATH = str(resolve_relative_path('static/bigfin_logo.ico', __file__))


def scale_font(font_size: int) -> int:
    monitor_width, monitor_height = pag.size()
    return int(font_size * monitor_height / (1080 * 1.1)) # 1.1 is to scale it down more for windows.


REFRESH_PERIOD = .1  # was 0.05 but It was increased to give to for the backlight to be updated in the controller

BACKLIGHT_SLIDER_MAX = 100

DEVICE_LAYOUT_PADDING = 16

SMALL_FONT = f'Courier {scale_font(8)}'

REG_FONT = f'Courier {scale_font(10)}'
REG_FONT_BOLD = REG_FONT + ' bold'

FRAME_FONT = f'Courier {scale_font(12)}'

HEADER_FONT = f'Courier {scale_font(15)}'

EMPTY_CIRCLE = '\u25CB'

LED_FONT = f'Courier {scale_font(12)}'

LED_ON = {'value': '\u2B24', 'text_color': 'Green', 'font': FRAME_FONT}
LED_WAIT = {'value': '\u25B2', 'text_color': 'Orange', 'font': LED_FONT}
LED_OFF = {'value': '\u25CB', 'text_color': 'Red', 'font': LED_FONT + ' bold'}

ENABLED_BUTTON_COLOR = ('black', "light blue")
DISABLED_BUTTON_COLOR = ('gray', "light grey")
SELECTED_BUTTON_COLOR = ('OrangeRed', "light grey")

META_OFF = {'text_color': 'gray', 'background_color': 'light grey'}
META_ON = {'text_color': 'black', 'background_color': 'gold'}

USER_SETTING_FILE = 'user_settings.json'


def main():
    try:
        init_logging(stdout_level='INFO', write=True)
        run()
    except Exception as e:
        logging.error(traceback.format_exc(), exc_info=True)
        sg.popup_error(f'CRITICAL ERROR. SHUTTING DOWN', title='CRITICAL ERROR', keep_on_top=True)
    finally:
        # sys.exit()
        pass


def init_dcs5_controller():
    controller_config_path = Path(sg.user_settings()['configs_path']).joinpath(CONTROLLER_CONFIGURATION_FILE_NAME)
    devices_specifications_path = Path(sg.user_settings()['configs_path']).joinpath(DEVICES_SPECIFICATION_FILE_NAME)

    check_config_integrity(
        controller_config_path=controller_config_path,
        devices_specifications_path=devices_specifications_path,
    )

    try:
        controller = Dcs5Controller(
            controller_config_path,
            devices_specifications_path,
        )
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


def check_config_integrity(
        controller_config_path,
        devices_specifications_path,
):
    if not controller_config_path.exists():
        sg.popup_ok(
            f'`controller_config.json` was missing from the directory: {controller_config_path.parent}. One was created. (default model: xt)',
            title='Missing file', keep_on_top=True)
        shutil.copyfile(XT_DEFAULT_CONTROLLER_CONFIGURATION_FILE, controller_config_path)
    if not devices_specifications_path.exists():
        sg.popup_ok(
            '`devices_specifications.json` was missing from the directory. One was created (default model: xt).',
            title='Missing file', keep_on_top=True)
        shutil.copyfile(XT_DEFAULT_DEVICES_SPECIFICATION_FILE, devices_specifications_path)


def load_user_settings():
    sg.user_settings().update({'configs_path': None}),
    sg.user_settings_load()
    logging.debug(f'User Settings: {sg.user_settings()}')
    if (config_path := sg.user_settings()['configs_path']) is not None:
        if Path(config_path).name not in list_configs():
            sg.user_settings().update({'configs_path': None})
    sg.user_settings().update({'previous_configs_path': None})
    save_user_settings()


def save_user_settings():
    previous_configs_path = sg.user_settings().pop('previous_configs_path')
    sg.user_settings_save()
    sg.user_settings().update({'previous_configs_path': previous_configs_path})


def make_window():
    device_layout = [[
        sg.Frame(
            'Device', [
                [sg.Text(dotted(" Name", 18), pad=(0, 0), font=REG_FONT),
                 sg.Text(dotted("N\A ", DEVICE_LAYOUT_PADDING, 'right'), font=REG_FONT, p=(0, 0), key='-NAME-')],
                [sg.Text(dotted(" Model", 18), pad=(0, 0), font=REG_FONT),
                 sg.Text(dotted("N\A ", DEVICE_LAYOUT_PADDING, 'right'), font=REG_FONT, p=(0, 0), key='-MODEL-')],
                [sg.Text(dotted(" Firmware", 18), pad=(0, 0), font=REG_FONT),
                 sg.Text(dotted("N\A ", DEVICE_LAYOUT_PADDING, 'right'), font=REG_FONT, p=(0, 0), key='-FIRMWARE-')],
                [sg.Text(dotted(" MAC address", 18), pad=(0, 0), font=REG_FONT),
                 sg.Text(dotted("N\A", DEVICE_LAYOUT_PADDING, 'right'), font=REG_FONT, p=(0, 0), key='-MAC-')],
                [sg.Text(dotted(" Port (Bt Channel)", 18), pad=(0, 0), font=REG_FONT),
                 sg.Text(dotted("N\A ", DEVICE_LAYOUT_PADDING, 'right'), font=REG_FONT, p=(0, 0), key='-PORT-')],
                [sg.HSeparator()],

                [sg.Text("Temperature:", font=REG_FONT), sg.Text("N\A", key="-TEMPERATURE-", font=REG_FONT),
                 sg.Push(),
                 sg.Text("Battery:", font=REG_FONT), sg.Text("N\A", key="-BATTERY-", font=REG_FONT)
                 ],
                [sg.Text("Humidity:", font=REG_FONT), sg.Text("N\A", key="-HUMIDITY-", font=REG_FONT),
                 sg.Push(),
                 sg.Text("Charging:", font=REG_FONT), sg.Text("N\A", key="-CHARGING-", font=REG_FONT)
                 ],
                [sg.HSeparator()],
                [sg.Text("Marel Weight:", font=REG_FONT),
                 sg.Text("N/A", key="-MAREL_WEIGHT_DEVICE-", font=REG_FONT)]
            ],
            font=FRAME_FONT
        )
    ]]

    _pad = 20
    marel_layout = [[
        sg.Frame(
            'Marel', [
                [sg.Text(dotted(" Host", _pad), pad=(0, 0), font=REG_FONT),
                 sg.InputText(size=(14, 1), border_width=1, pad=(0, 0), key='-MAREL_HOST-', justification='right',
                              font=REG_FONT, tooltip="Scale IP address", enable_events=False)
                 ],
                [sg.Text(" Status", pad=(0, 0), font=REG_FONT), led(key='-MAREL_LED-'),
                 sg.Push(),
                 ibutton('Start', size=(6, 1), key='-MAREL_START-'),
                 ibutton('Stop', size=(6, 1), key='-MAREL_STOP-', button_color='darkred')],
                [sg.Text(dotted(" Weight", _pad), pad=(0, 0), font=REG_FONT),  # sg.Push(),
                 sg.Text("N/A", key="-MAREL_WEIGHT-", font=FRAME_FONT, size=(12, 1), justification='right',
                         relief='sunken', border_width=1)],
                [
                    sg.Push(),
                    sg.Text("Units", pad=(0, 0), font=REG_FONT),
                    sg.Combo(default_value='kg', values=['kg', 'g', 'lb', 'oz'], key='-MAREL_UNITS-', enable_events=True, size=(5, 1), readonly=True,
                     pad=(1, 1), font=REG_FONT)
                ],
            ],
            font=FRAME_FONT
        )
    ]]

    ### STATUS
    connection_layout = [
        [sg.Text(' Connected', font=REG_FONT), led(key='-CONNECTED_LED-')],
        [ibutton('Connect', size=(11, 1), key='-CONNECT-')]]
    activate_layout = [
        [sg.Text(' Activated', font=REG_FONT), led(key='-ACTIVATED_LED-')],
        [ibutton('Activate', size=(11, 1), key='-ACTIVATE-')]]
    mute_layout = [
        [sg.Text('  Muted', font=REG_FONT), led(key='-MUTED_LED-')],
        [ibutton('Mute', size=(11, 1), key='-MUTE-')]]

    restart_layout = [ibutton('Disconnect', size=(11, 1), key='-DISCONNECT-', button_color='orange'),
                      sg.Push(),
                      sg.Button('Restart', size=(11, 1),
                                font=REG_FONT,
                                pad=(1, 1),
                                button_color=('white', 'red3'),
                                border_width=1,
                                disabled_button_color=DISABLED_BUTTON_COLOR,
                                key='-RESTART-',
                                )]
    _status_layout = col([connection_layout, activate_layout, mute_layout])
    status_layout = [[sg.Frame('Status', [_status_layout, restart_layout], font=FRAME_FONT, expand_x=True)]]

    ### SYNC
    _sync_layout = [
        [sg.Text('Synchronized', font=REG_FONT), led(key='-SYNC_LED-')],
        [ibutton('Synchronize', size=(15, 1), key='-SYNC-'), ]]
    sync_layout = [[sg.Frame('Synchronize', _sync_layout, font=FRAME_FONT)]]

    ### CALIBRATION
    _calibration_layout = [
        [sg.Text('Calibrated', font=REG_FONT), led(key='-CAL_LED-')],
        [ibutton('Calibrate', size=(15, 1), key='-CALIBRATE-'),
         ibutton('Set Cal. Pts.', size=(15, 1), key='-CALPTS-')]]  # TODO
    calibration_layout = [[sg.Frame('Calibration', _calibration_layout, font=FRAME_FONT)]]

    ### READING PROFILE
    _reading_profile_layout = [[sg.Text(dotted('Settling delay', 19), font=REG_FONT),
                                sg.Text("---", font=REG_FONT_BOLD, background_color='white',
                                        size=(3, 1), p=(1, 0), justification='c', key='-SETTLING-DELAY-')],
                               [sg.Text(dotted('Number of reading', 19), font=REG_FONT),
                                sg.Text("---", font=REG_FONT_BOLD, background_color='white',
                                        size=(3, 1), p=(1, 0), justification='c', key='-NUMBER-READING-')],
                               [sg.Text(dotted('Max deviation', 19), font=REG_FONT),
                                sg.Text("---", font=REG_FONT_BOLD, background_color='white',
                                        size=(3, 1), p=(1, 0), justification='c', key='-MAX-DEVIATION-')]]
    reading_profile_layout = [[sg.Frame('Reading Profile', _reading_profile_layout, font=FRAME_FONT)]]

    ### LAST COMMAND
    _last_command_layout = [[sg.Text('Key'), sg.Text("", font=REG_FONT_BOLD, size=(10, 1), p=(1, 1), relief='solid',
                                                     border_width=2, justification='c', background_color='white',
                                                     key="-LAST_KEY-"),
                             sg.Text('Command'), sg.Text("", font=REG_FONT_BOLD, size=(20, 1), p=(1, 1), relief='solid',
                                                         border_width=2, justification='c', background_color='white',
                                                         key="-LAST_COMMAND-")]]
    last_command_layout = [[sg.Frame('Last Inputs', _last_command_layout, font=FRAME_FONT)]]

    ### BACKLIGHT
    _backlight_layout = [sg.Slider(orientation='h', key='-BACKLIGHT-', font=SMALL_FONT, enable_events=True)]
    backlight_layout = [[sg.Frame('Backlight level', [_backlight_layout], font=REG_FONT)]]

    ### UNITS
    _units_layout = [[ibutton('mm', size=(5, 1), key='-UNITS-MM-', disabled_button_color=SELECTED_BUTTON_COLOR),
                      ibutton('cm', size=(5, 1), key='-UNITS-CM-', disabled_button_color=SELECTED_BUTTON_COLOR)]]
    units_layout = [[sg.Frame('Units', _units_layout, font=FRAME_FONT)]]

    ### STYLUS
    _stylus_layout = [
        [sg.Combo(values=[''], key='-STYLUS-', enable_events=True, size=(10, 1), pad=(1, 1), font=REG_FONT, readonly=True),
         sg.Text('Offset:', font=REG_FONT),
         sg.Text("-", font=REG_FONT_BOLD, background_color='white',
                 size=(3, 1), p=(1, 0), justification='c', key='-STYLUS_OFFSET-')
         ]]
    stylus_layout = [[sg.Frame('Stylus', _stylus_layout, font=FRAME_FONT)]]

    ### MODE
    _mode_layout = [[ibutton('Top', size=(8, 1), key='-MODE-TOP-', disabled_button_color=SELECTED_BUTTON_COLOR),
                     ibutton('Length', size=(8, 1), key='-MODE-LENGTH-', disabled_button_color=SELECTED_BUTTON_COLOR),
                     ibutton('Bottom', size=(8, 1), key='-MODE-BOTTOM-', disabled_button_color=SELECTED_BUTTON_COLOR)]]
    mode_layout = [[sg.Frame('Mode', _mode_layout, font=FRAME_FONT)]]
    ### Auto_enter

    _auto_enter_layout = [[
        sg.Text(" Auto-enter:", pad=(0, 0), font=REG_FONT),
        ibutton('On', size=(3, 1), key='-AUTO_ENTER-')
    ]]

    auto_enter_layout = [[sg.Frame('Misc', _auto_enter_layout, font=FRAME_FONT)]]

    ### META key
    _meta_layout = [[sg.Text('Mode', font=REG_FONT_BOLD, border_width=2, relief='solid', **META_OFF, size=(6, 1),
                             justification='center', pad=(1, 1), key='-META-'),
                     sg.Text('Shift', font=REG_FONT_BOLD, border_width=2, relief='solid', **META_OFF, size=(6, 1),
                             justification='center', pad=(1, 1), key='-SHIFT-'),
                     sg.Text('Ctrl', font=REG_FONT_BOLD, border_width=2, relief='solid', **META_OFF, size=(6, 1),
                             justification='center', pad=(1, 1), key='-CTRL-'),
                     sg.Text('Alt', font=REG_FONT_BOLD, border_width=2, relief='solid', **META_OFF, size=(6, 1),
                             justification='center', pad=(1, 1), key='-ALT-')]]
    meta_layout = [[sg.Frame('Meta Key', _meta_layout, font=FRAME_FONT)]]

    ### TABS LAYOUTS ###

    marel_tab_layout = [
        col([marel_layout])
    ]

    controller_tab_layout = [
        col([device_layout]),
        col([status_layout]),
        col([reading_profile_layout, sync_layout]),
        col([calibration_layout]),
        col([units_layout, mode_layout]),
        col([auto_enter_layout, meta_layout]),
        col([last_command_layout]),
        col([stylus_layout, backlight_layout])
    ]

    # MENU #

    _menu_layout = [
        ['&Dcs5', [
            '&Configuration',
            '---',
            '&Exit']],
        ['Help', ['Guide_fr', 'Guide_en']]
    ]

    menu_layout = [sg.Menu(_menu_layout, k='-MENU-', p=0, font=REG_FONT, disabled_text_color='grey'), ]

    # FOOTNOTE #
    footnote_layout = [[
        sg.Text(f'version: v{VERSION}', font=SMALL_FONT), sg.Push(), sg.Text('Config:', font=SMALL_FONT),
        sg.Text('No Configuration Selected', font=SMALL_FONT + ' bold', key='-CONFIGS-')
    ]]

    # GLOBAL #
    global_layout = [
        [menu_layout],
        [sg.TabGroup([
            [sg.Tab('Dcs5', controller_tab_layout,  element_justification='center')],
            [sg.Tab('Marel', marel_tab_layout, element_justification='center')]
        ])],
        [footnote_layout]
    ]

    window = sg.Window(
        f'Dcs5 Controller',
        global_layout,
        margins=(0, 0),
        finalize=True,
        grab_anywhere=True,
     #   resizable=True,
        keep_on_top=False,
        element_justification='center',
    )
    #window.set_min_size(tuple(map(lambda x: int(x / 2), window.size)))
    #window.set_min_size((window.size[0], int(window.size[1]/2)))

    window['-MAREL_HOST-'].bind("<Return>", "ENTER-")

    return window


def run():
    sg.user_settings_filename(USER_SETTING_FILE, LOCAL_FILE_PATH)
    load_user_settings()

    sg.theme('lightgrey')
    sg.theme_border_width(.1)
    sg.set_options(
        icon=LOGO_PATH,
        # sbar_width=2,
        # auto_size_buttons=True,
        # auto_size_text=True,
        use_ttk_buttons=True,
    )

    window = make_window()
    sg.SetOptions(window_location=get_new_location(window))

    window.metadata = {
        'is_connecting': False,
        'previous_configs_path': None,
    }

    if sg.user_settings()['configs_path'] is not None:
        controller = init_dcs5_controller()
    else:
        while sg.user_settings()['configs_path'] is None:
            controller = modal(window, popup_window_select_config)

    init_layout(window, controller)

    loop_run(window, controller)

    save_user_settings()


def init_layout(window: sg.Window, controller: Dcs5Controller):
    if controller is not None:
        window['-BACKLIGHT-'].update(range=(0, BACKLIGHT_SLIDER_MAX), value=0)

        if controller.config.client.marel_ip_address:
            window['-MAREL_HOST-'].update(controller.config.client.marel_ip_address)

    refresh_layout(window, controller)


def loop_run(window: sg.Window, controller: Dcs5Controller):
    while True:
        event, values = window.read(timeout=.05)

        if event != "__TIMEOUT__" and event is not None:
            logging.debug(f'{event}, {values}')

        if event in (sg.WIN_CLOSED, 'Exit'):
            if controller is not None:
                controller.close_client()
            break
        else:
            sg.SetOptions(window_location=get_new_location(window))

        match event:
            case "-MAREL_HOST-ENTER-":
                update_marel_host(controller, values['-MAREL_HOST-'])
            case "-MAREL_START-":
                update_marel_host(controller, values['-MAREL_HOST-'])
                controller.start_marel_listening()
                window['-MAREL_LED-'].update(**LED_WAIT)
                window['-MAREL_START-'].update(disabled=True)
                window.refresh()
            case "-MAREL_STOP-":
                controller.stop_marel_listening()
            case "-MAREL_UNITS-":
                logging.debug(f'UNITS {event}, {values}')
                controller.marel.set_units(values['-MAREL_UNITS-'])

            case "-AUTO_ENTER-":
                if controller.auto_enter:
                    window['-AUTO_ENTER-'].update('Off')
                else:
                    window['-AUTO_ENTER-'].update('On')
                controller.set_auto_enter(not controller.auto_enter)
                window.refresh()
            case "-CONNECT-":
                window.metadata['is_connecting'] = True
                window.perform_long_operation(controller.start_client, end_key='-END_CONNECT-')
            case "-DISCONNECT-":
                controller.close_client()
            case "-END_CONNECT-":
                window.metadata['is_connecting'] = False
                if not controller.client.is_connected:
                    modal(window, sg.popup_ok, controller.client.error_msg, title='Failed.', keep_on_top=True, font=REG_FONT,
                                modal=True)
            case "-ACTIVATE-":
                window['-ACTIVATED_LED-'].update(**LED_WAIT)
                window['-ACTIVATE-'].update(disabled=True)
                window.refresh()
                if not controller.is_sync:
                    controller.init_controller_and_board()
                controller.start_listening()
            case "-RESTART-":
                window.metadata['is_connecting'] = True
                window.perform_long_operation(controller.restart_client, end_key='-END_CONNECT-')
            case '-SYNC-':
                window['-SYNC_LED-'].update(**LED_WAIT)
                window['-SYNC-'].update(disabled=True)
                window.refresh()
                controller.init_controller_and_board()
            case "-CALPTS-":
                modal(window, popup_window_set_calibration_pt, controller)
            case "-CALIBRATE-":
                modal(window, popup_window_calibrate, controller)
            case 'Configuration':
                controller = modal(window, popup_window_select_config, controller=controller)
                # MAREL HOST IS UPDATED HERE SINCE THE FIELD IS ALSO AN INPUT
                window['-MAREL_HOST-'].update(controller.config.client.marel_ip_address)
            case '-STYLUS-':
                controller.change_stylus(values['-STYLUS-'], flash=False)
            case '-BACKLIGHT-':
                controller.c_set_backlighting_level(
                    int(
                        (values[
                             '-BACKLIGHT-'] / BACKLIGHT_SLIDER_MAX) * controller.control_box_parameters.max_backlighting_level
                    )
                )
            case '-UNITS-MM-':
                if controller.is_listening:
                    controller.change_length_units_mm(flash=False)  # QUICK FIX should be disabled from the gui
            case '-UNITS-CM-':
                if controller.is_listening:
                    controller.change_length_units_cm(flash=False)
            case '-MODE-TOP-':
                if controller.is_listening:
                    controller.change_board_output_mode('top')
            case '-MODE-LENGTH-':
                if controller.is_listening:
                    controller.change_board_output_mode('length')
            case '-MODE-BOTTOM-':
                if controller.is_listening:
                    controller.change_board_output_mode('bottom')
            case '-MUTE-':
                if controller.is_muted:
                    controller.unmute_board()
                    window['-MUTE-'].update(text='Mute')
                else:
                    controller.mute_board()
                    window['-MUTE-'].update(text='Unmute')
            case 'Guide_en':
                webbrowser.open_new(USER_GUIDE_FILE_ENGLISH)
            # case 'Guide_fr':
            #     webbrowser.open_new(USER_GUIDE_FILE_FRANÇAIS)

        refresh_layout(window, controller)

        time.sleep(REFRESH_PERIOD)

    window.close()


def refresh_layout(window: sg.Window, controller: Dcs5Controller):
    if (configs_path := sg.user_settings()['configs_path']) is not None:
        window['-CONFIGS-'].update(Path(configs_path).name)
    else:
        window['-CONFIGS-'].update('No Config Selected')
    if controller is not None:
        _refresh_marel_layout(window, controller)
        _refresh_controller_layout(window, controller)
    else:
        for key in [
            '-MAREL_START-', '-MAREL_STOP-',
            '-MAREL_HOST-', '-MAREL_UNITS-', #'-MAREL_AUTO_ENTER-',
            '-CONNECT-', '-ACTIVATE-',
            '-DISCONNECT-', '-RESTART-',
            '-MUTE-',
            '-SYNC-', '-CALIBRATE-',
            '-CALPTS-', '-BACKLIGHT-',
            '-UNITS-MM-', '-UNITS-CM-',
            '-MODE-TOP-', '-MODE-BOTTOM-', '-AUTO_ENTER-',
            '-MODE-LENGTH-'
        ]:
            window[key].update(disabled=True)
        for key in ['-CONNECTED_LED-', '-ACTIVATED_LED-', '-SYNC_LED-', '-MUTED_LED-', '-CAL_LED-', '-MAREL_LED-']:
            window[key].update(**LED_OFF)


def _refresh_marel_layout(window: sg.Window, controller: Dcs5Controller):
    if controller.marel is not None:
        window["-MAREL_UNITS-"].update(disabled=False)

        if controller.marel.is_listening:
            window["-MAREL_STOP-"].update(disabled=False)

        if controller.marel.client.is_connecting:
            window["-MAREL_STOP-"].update(disabled=False)
            window["-MAREL_LED-"].update(**LED_WAIT)
            window["-MAREL_WEIGHT-"].update("N/A")
            window["-MAREL_WEIGHT_DEVICE-"].update("N/A")
        elif controller.marel.client.is_connected and controller.marel.is_listening:
            # elif controller.marel.is_listening:
            #     if controller.marel.client.is_connected:
            #         window["-MAREL_LED-"].update(**LED_ON)
            window["-MAREL_LED-"].update(**LED_ON)
            window["-MAREL_HOST-"].update(disabled=True)
            window["-MAREL_START-"].update(disabled=True)
            window["-MAREL_STOP-"].update(disabled=False)
            window["-MAREL_WEIGHT-"].update(f"{controller.marel.get_weight(controller.marel.units)} {controller.marel.units}")
            window["-MAREL_WEIGHT_DEVICE-"].update(f"{controller.marel.get_weight(controller.marel.units)} {controller.marel.units}")
        else:
            window["-MAREL_HOST-"].update(disabled=False)
            window["-MAREL_START-"].update(disabled=False)
            window["-MAREL_STOP-"].update(disabled=True)
            window["-MAREL_LED-"].update(**LED_OFF)
            window["-MAREL_WEIGHT-"].update("N/A")
            window["-MAREL_WEIGHT_DEVICE-"].update("N/A")
    else:
        window["-MAREL_UNITS-"].update(disabled=True)
        #window["-MAREL_AUTO_ENTER-"].update(disabled=True)
        window["-MAREL_START-"].update(disabled=False)
        window["-MAREL_STOP-"].update(disabled=True)
        window["-MAREL_LED-"].update(**LED_OFF)
        window["-MAREL_WEIGHT-"].update("N/A")
        window["-MAREL_WEIGHT_DEVICE-"].update("N/A")


def _refresh_controller_layout(window: sg.Window, controller: Dcs5Controller):
    window['-NAME-'].update(dotted(controller.config.client.device_name + " ", DEVICE_LAYOUT_PADDING, 'right'))
    window['-MODEL-'].update(
        dotted(controller.devices_specifications.control_box.model + " ", DEVICE_LAYOUT_PADDING, 'right'))
    window['-MAC-'].update(dotted(controller.config.client.mac_address + " ", DEVICE_LAYOUT_PADDING, 'right'))

    window['-SETTLING-DELAY-'].update(controller.internal_board_state.stylus_settling_delay)
    window['-NUMBER-READING-'].update(controller.internal_board_state.number_of_reading)
    window['-MAX-DEVIATION-'].update(controller.internal_board_state.stylus_max_deviation)

    if controller.auto_enter:
        window['-AUTO_ENTER-'].update('On')
    else:
        window['-AUTO_ENTER-'].update('Off')
    window["-AUTO_ENTER-"].update(disabled=False)

    window['-STYLUS-'].update(value=controller.stylus,
                              values=list(controller.devices_specifications.stylus_offset.keys()))
    window['-STYLUS-'].update(value=controller.stylus)
    window['-STYLUS_OFFSET-'].update(value=controller.stylus_offset)

    if controller.is_muted:
        window['-MUTED_LED-'].update(**LED_ON)
    else:
        window['-MUTED_LED-'].update(**LED_OFF)
    window['-MUTE-'].update(disabled=False)

    if controller.client.is_connected:
        window["-DISCONNECT-"].update(disabled=False)
        window["-CONNECTED_LED-"].update(**LED_ON)
        window["-CONNECT-"].update(disabled=True)
        window["-RESTART-"].update(disabled=False)

        window['-PORT-'].update(dotted(str(controller.client.port) + " " or "N/A ", DEVICE_LAYOUT_PADDING, 'right'))
        window['-SYNC-'].update(disabled=False)

        if controller.internal_board_state.firmware is not None:
            window['-FIRMWARE-'].update(
                dotted(controller.internal_board_state.firmware + " ", DEVICE_LAYOUT_PADDING, 'right'))

        if controller.internal_board_state.cal_pt_1 is not None \
                and controller.internal_board_state.cal_pt_2 is not None:
            window['-CALIBRATE-'].update(disabled=False)
        else:
            window['-CALIBRATE-'].update(disabled=True)

        if controller.is_listening:
            if (battery := controller.internal_board_state.battery_level) is not None:
                window["-BATTERY-"].update(f"{battery}%")
            if (charging := controller.internal_board_state.is_charging) is not None:
                window["-CHARGING-"].update('yes' if charging else 'no')
            if (temperature := controller.internal_board_state.temperature) is not None:
                window["-TEMPERATURE-"].update(f"{temperature}°C")
            if (humidity := controller.internal_board_state.humidity) is not None:
                window["-HUMIDITY-"].update(f"{humidity}%")

            window['-CALPTS-'].update(disabled=False)

            window["-ACTIVATED_LED-"].update(**LED_ON)
            window["-ACTIVATE-"].update(disabled=True)

            window['-MODE-TOP-'].update(disabled=not controller.output_mode != 'top', disabled_button_color=SELECTED_BUTTON_COLOR)
            window['-MODE-LENGTH-'].update(disabled=not controller.output_mode != 'length', disabled_button_color=SELECTED_BUTTON_COLOR)
            window['-MODE-BOTTOM-'].update(disabled=not controller.output_mode != 'bottom', disabled_button_color=SELECTED_BUTTON_COLOR)

            window['-UNITS-MM-'].update(disabled=controller.length_units == 'mm', disabled_button_color=SELECTED_BUTTON_COLOR)
            window['-UNITS-CM-'].update(disabled=controller.length_units == 'cm', disabled_button_color=SELECTED_BUTTON_COLOR)

            if controller.internal_board_state.backlighting_level is not None:
                backlight_level = round(
                    (
                                controller.internal_board_state.backlighting_level / controller.control_box_parameters.max_backlighting_level) * BACKLIGHT_SLIDER_MAX
                )
                window['-BACKLIGHT-'].update(disabled=False,
                                             value=backlight_level)  # or None ? Removed
            if controller.socket_listener.last_key is not None:
                window['-LAST_KEY-'].update('< ' + str(controller.socket_listener.last_key) + ' >')
                window['-LAST_COMMAND-'].update('< ' + str(controller.socket_listener.last_command) + ' >')
            else:
                window['-LAST_KEY-'].update('-')
                window['-LAST_COMMAND-'].update('-')

        else:
            window["-ACTIVATED_LED-"].update(**LED_OFF)
            window["-ACTIVATE-"].update(disabled=False)

            window['-BACKLIGHT-'].update(disabled=True, value=None)

            window['-MODE-TOP-'].update(disabled=True)
            window['-MODE-LENGTH-'].update(disabled=True)
            window['-MODE-BOTTOM-'].update(disabled=True)
            window['-UNITS-MM-'].update(disabled=True)
            window['-UNITS-CM-'].update(disabled=True)

        if controller.is_sync:
            window["-SYNC_LED-"].update(**LED_ON)
        else:
            window["-SYNC_LED-"].update(**LED_OFF)

        if controller.internal_board_state.calibrated is True:
            window["-CAL_LED-"].update(**LED_ON)
        else:
            window["-CAL_LED-"].update(**LED_OFF)

        if 'shift' in controller.shouter.meta_key_combo:
            window["-SHIFT-"].update(**META_ON)
        else:
            window["-SHIFT-"].update(**META_OFF)
        if 'ctrl' in controller.shouter.meta_key_combo:
            window["-CTRL-"].update(**META_ON)
        else:
            window["-CTRL-"].update(**META_OFF)
        if 'alt' in controller.shouter.meta_key_combo:
            window["-ALT-"].update(**META_ON)
        else:
            window["-ALT-"].update(**META_OFF)
        if controller.socket_listener.with_mode is True:
            window["-META-"].update(**META_ON)
        else:
            window["-META-"].update(**META_OFF)

    else:
        window['-MODE-TOP-'].update(disabled=True, disabled_button_color=DISABLED_BUTTON_COLOR)
        window['-MODE-LENGTH-'].update(disabled=True, disabled_button_color=DISABLED_BUTTON_COLOR)
        window['-MODE-BOTTOM-'].update(disabled=True, disabled_button_color=DISABLED_BUTTON_COLOR)

        window['-UNITS-MM-'].update(disabled=True, disabled_button_color=DISABLED_BUTTON_COLOR)
        window['-UNITS-CM-'].update(disabled=True, disabled_button_color=DISABLED_BUTTON_COLOR)

        window["-DISCONNECT-"].update(disabled=True)
        window['-BACKLIGHT-'].update(disabled=True, value=None)

        window["-SYNC_LED-"].update(**LED_OFF)
        window['-SYNC-'].update(disabled=True)

        window["-CAL_LED-"].update(**LED_OFF)
        window['-CALIBRATE-'].update(disabled=True)
        window['-CALPTS-'].update(disabled=True)

        window['-ACTIVATE-'].update(disabled=True)
        window['-ACTIVATED_LED-'].update(**LED_OFF)

        window['-LAST_KEY-'].update('-')
        window['-LAST_COMMAND-'].update('-')

        for field in ["-BATTERY-", "-CHARGING-", "-TEMPERATURE-", "-HUMIDITY-"]:
            window[field].update("N\A")

        if window.metadata['is_connecting']:
            window["-CONNECTED_LED-"].update(**LED_WAIT)
            window["-CONNECT-"].update(disabled=True)
            window["-RESTART-"].update(disabled=True)

        else:
            window["-CONNECTED_LED-"].update(**LED_OFF)
            window["-CONNECT-"].update(disabled=False)
            window["-RESTART-"].update(disabled=False)


def popup_window_set_calibration_pt(controller: Dcs5Controller):
    layout = [
        [sg.Text('Enter calibration point values in mm')],
        [sg.Text('Point 1: ', size=(7, 1), font=FRAME_FONT),
         sg.InputText(default_text=controller.internal_board_state.cal_pt_1, key='cal_pt_1', size=(4, 1),
                      justification='c', font=FRAME_FONT, enable_events=True),
         sg.Text('mm', size=(3, 1), font=FRAME_FONT)],
        [sg.Text('Point 2: ', size=(7, 1), font=FRAME_FONT),
         sg.InputText(default_text=controller.internal_board_state.cal_pt_2, key='cal_pt_2', size=(4, 1),
                      justification='c', font=FRAME_FONT),
         sg.Text('mm', size=(3, 1), font=FRAME_FONT)],
        [sg.Submit(), sg.Cancel()]
    ]

    window = sg.Window('Calibration points', layout, element_justification='center', keep_on_top=True,
                       enable_close_attempted_event=True)

    while True:
        event, values = window.read(timeout=0.5)
        window['cal_pt_1'].bind("<Return>", "_Enter")
        if event is None:
            break

        if event in '__TIMEOUT__':
            pass
        else:
            print(event, values)

        if event in ["Cancel", "-WINDOW CLOSE ATTEMPTED-"]:
            window.close()
            break

        if event == "cal_pt_1_Enter":
            if values['cal_pt_1']:
                window['cal_pt_2'].set_focus()

        elif event == "Submit":
            if values['cal_pt_1'].isnumeric() and values['cal_pt_2'].isnumeric():
                controller.c_set_calibration_points_mm(1, int(values['cal_pt_1']))
                controller.c_set_calibration_points_mm(2, int(values['cal_pt_2']))
                break
            else:
                window.keep_on_top_clear()
                sg.popup_error('Invalid values.', title='Error', keep_on_top=True, non_blocking=False)
                window.keep_on_top_set()
        else:
            sg.SetOptions(window_location=get_new_location(window))

    window.close()


def popup_window_calibrate(controller: Dcs5Controller):
    """Test closing on perform_long_operation"""
    cal_pt_values = {1: controller.internal_board_state.cal_pt_1, 2: {controller.internal_board_state.cal_pt_2}}
    for i in [1, 2]:
        layout = [
            [sg.Text(f'Set Stylus down for calibration point {i}: {cal_pt_values[i]} mm', pad=(5, 5), font=FRAME_FONT)],
        ]
        window = sg.Window(f'Calibrate point {i}', layout, finalize=True, element_justification='center',
                           keep_on_top=True)
        window.perform_long_operation(lambda: controller.calibrate(i), end_key=f'-cal_pt_{i}-')

        while True:
            event, values = window.read(timeout=0.1)

            if event == '__TIMEOUT__':
                pass

            if event == "Cancel":
                window.close()
                break
            elif event == f"-cal_pt_{i}-":
                break
            else:
                sg.SetOptions(window_location=get_new_location(window))
        window.close()

        if values[0] == 1:
            sg.popup_ok('Calibration successful.', keep_on_top=True)
        else:
            sg.popup_ok('Calibration failed.', keep_on_top=True)


def config_window():
    if (current_config := get_current_config()) is None:
        current_config = 'No configuration loaded.'

    select_layout = [
        [sg.Text('Current:', font=REG_FONT, justification='left', pad=(0, 0)),
         sg.Text(current_config, font=REG_FONT_BOLD, key='-CONFIGURATION-', background_color='white', pad=(0, 0))],
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

    window = sg.Window('Configurations', layout, element_justification='center', modal=True)

    return window


def popup_window_select_config(controller: Dcs5Controller = None) -> Dcs5Controller:
    current_config = get_current_config()

    window = config_window()

    while True:
        event, values = window.read(timeout=0.1)

        if event == '__TIMEOUT__':
            pass

        if event in ['Close', sg.WIN_CLOSED]:
            break
        else:
            sg.SetOptions(window_location=get_new_location(window))

        if event == 'New':
            window.DisableClose = True
            _ = create_new_configs()
            window.DisableClose = False

            window['-CONFIG-'].update(values=list_configs(), set_to_index=[])
            window['Load'].update(disabled=True)
            window['Delete'].update(disabled=True)
            window['-EDIT-'].update(disabled=True)
            window['Edit'].update(disabled=True)

        elif values is not None:
            if values['-CONFIG-'] is not None:
                if len(values['-CONFIG-']) != 0:
                    window['Load'].update(disabled=False)
                    window['Delete'].update(disabled=False)
                    window['-EDIT-'].update(disabled=False)
                    if len(values['-EDIT-']) != 0:
                        window['Edit'].update(disabled=False)

                    if event == 'Load':
                        selected_config_path = str(Path(CONFIG_FILES_PATH).joinpath(values['-CONFIG-'][0]))

                        sg.user_settings()['previous_configs_path'] = sg.user_settings()['configs_path']
                        sg.user_settings()['configs_path'] = selected_config_path

                        if controller is None:
                            controller = modal(window, init_dcs5_controller)
                        else:
                            modal(window, reload_controller_config, controller)

                        current_config = get_current_config()

                    if event == 'Delete':
                        if values['-CONFIG-'][0] == current_config:
                            modal(window, sg.popup_ok, 'Cannot delete the configuration currently in use.',
                                        title='Deletion error', keep_on_top=True, modal=True)
                        elif modal(window, sg.popup_yes_no, f"Are you sure you want to delete `{values['-CONFIG-'][0]}`",
                                             keep_on_top=True, modal=True) == 'Yes':
                            shutil.rmtree(str(Path(CONFIG_FILES_PATH).joinpath(values['-CONFIG-'][0])))

                            window['-CONFIG-'].update(list_configs(), set_to_index=[])
                            window['Load'].update(disabled=True)
                            window['Delete'].update(disabled=True)
                            window['-EDIT-'].update(disabled=True)
                            window['Edit'].update(disabled=True)

                    if event == 'Edit':
                        config_path = Path(CONFIG_FILES_PATH).joinpath(values['-CONFIG-'][0])
                        match values['-EDIT-'][0]:
                            case 'Controller Configuration':
                                click.edit(filename=str(config_path.joinpath(CONTROLLER_CONFIGURATION_FILE_NAME)))
                            case 'Devices Specification':
                                click.edit(filename=str(config_path.joinpath(DEVICES_SPECIFICATION_FILE_NAME)))

                        if values['-CONFIG-'][0] == current_config:
                            sg.user_settings()['previous_configs_path'] = current_config + '*'
                            if modal(window, sg.popup_yes_no, 'Do you want to reload the configuration ?', keep_on_top=True,
                                               modal=True) == 'Yes':
                                modal(window, reload_controller_config, controller)

                if (current_config := get_current_config()) is not None:
                    window['-CONFIGURATION-'].update(current_config)
                else:
                    window['-CONFIGURATION-'].update('No Config Selected')
        window.bring_to_front()
    window.close()

    return controller


def get_current_config():
    return Path(sg.user_settings()['configs_path']).name if sg.user_settings()['configs_path'] is not None else None


def list_configs():
    return [x.name for x in Path(CONFIG_FILES_PATH).iterdir() if x.is_dir()]


def new_config_window():
    model_layout = [[sg.Text('Model: ', font=REG_FONT),
                     sg.DropDown(['xt', 'micro'], default_value='xt', size=(20, 4), enable_events=False, font=REG_FONT, readonly=True,
                                  key='-MODEL-')]]
    path_layout = [
        [sg.Text('Name:  ', font=REG_FONT), sg.InputText(key='-PATH-', font=REG_FONT, size=[20, 1], default_text=None)]]
    submit_layout = [[
        button('Create', size=(6, 1), button_color=('black', "orange")),
        button('Close', size=(6, 1), button_color=ENABLED_BUTTON_COLOR)
    ]]

    global_layout = [model_layout, path_layout, submit_layout]

    window = sg.Window('Configurations', global_layout, element_justification='center', keep_on_top=True, modal=True)

    return window


def create_new_configs():
    window = new_config_window()
    while True:
        event, values = window.read()
        if event in ['Close', sg.WIN_CLOSED]:
            break

        if event is None or event == 'Create':
            if values['-PATH-']:
                if Path(values['-PATH-']).name in list_configs():
                    window.keep_on_top_clear()
                    if modal(window, sg.popup_yes_no,
                             'Configuration name already exists. Do you want to overwrite it ?',
                             title='Warning', keep_on_top=True) == 'No':
                        break
                    window.keep_on_top_set()

                new_config_path = copy_config_files(values['-PATH-'], values['-MODEL-'])

                window.close()
                return new_config_path
    window.close()
    return None


def copy_config_files(dest_path: str, model: str):
    new_config_path = CONFIG_FILES_PATH.joinpath(dest_path)
    new_config_path.mkdir(parents=True, exist_ok=True)

    if model == 'xt':
        default_files = [XT_DEFAULT_CONTROLLER_CONFIGURATION_FILE, XT_DEFAULT_DEVICES_SPECIFICATION_FILE]
    else:
        default_files = [MICRO_DEFAULT_CONTROLLER_CONFIGURATION_FILE,
                         MICRO_DEFAULT_DEVICES_SPECIFICATION_FILE]

    local_files = [new_config_path.joinpath(fn) for fn in
                   (CONTROLLER_CONFIGURATION_FILE_NAME, DEVICES_SPECIFICATION_FILE_NAME)]

    for lf, df in zip(local_files, default_files):
        if not Path(lf).exists():
            shutil.copyfile(df, lf)
        else:
            shutil.copyfile(df, lf)
            logging.debug(f'Writing file: {lf}')

    return new_config_path


def reload_controller_config(controller: Dcs5Controller):
    update_controller_config_paths(controller)
    try:
        controller.reload_configs()
        logging.debug('Controller reloaded.')
        if controller.client.is_connected:
            if sg.popup_yes_no('Do you want to synchronize board ?', keep_on_top=True) == "yes":
                controller.init_controller_and_board()
        sg.user_settings()['configs_path'] = sg.user_settings()['configs_path'].strip('*')

    except ConfigError as err:
        logging.debug(f'ConfigError while loading config files.\n {err}')
        sg.popup_ok('Could not load the configuration files.\n'
                    ' Error in the configurations files. \n'
                    f'{err}', keep_on_top=True)
        sg.user_settings().update({'configs_path': sg.user_settings()['previous_configs_path']})


def update_controller_config_paths(controller: Dcs5Controller):
    configs_path = sg.user_settings()['configs_path'].strip('*')
    controller.config_path = Path(configs_path).joinpath(CONTROLLER_CONFIGURATION_FILE_NAME)
    controller.devices_specifications_path = Path(configs_path).joinpath(DEVICES_SPECIFICATION_FILE_NAME)
    logging.debug('Config files path updated.')


### gui functions ###

def get_new_location(window: sg.Window) -> Tuple[int, int]:
    x, y = window.current_location(more_accurate=True)
    w, h = window.size

    return x, y + int(h / 2)


def dotted(value, length=50, justification='left'):
    ndots = length - len(value)
    if justification == 'left':
        return value + ' ' + '.' * ndots
    elif justification == 'right':
        return '.' * ndots + ' ' + value


def led(key=None):
    return sg.Text(EMPTY_CIRCLE, key=key, text_color='red', font=LED_FONT)


def ibutton(label, size, key=None,
            button_color=ENABLED_BUTTON_COLOR,
            disabled_button_color=DISABLED_BUTTON_COLOR,
            disabled=False):
    return sg.Button(label, size=size,
                     font=REG_FONT,
                     pad=(1, 1),
                     button_color=button_color,
                     border_width=1,
                     disabled_button_color=disabled_button_color,
                     key=key or label,
                     disabled=disabled,
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


def modal(window: sg.Window, func: callable, *args, **kwargs) -> Any:
    """Disable the current window `Close` action while `func` is running.

    Used for popup window.

    Parameters
    ----------
    window:
        current window.

    func:
        Function to execute while the current window `Close` action is disabled.


    """
    window.DisableClose = True
    out = func(*args, **kwargs)
    window.DisableClose = False
    return out


def update_marel_host(controller: Dcs5Controller, value):
    controller.config.client.marel_ip_address = value
    update_json_value(controller.config_path, ['client', 'marel_ip_address'],
                      str(controller.config.client.marel_ip_address))
    logging.debug(f'Marel Host address updated {value}')


if __name__ == "__main__":
    main()
#    c.start_client()
# c.start_listening()
