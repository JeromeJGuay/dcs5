"""
"""
import logging
import os
import shutil
import webbrowser
from pathlib import Path

import PySimpleGUI as sg
import click
import pyautogui as pag

from dcs5 import VERSION, \
    LOCAL_FILE_PATH, \
    SERVER_CONFIGURATION_FILE_NAME, \
    CONTROLLER_CONFIGURATION_FILE_NAME, \
    DEVICES_SPECIFICATION_FILE_NAME, \
    CONTROL_BOX_PARAMETERS_FILE_NAME, \
    DEFAULT_SERVER_CONFIGURATION_FILE, \
    DEFAULT_CONTROLLER_CONFIGURATION_FILE, \
    DEFAULT_DEVICES_SPECIFICATION_FILE, \
    DEFAULT_CONTROL_BOX_PARAMETERS, \
    CONFIG_FILES_PATH, \
    USER_GUIDE_FILE
from dcs5.controller import Dcs5Controller
from dcs5.controller_configurations import ConfigError
from dcs5.logger import init_logging

if os.environ.get('EDITOR') == 'EMACS':
    print('Text editor changed.')
    os.environ.update({'EDITOR': 'pluma'})  # FIXME


def scale_font(font_size: int) -> int:
    monitor_width, monitor_height = pag.size()
    return int(font_size * monitor_height / 1080)


SMALL_FONT = f'Courier {scale_font(8)}'

REG_FONT = f'Courier {scale_font(10)}'
REG_FONT_BOLD = REG_FONT + ' bold'

TAB_FONT = f'Courier {scale_font(12)}'

HEADER_FONT = f'Courier {scale_font(20)}'

EMPTY_CIRCLE = '\u25CB'

LED_FONT = f'Courier {scale_font(16)}'

LED_ON = {'value': '\u2B24', 'text_color': 'Green', 'font': TAB_FONT}
LED_WAIT = {'value': '\u25B2', 'text_color': 'Orange', 'font': LED_FONT}
LED_OFF = {'value': '\u25CB', 'text_color': 'Red', 'font': LED_FONT + ' bold'}


ENABLED_BUTTON_COLOR = ('black', "light blue")
DISABLED_BUTTON_COLOR = ('gray', "light grey")
SELECTED_BUTTON_COLOR = ('OrangeRed', "light grey")

META_OFF = {'text_color': 'gray', 'background_color': 'light grey'}
META_ON = {'text_color': 'black', 'background_color': 'gold'}

LOGO = '../static/bigfin_logo.png'
USER_SETTING_FILE = 'user_settings.json'


def main():
    init_logging(stdout_level='DEBUG')
    run()
    exit()


