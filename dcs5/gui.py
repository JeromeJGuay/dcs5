#! /usr/bin/env python3
import PySimpleGUI as sg
from controller import *
from utils import json2dict, dict2json
from pathlib import PurePath
import logging
import argparse
import time

# DEFAULT_SETTINGS = json2dict(PurePath(PurePath(__file__).parent, 'configs/default_settings.json'))
#
# CLIENT_SETTINGS = DEFAULT_SETTINGS['client_settings']
# DEVICE_NAME = CLIENT_SETTINGS["DEVICE_NAME"]
# PORT = CLIENT_SETTINGS["PORT"]
# DCS5_ADDRESS = CLIENT_SETTINGS["DCS5_ADDRESS"]
#
# BOARD_SETTINGS = DEFAULT_SETTINGS['board_settings']
# DEFAULT_SETTLING_DELAY = {'measure': BOARD_SETTINGS['DEFAULT_SETTLING_DELAY'], 'typing': 1}
# DEFAULT_MAX_DEVIATION = {'measure': BOARD_SETTINGS['DEFAULT_MAX_DEVIATION'], 'typing': 1}
# DEFAULT_NUMBER_OF_READING = {'measure': BOARD_SETTINGS['DEFAULT_NUMBER_OF_READING'], 'typing': 1}
#
# MAX_SETTLING_DELAY = BOARD_SETTINGS['MAX_SETTLING_DELAY']
# MAX_MAX_DEVIATION = BOARD_SETTINGS['MAX_MAX_DEVIATION']
#
# DEFAULT_BACKLIGHTING_LEVEL = BOARD_SETTINGS['DEFAULT_BACKLIGHTING_LEVEL']
# MIN_BACKLIGHTING_LEVEL = BOARD_SETTINGS['MIN_BACKLIGHTING_LEVEL']
# MAX_BACKLIGHTING_LEVEL = BOARD_SETTINGS['MAX_BACKLIGHTING_LEVEL']
# DEFAULT_BACKLIGHTING_AUTO_MODE = BOARD_SETTINGS['DEFAULT_BACKLIGHTING_AUTO_MODE']
# DEFAULT_BACKLIGHTING_SENSITIVITY = BOARD_SETTINGS['DEFAULT_BACKLIGHTING_SENSITIVITY']
# MIN_BACKLIGHTING_SENSITIVITY = BOARD_SETTINGS['MIN_BACKLIGHTING_SENSITIVITY']
# #MAX_BACKLIGHTING_SENSITIVITY = BOARD_SETTINGS['MAX_BACKLIGHTING_SENSITIVITY']


