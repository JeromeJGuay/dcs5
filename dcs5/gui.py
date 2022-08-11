"""





VerticalSeparator(pad=None)

"""
import logging
import PySimpleGUI as sg
from dcs5.logger import init_logging



def main():
    init_logging(stdout_level='error', write=False)
    logging.info('Starting Gui...')





def frame_example(window: sg.Window):
    frame_layout = [
        [sg.T('Text inside of a frame')],
        [sg.CB('Check 1'), sg.CB('Check 2')],
    ]
    layout = [
        [sg.Frame('My Frame Title', frame_layout, font='Any 12', title_color='blue')],
        [sg.Submit(), sg.Cancel()]
    ]

    window = sg.Window('Frame with buttons', layout, font=("Helvetica", 12))