def init_dcs5_controller():
    controller_config_path = Path(sg.user_settings()['configs_path']).joinpath(CONTROLLER_CONFIGURATION_FILE_NAME)
    devices_specifications_path = Path(sg.user_settings()['configs_path']).joinpath(DEVICES_SPECIFICATION_FILE_NAME)
    control_box_parameters_path = Path(sg.user_settings()['configs_path']).joinpath(CONTROL_BOX_PARAMETERS_FILE_NAME)

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

    restart_layout = [sg.Push(),
                      sg.Button('Restart', size=(11, 1),
                                font=REG_FONT,
                                pad=(1, 1),
                                button_color=('white', 'red3'),
                                border_width=1,
                                disabled_button_color=DISABLED_BUTTON_COLOR,
                                key='-RESTART-',
                                )]
    _status_layout = col([connection_layout, activate_layout, mute_layout])
    status_layout = [[sg.Frame('Status', [_status_layout, restart_layout], font=TAB_FONT, expand_x=True)]]

    ### SYNC
    _sync_layout = [
        [sg.Text('Synchronized', font=REG_FONT), led(key='-SYNC_LED-')],
        [ibutton('Synchronize', size=(15, 1), key='-SYNC-'), ]]
    sync_layout = [[sg.Frame('Synchronize', _sync_layout, font=TAB_FONT)]]

    ### CALIBRATION
    _calibration_layout = [
        [sg.Text('Calibrated', font=REG_FONT), led(key='-CAL_LED-')],
        [ibutton('Calibrate', size=(15, 1), key='-CALIBRATE-'),
         ibutton('Set Cal. Pts.', size=(15, 1), key='-CALPTS-')]]  # TODO
    calibration_layout = [[sg.Frame('Calibration', _calibration_layout, font=TAB_FONT)]]

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
    reading_profile_layout = [[sg.Frame('Reading Profile', _reading_profile_layout, font=TAB_FONT)]]

    ### LAST COMMAND
    _last_command_layout = [[sg.Text('Key'), sg.Text("", font=REG_FONT_BOLD, size=(10, 1), p=(1, 1), relief='solid',
                                                     border_width=2, justification='c', background_color='white',
                                                     key="-LAST_KEY-"),
                            sg.Text('Command'), sg.Text("", font=REG_FONT_BOLD, size=(20, 1), p=(1, 1), relief='solid',
                                                        border_width=2, justification='c', background_color='white',
                                                        key="-LAST_COMMAND-")]]
    last_command_layout = [[sg.Frame('Last Inputs', _last_command_layout, font=TAB_FONT)]]

    ### BACKLIGHT
    _backlight_layout = [sg.Slider(orientation='h', key='-BACKLIGHT-', font=SMALL_FONT, enable_events=True)]
    backlight_layout = [[sg.Frame('Backlight level', [_backlight_layout], font=REG_FONT)]]

    ### UNITS
    _units_layout = [[ibutton('mm', size=(5, 1), key='-UNITS-MM-', disabled_button_color=SELECTED_BUTTON_COLOR),
                      ibutton('cm', size=(5, 1), key='-UNITS-CM-', disabled_button_color=SELECTED_BUTTON_COLOR)]]
    units_layout = [[sg.Frame('Units', _units_layout, font=TAB_FONT)]]

    ### STYLUS
    _stylus_layout = [[sg.Combo(values=[''], key='-STYLUS-', enable_events=True, size=(10,1),pad=(1,1), font=REG_FONT),
                       sg.Text('Offset:', font=REG_FONT),
                       sg.Text("-", font=REG_FONT_BOLD, background_color='white',
                               size=(3, 1), p=(1, 0), justification='c', key='-STYLUS_OFFSET-')
                      ]]
    stylus_layout = [[sg.Frame('Stylus', _stylus_layout, font=TAB_FONT)]]

    ### MODE
    _mode_layout = [[ibutton('Top', size=(8, 1), key='-MODE-TOP-', disabled_button_color=SELECTED_BUTTON_COLOR),
                     ibutton('Length', size=(8, 1), key='-MODE-LENGTH-', disabled_button_color=SELECTED_BUTTON_COLOR),
                     ibutton('Bottom', size=(8, 1), key='-MODE-BOTTOM-', disabled_button_color=SELECTED_BUTTON_COLOR)]]
    mode_layout = [[sg.Frame('Mode', _mode_layout, font=TAB_FONT)]]
    ###
    _meta_layout = [[sg.Text('Mode', font=REG_FONT_BOLD, border_width=2, relief='solid', **META_OFF, size=(6, 1),
                             justification='center', pad=(1, 1), key='-META-'),
                     sg.Text('Shift', font=REG_FONT_BOLD, border_width=2, relief='solid', **META_OFF, size=(6, 1),
                             justification='center', pad=(1, 1), key='-SHIFT-'),
                     sg.Text('Ctrl', font=REG_FONT_BOLD, border_width=2, relief='solid', **META_OFF, size=(6, 1),
                             justification='center', pad=(1, 1), key='-CTRL-'),
                     sg.Text('Alt', font=REG_FONT_BOLD, border_width=2, relief='solid', **META_OFF, size=(6, 1),
                             justification='center', pad=(1, 1), key='-ALT-')]]
    meta_layout = [[sg.Frame('Meta Key', _meta_layout, font=TAB_FONT)]]

    controller_tab_layout = [
        col([device_layout]),
        col([status_layout]),
        col([reading_profile_layout, sync_layout]),
        col([calibration_layout]),
        col([units_layout, mode_layout]),
        col([meta_layout]),
        col([last_command_layout]),
        col([stylus_layout, backlight_layout]),
    ]

    # --- MENU ---#

    _menu_layout = [
        ['&Dcs5', [
            '&Configuration',
            '---',
            '&Exit']],
        ['Help', ['Guide']]
    ]

    menu_layout = [sg.Menu(_menu_layout, k='-MENU-', p=0, font=REG_FONT, disabled_text_color='grey'), ]

    # --- GLOBAL ---#
    global_layout = [menu_layout]

    global_layout += [[controller_tab_layout]]

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
    sg.user_settings_filename(USER_SETTING_FILE, LOCAL_FILE_PATH)
    load_user_settings()

    sg.theme('lightgrey')
    sg.theme_border_width(.2)
    sg.set_options(
        icon=LOGO,
        auto_size_buttons=True,
        use_ttk_buttons=True,
    )

    window = make_window()

    window.metadata = {
        'is_connecting': False,
        'previous_configs_path': None,
    }

    if sg.user_settings()['configs_path'] is not None:
        controller = init_dcs5_controller()
    else:
        controller = popup_window_select_config()

    init_layout(window, controller)

    loop_run(window, controller)

    save_user_settings()