def make_window(controller: Dcs5Controller):
    width_col1 = 20
    width_col2 = 10
    sg.theme('Topanga')
    row_m = [
        [
            sg.Text(f'Settling delay [0-{MAX_SETTLING_DELAY}]', size=(width_col1, 1)),
            sg.Text('', key='-m_delay-', size=(width_col2, 1), justification='center', enable_events=True,
                    border_width=1),  # , background_color='lightgrey'),
            sg.Input('', key='-m_delay_input-', size=(width_col2, 1), justification='center')
        ],
        [
            sg.Text(f'Max Deviation [0-{MAX_MAX_DEVIATION}]', size=(width_col1, 1)),
            sg.Text('', key='-m_max_deviation-', size=(width_col2, 1), justification='center', enable_events=True, ),
            # , background_color='lightgrey'),
            sg.Input('', key='-m_max_deviation_input-', size=(width_col2, 1), justification='center')
        ],
        [
            sg.Text(f'Number of Reading', size=(width_col1, 1)),
            sg.Text('', key='-m_number_of_reading-', size=(width_col2, 1), justification='center',
                    enable_events=True, ),  # , background_color='lightgrey'),
            sg.Input('', key='-m_number_of_reading_input-', size=(width_col2, 1), justification='center'),
        ],
        [
            sg.Text('', size=(width_col1, 1)),
            sg.Text('', size=(width_col2, 1)),
            sg.Button('Update', key='-update_row_m-', size=(width_col2 - 3, 1), border_width=0),

        ]
    ]
    row_t = [
        [
            sg.Text(f'Settling delay [0-{MAX_SETTLING_DELAY}]', size=(width_col1, 1)),
            sg.Text('', key='-t_delay-', size=(width_col2, 1), justification='center', enable_events=True, ),
            # , background_color='ivory1'),
            sg.Input('', key='-t_delay_input-', size=(width_col2, 1), justification='center')
        ],
        [
            sg.Text(f'Max Deviation [0-{MAX_MAX_DEVIATION}]', size=(width_col1, 1)),
            sg.Text('', key='-t_max_deviation-', size=(width_col2, 1), justification='center', enable_events=True, ),
            # background_color='ivory1'),
            sg.Input('', key='-t_max_deviation_input-', size=(width_col2, 1), justification='center')
        ],
        [
            sg.Text(f'Number of Reading', size=(width_col1, 1)),
            sg.Text('', key='-t_number_of_reading-', size=(width_col2, 1), justification='center',
                    enable_events=True, ),  # background_color='ivory1'),
            sg.Input('', key='-t_number_of_reading_input-', size=(width_col2, 1), justification='center'),
        ],
        [
            sg.Text('', size=(width_col1, 1)),
            sg.Text('', size=(width_col2, 1)),
            sg.Button('Update', key='-update_row_t-', size=(width_col2 - 3, 1), border_width=0),

        ]
    ]
    connection_status = [('\u2B24' + ' Disconnect', 'red'), ('\u2B24' + ' Connect', 'green')]
    client_row = [
        [sg.Text(f'Mac Address:'), sg.Text('', key='-mac_address-')],
        [sg.Text(f'Port:'), sg.Text('', key='-port-')],
        [sg.Text(text=connection_status[0][0], text_color=connection_status[0][1], size=(20, 1), key='INDICATOR')],
        [sg.Column([[sg.Button('Connect'), sg.Button('Disconnect')]], )],
    ]

    row_modes = [[sg.Text('Stylus', justification='center')],
                 [sg.Drop(values=('pen', 'finger'), default_value='pen', size=(10, 2), auto_size_text=True)],
                 ]

    active_status = [('\u2B24' + 'Inactive', 'red'), ('\u2B24' + ' Active', 'green')]
    active_row = [
        [
            sg.Text(text=active_status[0][0], text_color=active_status[0][1], size=(20, 1), key='-active-indicator-'),
            sg.Column([[sg.Button("Activate", button_color='darkgreen'),
            sg.Button("Deactivate", button_color='darkred')]])
        ]
    ]


    layout = [
        [sg.Frame(title='Connection', layout=client_row)],
        [sg.Button('Initialize Board', key='-init-')],
        [sg.Frame(title='Measuring Settings', layout=row_m, font=('Helvetica', 12))],
        [sg.Frame(title='Typing Settings', layout=row_t, font=('Helvetica', 12))],
        [sg.Push(), sg.Button('Update Firmware')],
        [sg.Frame(title='Modes', layout=row_modes, font=('Helvetica', 12))],
        [sg.Frame(title='Status', layout=active_row,font=('Helvetica', 12))]
    ]

    window = sg.Window("DCS5-XT Board Interface", layout, finalize=True, location=(400, 100))
    while True:
        event, values = window.read(timeout=500)
        # End program if user closes window or
        # presses the OK button
        if event == 'Connect':
            try:
                controller.start_client(address=DCS5_ADDRESS, port=PORT)
                window['-mac_address-'].update(controller.client.dcs5_address)
                window['-port-'].update(controller.client.port)
                window['INDICATOR'].update(value=connection_status[1][0], text_color=connection_status[1][1])
            except OSError:
                pass
        elif event == 'Disconnect':
            controller.close_client()
            if controller.client_isconnected is True:
                window['INDICATOR'].update(value=connection_status[0][0], text_color=connection_status[0][1])
        elif event == 'Activate':
            controller.start_listening()
            window['-active-indicator-'].update(value=active_status[1][0], text_color=active_status[1][1])
        elif event == 'Deactivate':
            controller.stop_listening()
            window['-active-indicator-'].update(value=active_status[0][0], text_color=active_status[0][1])
        elif event == '-init-':
            controller.sync_controller_and_board()
        elif event == '-update_row_m-':
            if values['-m_delay_input-'].isnumeric():
                delay = int(values['-m_delay_input-'])
                if 0 <= delay <= MAX_SETTLING_DELAY:
                    controller.stylus_modes_settling_delay['measure'] = values['-m_delay_input-']
            if values['-m_max_deviation_input-'].isnumeric():
                deviation = int(values['-m_max_deviation_input-'])
                if 0 <= deviation <= MAX_MAX_DEVIATION:
                    controller.stylus_modes_max_deviation['measure'] = values['-m_max_deviation_input-']
            if values['-m_number_of_reading_input-'].isnumeric():
                controller.stylus_modes_number_of_reading['measure'] = values['-m_number_of_reading_input-']
            if controller.board_output_mode == 'measure':
                controller.change_board_output_mode('measure')
            window['-m_delay_input-'].update('')
            window['-m_max_deviation_input-'].update('')
            window['-m_number_of_reading_input-'].update('')

        elif event == '-update_row_t-':
            if values['-t_delay_input-'].isnumeric():
                delay = int(values['-t_delay_input-'])
                if 0 <= delay <= MAX_SETTLING_DELAY:
                    controller.stylus_modes_settling_delay['typing'] = values['-t_delay_input-']
            if values['-t_max_deviation_input-'].isnumeric():
                deviation = int(values['-t_max_deviation_input-'])
                if 0 <= deviation <= MAX_MAX_DEVIATION:
                    controller.stylus_modes_max_deviation['typing'] = values['-t_max_deviation_input-']
            if values['-t_number_of_reading_input-'].isnumeric():
                controller.stylus_modes_number_of_reading['typing'] = values['-t_number_of_reading_input-']
            if controller.board_output_mode == 'typing':
                controller.change_board_output_mode('typing')
            window['-t_delay_input-'].update('')
            window['-t_max_deviation_input-'].update('')
            window['-t_number_of_reading_input-'].update('')

        elif event == 'Update Firmware':
            update_file = sg.popup_get_file('Select firmware update file')
        elif event == sg.WIN_CLOSED:
            break

        controller_values = get_controller_values(controller)
        for key, cvalue in controller_values.items():
            if window[key].get() != cvalue:
                window[key].update(cvalue)

    window.close()


