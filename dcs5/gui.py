"""

- VerticalSeparator(pad=None)

- Use Popup for printing error. (bt device not found etc)

"""
import logging
import PySimpleGUI as sg
from dcs5.logger import init_logging

sg.theme('lightgrey')

ENABLED_BUTTON_COLOR = "light blue"
DISABLED_BUTTON_COLOR = "light grey"

def main():
    init_logging(stdout_level='error', write=False)
    logging.info('Starting Gui ...')

    run()

    exit(0)


def make_window():
    header_layout = [sg.Image('../windows/bigfin_logo.png'),
                     sg.Text('Dcs5 Controller App', font='Courier 20', justification='c')]

    device_layout = [[sg.Text('A')]]
    # [[sg.Frame('Choose your Bread', [[sg.Radio('Whole Wheat', 'rd_bread', key='Whole Wheat'),
    #                                sg.Radio('Multigrain', 'rd_bread', key='Multigrain'),
    #                                sg.Radio('Normal', 'rd_bread', key='Normal'),
    #                                sg.Radio('Stuffed', 'rd_bread', key='Stuffed'),
    #                                sg.Radio('Healthy seeds', 'rd_bread', key='Healthy seeds')]], border_width=10)]]

    device_layout = [[
        sg.Frame(
            'Device', [
                [dotted("Name", "NAME TODO", 30)],
                [dotted("MAC address", "MAC TODO", 30)],
                [dotted("Port (Bt Channel)", 'PORT TODO', 30)]
            ],
            font='Courier 12'
        )
    ]]

    connection_layout = [[sg.Frame('Status',
                                   [[
                                       sg.Text('Connected'), led('red', key='-C_LED-', size=30),
                                       sg.Text('Activated'), led('red', key='-A_LED-', size=30),
                                   ],
                                    [
                                        sg.Button('Connect', size=(10, 1), font='Courier 10', button_color=ENABLED_BUTTON_COLOR,
                                        disabled_button_color=DISABLED_BUTTON_COLOR, key='-CONNECT-', use_ttk_buttons=True),
                                        sg.Button('Activate', size=(10, 1), font='Courier 10', button_color=ENABLED_BUTTON_COLOR,
                                        disabled_button_color=DISABLED_BUTTON_COLOR, key='-ACTIVATE-', use_ttk_buttons=True),
                                        sg.Button('Restart', size=(10, 1), font='Courier 10', button_color=ENABLED_BUTTON_COLOR,
                                        disabled_button_color=DISABLED_BUTTON_COLOR, key='-RESTART-', use_ttk_buttons=True)
                                    ]
                                   ], font='Courier 12'
                                    )]]

    logging_layout = [[sg.Text("Logging")],
                      [sg.Multiline(size=(60, 15), font='Courier 8', expand_x=True, expand_y=True, write_only=True,
                                    reroute_stdout=True, reroute_stderr=True, echo_stdout_stderr=True, autoscroll=True,
                                    auto_refresh=True)]
                      ]

    controller_layout = [[sg.Col(device_layout, p=0), sg.Col(connection_layout, p=0)]]

    global_layout = [[sg.Menu([['File', ['Exit']], ], k='-MENUBAR-', p=0)],
                     header_layout,
                     ]

    global_layout += [[sg.TabGroup([[sg.Tab('Controller', controller_layout),
                                     sg.Tab('Logging', logging_layout)]],
                                   key='-TAB GROUP-', expand_x=True, expand_y=True, font='Courier 10')]]
    global_layout[-1].append(sg.Sizegrip())

    window = sg.Window('Dcs5 Controller', global_layout, finalize=True, keep_on_top=False, resizable=True)

    return window


def run():
    window = make_window()

    while True:
        event, values = window.read(timeout=1)
        match event:
            case sg.WIN_CLOSED | 'Exit':
                break
            case "-CONNECT-":
                window["-CONNECT-"].update(disabled=True)
                window["-C_LED-"].update(text_color='Green')
            case "-ACTIVATE-":
                window["-ACTIVATE-"].update(disabled=True)
            case "-RESTART-":
                window["-RESTART-"].update(disabled=True)
            case _:
                continue

    window.close()


def dotted(key, value, length=50):
    dots = length - len(key) - len(value) - 2
    return sg.Text(key + ' ' + '•' * dots + ' ' + value, size=(length, 1), justification='r', pad=(0, 0),
                   font='Courier 10')


def led(color, filled=True, key=None, size=10):
    if filled:
        circle = '⚫'
    else:
        circle = '⚪'
    return sg.Text(circle, text_color=color, key=key, font=str(size))


if __name__ == "__main__":
    main()