def init_layout(window: sg.Window, controller: Dcs5Controller):
    if controller is not None:
        window['-BACKLIGHT-'].update(range=(0, controller.control_box_parameters.max_backlighting_level))
    refresh_layout(window, controller)


def loop_run(window: sg.Window, controller: Dcs5Controller):
    while True:
        event, values = window.read(timeout=.05)

        if event != "__TIMEOUT__" and event is not None:
            logging.debug(f'{event}, {values}')

        match event:
            case sg.WIN_CLOSED | 'Exit':
                if controller is not None:
                    controller.close_client()
                break
            case "-CONNECT-":
                window.metadata['is_connecting'] = True
                window.perform_long_operation(controller.start_client, end_key='-END_CONNECT-')
            case "-END_CONNECT-":
                window.metadata['is_connecting'] = False
                if not controller.client.is_connected:
                    sg.popup_ok(controller.client.error_msg,  title='Failed.', keep_on_top=True, font=REG_FONT)
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
                logging.debug('sync not mapped')
            case "-CALPTS-":
                popup_window_set_calibration_pt(controller)
            case "-CALIBRATE-":
                popup_window_calibrate(controller)
            case 'Configuration':
                controller = popup_window_select_config(controller=controller)
            case '-STYLUS-':
                controller.change_stylus(values['-STYLUS-'], flash=False)
            case '-BACKLIGHT-':
                controller.c_set_backlighting_level(int(values['-BACKLIGHT-']))
            case '-UNITS-MM-':
                controller.change_length_units_mm(flash=False)
            case '-UNITS-CM-':
                controller.change_length_units_cm(flash=False)
            case '-MODE-TOP-':
                controller.change_board_output_mode('top', flash=False)
            case '-MODE-LENGTH-':
                controller.change_board_output_mode('length', flash=False)
            case '-MODE-BOTTOM-':
                controller.change_board_output_mode('bottom', flash=False)
            case '-MUTE-':
                if controller.is_muted:
                    controller.unmute_board()
                    window['-MUTE-'].update(text='Mute')
                else:
                    controller.mute_board()
                    window['-MUTE-'].update(text='Unmute')
            case 'Guide':
                webbrowser.open_new(USER_GUIDE_FILE)

        refresh_layout(window, controller)

    window.close()


