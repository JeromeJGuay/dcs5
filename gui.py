import PySimpleGUI as sg
from dcs5.controller import Dcs5Interface

def gui(self):
    width_col1 = 20
    width_col2 = 10
    sg.theme('Topanga')  # lightgreen darkamber
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

    layout = [
        [sg.Frame(title='Connection', layout=client_row)],
        [sg.Frame(title='Measuring Settings', layout=row_m, font=('Helvetica', 12))],
        [sg.Frame(title='Typing Settings', layout=row_t, font=('Helvetica', 12))],
        [sg.Push(), sg.Button('Update Firmware')],
        [sg.Frame(title='Modes', layout=row_modes, font=('Helvetica', 12))],
        [sg.Button("start listening", button_color='darkgreen'), sg.Button("stop listening", button_color='darkred')],
    ]

    window = sg.Window("DCS5-XT Board Interface", layout, finalize=True, location=(400, 100))
    while True:
        event, values = window.read(timeout=500)
        # End program if user closes window or
        # presses the OK button
        if event == "start listening":
            self.start_listening()
        if event == 'stop listening':
            self.stop_listening()

        if event == 'Connect':
            self.client.connect(address=DCS5_ADDRESS, port=PORT)
            window['-mac_address-'].update(self.client.dcs5_address)
            window['-port-'].update(self.client.port)
            if self.client.isconnected is True:
                window['INDICATOR'].update(value=connection_status[1][0], text_color=connection_status[1][1])
        if event == 'Disconnect':
            self.close_client()
            if self.client.isconnected is True:
                window['INDICATOR'].update(value=connection_status[0][0], text_color=connection_status[0][1])

        if event == '-update_row_m-':
            if values['-m_delay_input-'].isnumeric():
                delay = int(values['-m_delay_input-'])
                if 0 <= delay <= MAX_SETTLING_DELAY:
                    self.stylus_modes_settling_delay['measure'] = values['-m_delay_input-']
            if values['-m_max_deviation_input-'].isnumeric():
                deviation = int(values['-m_max_deviation_input-'])
                if 0 <= deviation <= MAX_MAX_DEVIATION:
                    self.stylus_modes_max_deviation['measure'] = values['-m_max_deviation_input-']
            if values['-m_number_of_reading_input-'].isnumeric():
                self.stylus_modes_number_of_reading['measure'] = values['-m_number_of_reading_input-']
            if self.stylus_entry_mode == 'measure':
                self.change_stylus_entry_mode('measure')
            window['-m_delay_input-'].update('')
            window['-m_max_deviation_input-'].update('')
            window['-m_number_of_reading_input-'].update('')

        if event == '-update_row_t-':
            if values['-t_delay_input-'].isnumeric():
                delay = int(values['-t_delay_input-'])
                if 0 <= delay <= MAX_SETTLING_DELAY:
                    self.stylus_modes_settling_delay['typing'] = values['-t_delay_input-']
            if values['-t_max_deviation_input-'].isnumeric():
                deviation = int(values['-t_max_deviation_input-'])
                if 0 <= deviation <= MAX_MAX_DEVIATION:
                    self.stylus_modes_max_deviation['typing'] = values['-t_max_deviation_input-']
            if values['-t_number_of_reading_input-'].isnumeric():
                self.stylus_modes_number_of_reading['typing'] = values['-t_number_of_reading_input-']
            if self.stylus_entry_mode == 'typing':
                self.change_stylus_entry_mode('typing')
            window['-t_delay_input-'].update('')
            window['-t_max_deviation_input-'].update('')
            window['-t_number_of_reading_input-'].update('')

        if event == 'Update Firmware':
            update_file = sg.popup_get_file('Select firmware update file')
        if event == sg.WIN_CLOSED:
            break

        controller_values = self.get_controller_values()
        for key, cvalue in controller_values.items():
            if window[key].get() != cvalue:
                window[key].update(cvalue)

    window.close()


def get_controller_values(self):
    return {'-m_delay-': self.stylus_modes_settling_delay['measure'],
            '-m_max_deviation-': self.stylus_modes_max_deviation['measure'],
            '-m_number_of_reading-': self.stylus_modes_number_of_reading['measure'],
            '-t_delay-': self.stylus_modes_settling_delay['typing'],
            '-t_max_deviation-': self.stylus_modes_max_deviation['typing'],
            '-t_number_of_reading-': self.stylus_modes_number_of_reading['typing']
            }