def get_controller_values(controller: Dcs5Controller):
    return {'-m_delay-': controller.stylus_modes_settling_delay['measure'],
            '-m_max_deviation-': controller.stylus_modes_max_deviation['measure'],
            '-m_number_of_reading-': controller.stylus_modes_number_of_reading['measure'],
            '-t_delay-': controller.stylus_modes_settling_delay['typing'],
            '-t_max_deviation-': controller.stylus_modes_max_deviation['typing'],
            '-t_number_of_reading-': controller.stylus_modes_number_of_reading['typing']
            }

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-v",
        "--verbose",
        nargs=1,
        default="info",
        help=("Provide logging level: [debug, info, warning, error, critical]"),
    )
    #    parser.add_argument(
    #        "-log",
    #        "--logfile",
    #        nargs=1,
    #        default="./lod/dcs5.log",
    #        help=("Filename to print the logs to."),
    #    )
    args = parser.parse_args()

    log_name = 'dcs5_log_' + time.strftime("%y%m%dT%H%M%S", time.gmtime())

    log_path = PurePath(PurePath(__file__).parent, '../logs', log_name)

    logging.basicConfig(
        level=args.verbose.upper(),
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(log_path),
            logging.StreamHandler()
        ]
    )
    logging.info('Starting')
    c = Dcs5Controller()
    make_window(c)
    logging.info('Finished')


if __name__ == '__main__':
    main()