def refresh_layout(window: sg.Window, controller: Dcs5Controller):
    if (configs_path := sg.user_settings()['configs_path']) is not None:
        window['-CONFIGS-'].update(Path(configs_path).name)
    else:
        window['-CONFIGS-'].update('No Config Selected')
    if controller is not None:
        _controller_refresh_layout(window, controller)
    else:
        for key in ['-CONNECT-', '-ACTIVATE-',
                    '-RESTART-', f'-MUTE-',
                    '-SYNC-', '-CALIBRATE-',
                    '-CALPTS-', '-BACKLIGHT-',
                    '-UNITS-MM-', '-UNITS-CM-',
                    '-MODE-TOP-', '-MODE-BOTTOM-',
                    '-MODE-LENGTH-']:
            window[key].update(disabled=True)
        for key in ['-CONNECTED_LED-', '-ACTIVATED_LED-', '-SYNC_LED-', '-MUTED_LED-', '-CAL_LED-']:
            window[key].update(**LED_OFF)


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

    window['-STYLUS-'].update(value=controller.stylus, values=list(controller.devices_spec.stylus_offset.keys()))
    window['-STYLUS-'].update(value=controller.stylus)
    window['-STYLUS_OFFSET-'].update(value=controller.stylus_offset)

    if controller.is_muted:
        window['-MUTED_LED-'].update(**LED_ON)
    else:
        window['-MUTED_LED-'].update(**LED_OFF)
    window['-MUTE-'].update(disabled=False)

    if controller.client.is_connected:
        window["-CONNECTED_LED-"].update(**LED_ON)
        window["-CONNECT-"].update(disabled=True)
        window["-RESTART-"].update(disabled=False)

        window['-PORT-'].update(dotted(str(controller.client.port) + " " or "N/A ", DEVICE_LAYOUT_PADDING, 'right'))
        window['-SYNC-'].update(disabled=False)

        if controller.internal_board_state.cal_pt_1 is not None \
                and controller.internal_board_state.cal_pt_2 is not None:
            window['-CALIBRATE-'].update(disabled=False)
        else:
            window['-CALIBRATE-'].update(disabled=True)

        if controller.is_listening:
            window['-CALPTS-'].update(disabled=False)

            window["-ACTIVATED_LED-"].update(**LED_ON)
            window["-ACTIVATE-"].update(disabled=True)
            window['-BACKLIGHT-'].update(disabled=False,
                                         value=controller.internal_board_state.backlighting_level) #  or None ? Removed
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
        [sg.Text('Point 1: ', size=(7, 1), font=TAB_FONT),
         sg.InputText(default_text=controller.internal_board_state.cal_pt_1, key='cal_pt_1', size=(4, 1), justification='c', font=TAB_FONT),
         sg.Text('mm', size=(3, 1), font=TAB_FONT)],
        [sg.Text('Point 2: ', size=(7, 1), font=TAB_FONT),
         sg.InputText(default_text=controller.internal_board_state.cal_pt_2, key='cal_pt_2', size=(4, 1), justification='c', font=TAB_FONT),
         sg.Text('mm', size=(3, 1), font=TAB_FONT)],
        [sg.Submit(), sg.Cancel()]
    ]

    window = sg.Window('Calibration points', layout, element_justification='center', keep_on_top=True)
    while True:
        event, values = window.read()
        if event == "Cancel":
            window.close()
            break
        if event == "Submit":
            if values['cal_pt_1'].isnumeric() and values['cal_pt_2'].isnumeric():
                controller.c_set_calibration_points_mm(1, int(values['cal_pt_1']))
                controller.c_set_calibration_points_mm(2, int(values['cal_pt_2']))
                break
            else:
                sg.popup_ok('Invalid values.', title='error', keep_on_top=True)

    window.close()


def popup_window_calibrate(controller: Dcs5Controller):
    """Test closing on perform_long_operation"""
    cal_pt_values = {1: controller.internal_board_state.cal_pt_1, 2: {controller.internal_board_state.cal_pt_2}}
    for i in [1, 2]:
        layout = [
            [sg.Text(f'Set Stylus down for calibration point {i}: {cal_pt_values[i]} mm', pad=(5,5), font=TAB_FONT)],
        ]
        window = sg.Window(f'Calibrate point {i}', layout, finalize=True, element_justification='center', keep_on_top=True)
        window.perform_long_operation(lambda: controller.calibrate(i), end_key=f'-cal_pt_{i}-')

        while True:
            event, values = window.read(timeout=0.1)
            if event == '__TIMEOUT__':
                pass

            elif event == "Cancel":
                window.close()
                break

            elif event == f"-cal_pt_{i}-":
                break
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

    window = sg.Window('Configurations', layout, element_justification='center', keep_on_top=True)

    return window


def popup_window_select_config(controller: Dcs5Controller = None) -> Dcs5Controller:
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

                        sg.user_settings()['previous_configs_path'] = sg.user_settings()['configs_path']
                        sg.user_settings()['configs_path'] = selected_config_path

                        if controller is None:
                            controller = init_dcs5_controller()
                        else:
                            reload_controller_config(controller)

                        current_config = get_current_config()

                    if event == 'Delete':
                        if value['-CONFIG-'][0] == current_config:
                            sg.popup_ok('Cannot delete the configuration currently in use.',
                                        title='Deletion error', keep_on_top=True)
                        elif sg.popup_yes_no(f"Are you sure you want to delete `{value['-CONFIG-'][0]}`"
                                , keep_on_top=True) == 'Yes':
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
                            sg.user_settings()['previous_configs_path'] = current_config + '*'
                            if sg.popup_yes_no('Do you want to reload the configuration ?', keep_on_top=True) == 'Yes':
                                reload_controller_config(controller)

                if (current_config := get_current_config()) is not None:
                    window['-CONFIGURATION-'].update(current_config)
                else:
                    window['-CONFIGURATION-'].update('No Config Selected')

    window.close()

    return controller


def get_current_config():
    return Path(sg.user_settings()['configs_path']).name if sg.user_settings()['configs_path'] is not None else None


def list_configs():
    return [x.name for x in Path(CONFIG_FILES_PATH).iterdir() if x.is_dir()]


def create_new_configs():
    folder_name = sg.popup_get_text('Enter a configuration name:', default_text=None, font=REG_FONT, keep_on_top=True)
    if folder_name: #not None or empty string
        if Path(folder_name).name in list_configs():
            if sg.popup_yes_no('Configuration name already exists. Do you want to overwrite it ?',
                               title='Warning', keep_on_top=True) == 'No':
                return None

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

        for lf, df in zip(local_files, default_files):
            if not Path(lf).exists():
                shutil.copyfile(df, lf)
            else:
                shutil.copyfile(df, lf)
                logging.debug(f'Writing file: {lf}')

        return new_configs_path

    sg.popup_ok('No name provided. Aborted', title='Warning', keep_on_top=True)
    return None


def reload_controller_config(controller: Dcs5Controller):
    update_controller_config_paths(controller)
    try:
        controller.reload_configs()
        logging.debug('Controller reloaded.')
        if controller.client.is_connected:
            if sg.popup_yes_no('Do you want to synchronize board ?', keep_on_top=True):
                controller.init_controller_and_board()
        sg.user_settings()['configs_path'] = sg.user_settings()['configs_path'].strip('*')

    except ConfigError:
        logging.debug('ConfigError while loading config files.')
        sg.popup_ok('Could not load the configuration files.\n'
                    ' Error in the configurations files. ', keep_on_top=True)
        sg.user_settings().update({'configs_path': sg.user_settings()['previous_configs_path']})


def update_controller_config_paths(controller: Dcs5Controller):
    configs_path = sg.user_settings()['configs_path'].strip('*')
    controller.config_path = Path(configs_path).joinpath(CONTROLLER_CONFIGURATION_FILE_NAME)
    controller.devices_specifications_path = Path(configs_path).joinpath(DEVICES_SPECIFICATION_FILE_NAME)
    controller.control_box_parameters_path = Path(configs_path).joinpath(CONTROL_BOX_PARAMETERS_FILE_NAME)
    logging.debug('Config files path updated.')


### gui element functions ###


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


if __name__ == "__main__":
    main()
