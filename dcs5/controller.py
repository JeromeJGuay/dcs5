"""
Author : JeromeJGuay
Date : May 2022

This module contains the class relative to the DCS5 XT and Micro Board Controller and Client (bluetooth).


References
----------
    https://bigfinllc.com/wp-content/uploads/Big-Fin-Scientific-Fish-Board-Integration-Guide-V2_0.pdf?fbclid=IwAR0tJMwvN7jkqxgEhRQABS0W3HLLntpOflg12bMEwM5YrDOwcHStznJJNQM

"""

import logging
import re
import threading
import time
from dataclasses import dataclass
from itertools import cycle
from queue import Queue
from typing import *

import pyautogui as pag

from dcs5.bluetooth_client import BluetoothClient
from dcs5.keyboard_emulator import KeyboardEmulator

from dcs5.controller_configurations import load_config, ControllerConfiguration, ConfigError
from dcs5.devices_specifications import load_devices_specification, DevicesSpecifications
from control_box_parameters import XtControlBoxParameters, MicroControlBoxParameters

BOARD_MESSAGE_DELIMITER = "\r"

pag.FAILSAFE = False

BOARD_STATE_MONITORING_SLEEP = 5

AFTER_SENT_SLEEP = 0.01

HANDLER_SLEEP = 0.01

LISTENER_SLEEP = 0.005


@dataclass
class InternalBoardState:
    sensor_mode: str = None
    stylus_status_msg: str = None
    stylus_settling_delay: int = None
    stylus_max_deviation: int = None
    number_of_reading: int = None

    firmware: str = None
    battery_level: str = None
    is_charging: bool = None
    temperature: int = None
    humidity: int = None
    board_stats: str = None
    board_interface: str = None
    calibrated: bool = None
    cal_pt_1: int = None
    cal_pt_2: int = None

    backlighting_level: int = None
    backlighting_auto_mode: bool = None
    backlighting_sensitivity: int = None


class Dcs5Controller:
    dynamic_stylus_settings: bool
    output_mode: str
    reading_profile: str
    length_units: str
    stylus: str
    stylus_offset: int
    stylus_cyclical_list: Generator

    def __init__(self, config_path: str, devices_specifications_path: str):
        """

        Parameters
        ----------
        config_path
        devices_specifications_path
        control_box_settings_path
        """
        self.config_path = config_path
        self.devices_specifications_path = devices_specifications_path
        self.config: ControllerConfiguration = None
        self.devices_specifications: DevicesSpecifications = None
        self.control_box_parameters: Union[XtControlBoxParameters, MicroControlBoxParameters] = None
        self._load_configs()

        self.listen_thread: threading.Thread = None
        self.command_thread: threading.Thread = None

        self.board_state_monitoring_thread: threading.Thread = None
        self.auto_reconnect_thread: threading.Thread = None
        self.auto_reconnect = False
        self.listener_handler_sync_barrier = threading.Barrier(2)
        self.listening_stopped_barrier = threading.Barrier(3)
        self.ping_event_check = threading.Event()

        self.client = BluetoothClient()
        self.shouter = KeyboardEmulator()
        self.internal_board_state = InternalBoardState()  # Board Current State

        self.socket_listener = SocketListener(self)
        self.command_handler = CommandHandler(self)

        self.is_sync = False  # True if the Dcs5Controller board settings are the same as the Board Internal Settings.
        self.is_listening = False  # listening to the keyboard on the connected socket.
        self.is_muted = False  # Message are processed but keyboard input are suppress.

        self.user_set_backlight_value: int = None # Used to save backlight value when MODE key is lit.

        self._set_board_settings()

        self.controller_commands = [
            "CHANGE_STYLUS",
            "UNITS_mm",
            "UNITS_cm",
            "CHANGE_OUTPUT_MODE",
            "MODE_TOP",
            "MODE_LENGTH",
            "MODE_BOTTOM",
            "MODE", "BACKLIGHT_UP", "BACKLIGHT_DOWN"
        ]

    def _load_configs(self):
        if (devices_spec := load_devices_specification(self.devices_specifications_path)) is None:
            raise ConfigError(f'Error in {self.devices_specifications_path}. File could not be loaded.')
        else:
            self.devices_specifications = devices_spec

        if (config := load_config(self.config_path)) is None:
            raise ConfigError(f'Error in {self.config_path}. File could not be loaded.')

        match self.devices_specifications.control_box.model:
            case "xt":
                self.control_box_parameters = XtControlBoxParameters()
            case "micro":
                self.control_box_parameters = MicroControlBoxParameters()

        if not 0 <= config.launch_settings.backlighting_level <= self.control_box_parameters.max_backlighting_level:
            raise ConfigError(
                f'launch_settings/Backlight_level outside range {(0, self.control_box_parameters.max_backlighting_level)}')

        for key, item in config.reading_profiles.items():
            if not self.control_box_parameters.min_settling_delay <= item.settling_delay <= self.control_box_parameters.max_settling_delay:
                raise ConfigError(
                    f'reading_profiles/{key}/settling_delay outside range {(self.control_box_parameters.min_settling_delay, self.control_box_parameters.max_settling_delay)}')
            if not self.control_box_parameters.min_max_deviation <= item.max_deviation <= self.control_box_parameters.max_max_deviation:
                raise ConfigError(
                    f'reading_profiles/{key}/max_deviation outside range {(self.control_box_parameters.min_max_deviation, self.control_box_parameters.max_max_deviation)}')

        self.config = config

    def reload_configs(self):
        self.is_sync = False
        self._load_configs()
        self._set_board_settings()

    def _set_board_settings(self):
        self.dynamic_stylus_settings = self.config.launch_settings.dynamic_stylus_mode
        self.output_mode = self.config.launch_settings.output_mode
        self.reading_profile = self.config.launch_settings.reading_profile
        self.length_units = self.config.launch_settings.length_units
        self.stylus: str = self.config.launch_settings.stylus
        self.stylus_offset = self.devices_specifications.stylus_offset[self.stylus]
        self.stylus_cyclical_list = cycle(list(self.devices_specifications.stylus_offset.keys()))

    def start_client(self, mac_address: str = None):
        """Create a socket and tries to connect with the board."""
        if self.client.is_connected:
            logging.debug("Client Already Connected.")
        else:
            self.is_sync = False  # If the board is Deconnected. Set sync flag to False.
            mac_address = mac_address or self.config.client.mac_address
            self.client.connect(mac_address, timeout=30)

            if self.client.is_connected:
                self.start_auto_reconnect_thread()

    def close_client(self):
        """"Should only be called from the thread main thread."""
        if self.client.is_connected:
            self.auto_reconnect = False
            self.stop_listening()
            self.client.close()
            logging.debug('Client Closed.')
        else:
            logging.debug('Client Already Closed')

    def restart_client(self):
        self.close_client()
        time.sleep(0.5)
        self.start_client()

    def start_auto_reconnect_thread(self):
        self.auto_reconnect = True
        self.auto_reconnect_thread = threading.Thread(target=self.monitor_connection,
                                                      name="auto reconnect", daemon=True)
        self.auto_reconnect_thread.start()
        logging.debug('Auto Reconnect Thread Started')

    def monitor_connection(self):
        while self.auto_reconnect is True:
            while self.client.is_connected:
                time.sleep(1) #FIXME Make into a global variables
            was_listening = self.is_listening
            self.stop_listening()

            if self.auto_reconnect is True:
                while not self.client.is_connected:
                    logging.debug('Attempting to reconnect.')
                    self.client.connect(self.config.client.mac_address, timeout=30)
                    time.sleep(.25)

            if was_listening:
                self.start_listening()
                self.init_controller_and_board()

    def start_listening(self):
        if self.client.is_connected:
            logging.debug(f"Active Threads: {threading.active_count()} {threading.enumerate()}")
            if not self.is_listening:
                logging.debug('Starting Threads.')

                self.is_listening = True
                self.command_thread = threading.Thread(target=self.command_handler.processes_queues, name='command handler',
                                                       daemon=True)
                self.command_thread.start()

                self.listen_thread = threading.Thread(target=self.socket_listener.listen, name='listener', daemon=True)
                self.listen_thread.start()

                if isinstance(self.board_state_monitoring_thread, threading.Thread):
                    if not self.board_state_monitoring_thread.is_alive():
                        self.start_board_state_monitoring_thread()
                else:
                    self.start_board_state_monitoring_thread()

                self.change_board_output_mode('length')

        else:
            logging.debug('Cannot start listening, board is not connected.')

    def stop_listening(self):
        if self.is_listening:
            self.is_listening = False
            barrier_value = self.listening_stopped_barrier.wait()
            logging.debug(f"Wait Called. Wait value: {barrier_value}.")

    def restart_listening(self):
        self.stop_listening()
        self.start_listening()

    def start_board_state_monitoring_thread(self):
        self.board_state_monitoring_thread = threading.Thread(target=self.monitor_board_state,
                                                              name='monitoring',
                                                              daemon=True)  # FIXME uncomment
        self.board_state_monitoring_thread.start()

    def monitor_board_state(self):
        while self.is_listening:
            self.c_get_battery_level()
            self.c_get_temperature_humidity()
            time.sleep(BOARD_STATE_MONITORING_SLEEP)

    def unmute_board(self):
        """Unmute board shout output"""
        if self.is_muted:
            self.is_muted = False
            logging.debug('Board unmuted')

    def mute_board(self):
        """Mute board shout output"""
        if not self.is_muted:
            self.is_muted = True
            logging.debug('Board muted')

    def init_controller_and_board(self):
        """Init measuring board.
        """
        logging.debug('Initializing Board.')

        self.internal_board_state = InternalBoardState()
        self.is_sync = False
        logging.debug('Internal Board State Values cleared. is_sync set to False')

        was_listening = self.is_listening
        self.restart_listening()

        self.c_set_backlighting_level(0)

        reading_profile = self.config.reading_profiles[
            self.config.output_modes.mode_reading_profiles[self.output_mode]
        ]

        # SET DEFAULT VALUES
        self.c_set_interface(0)

        self.c_set_stylus_detection_message(False)

        # SET USER VALUES
        self.c_set_stylus_settling_delay(reading_profile.settling_delay)
        self.c_set_stylus_max_deviation(reading_profile.max_deviation)
        self.c_set_stylus_number_of_reading(reading_profile.number_of_reading)

        self.c_set_backlighting_level(self.config.launch_settings.backlighting_level)

        self.c_check_calibration_state()
        self.c_get_board_stats()

        if self.wait_for_ping(timeout=5) is True:
            if (
                    self.internal_board_state.board_interface == "Dcs5LinkStream" and
                    self.internal_board_state.stylus_status_msg == "disable" and
                    self.internal_board_state.stylus_settling_delay == reading_profile.settling_delay and
                    self.internal_board_state.stylus_max_deviation == reading_profile.max_deviation and
                    self.internal_board_state.number_of_reading == reading_profile.number_of_reading
            ):
                self.is_sync = True
                logging.debug("Board initiation succeeded.")
            else:
                logging.debug("Board initiation failed.")
                state = [
                    self.internal_board_state.sensor_mode,
                    self.internal_board_state.stylus_status_msg,
                    (self.internal_board_state.stylus_settling_delay, reading_profile.settling_delay),
                    (self.internal_board_state.stylus_max_deviation, reading_profile.max_deviation),
                    (self.internal_board_state.number_of_reading, reading_profile.number_of_reading)]
                logging.debug(str(state))
        else:
            logging.debug("Ping was not received. Board initiation failed.")

        if not was_listening:
            self.stop_listening()

    def wait_for_ping(self, timeout=2):
        self.c_ping()
        self.ping_event_check.clear()
        logging.debug('Waiting for ping event.')
        if self.ping_event_check.wait(timeout):
            logging.debug('Ping received.')
            return True
        logging.debug('Ping not received.')
        return False

    def change_length_units_mm(self, flash=True):
        self.length_units = "mm"
        logging.debug(f"Length Units Change to mm")
        if self.is_listening and flash is True:
            self.c_flash_fuel_gauge()

    def change_length_units_cm(self, flash=True):
        self.length_units = "cm"
        logging.debug(f"Length Units Change to cm")
        if self.is_listening and flash is True:
            self.c_flash_fuel_gauge()

    def change_stylus(self, value: str, flash=True):
        """Stylus must be one of [pen, finger]"""
        self.stylus = value
        self.stylus_offset = self.devices_specifications.stylus_offset[self.stylus]
        logging.debug(f'Stylus set to {self.stylus}. Stylus offset {self.stylus_offset}')
        if self.is_listening and flash is True:
            self.c_flash_fuel_gauge()

    def mode_key_backlight_pattern(self, value: bool):
        if self.is_listening:
            if value is True:
                key = self.find_command_key('MODE')
                if key is not None:
                    key -= 1  # led keys are numbered 0-31 in the firmware
                    self.user_set_backlight_value = self.internal_board_state.backlighting_level
                    self.c_set_backlighting_level(round(self.control_box_parameters.max_backlighting_level / 3))
                    self.c_set_key_backlighting_level(level=self.control_box_parameters.max_backlighting_level, key=key)
            else:
                self.c_set_backlighting_level(self.user_set_backlight_value)

    def find_command_key(self, command: str):
        """Return the controller box internal key value."""
        _key = None
        for key in self.config.key_maps.control_box:
            for value in (self.config.key_maps.control_box[key], self.config.key_maps.control_box_mode[key]):
                if isinstance(value, str):
                    if command == value:
                        _key = key
                        break

                else:
                    if command in value:
                        _key = key
                        break
        if _key is not None:
            return int(dict(zip(self.devices_specifications.control_box.keys_layout.values(),
                            self.devices_specifications.control_box.keys_layout.keys()))[_key])
        return None

    def cycle_stylus(self):
        self.change_stylus(next(self.stylus_cyclical_list))

    def cycle_output_mode(self):
        self.change_board_output_mode({'top':'bottom', 'bottom':'length','length':'top'}[self.output_mode])

    def change_board_output_mode(self, value: str):
        """
        value must be one of  [length, bottom, top]
        """
        self.output_mode = value
        if self.client.is_connected:
            if self.is_listening:  # and flash is True:
                if self.devices_specifications.control_box.model == "xt":
                    if self.output_mode == 'bottom':
                        self.c_set_fuel_gauge(int("11110000", 2))
                    elif self.output_mode == 'top':
                        self.c_set_fuel_gauge(int("00001111", 2))
                    else:
                        self.c_set_fuel_gauge(int("00111100", 2))
                else:
                    color = [r,g,b,w] = int('FF', 16), int('60', 16), int('00', 16), int('00', 16) #  orange
                    if self.output_mode == 'bottom':
                        self.c_set_fuel_gauge(int("11000000", 2), color)
                    elif self.output_mode == 'top':
                        self.c_set_fuel_gauge(int("00001100", 2), color)
                    else:
                        self.c_set_fuel_gauge(int("00000011", 2), color)

            if self.dynamic_stylus_settings is True:
                reading_profile = self.config.reading_profiles[
                    self.config.output_modes.mode_reading_profiles[self.output_mode]
                ]
                self.c_set_stylus_settling_delay(reading_profile.settling_delay)
                self.c_set_stylus_max_deviation(reading_profile.max_deviation)
                self.c_set_stylus_number_of_reading(reading_profile.number_of_reading)
        logging.debug(f'Board entry: {self.output_mode}.')

    def _mode_top(self):
        self.change_board_output_mode('top')

    def _mode_length(self):
        self.change_board_output_mode('length')

    def _mode_bottom(self):
        self.change_board_output_mode('bottom')

    def to_keyboard(self, value: Union[int, float, str]):
        if not self.is_muted:
            logging.debug(f"Shouted value {value}")
            if isinstance(value, str):
                if value.startswith('print '):  # could be its own function
                    value = value[6:].strip(' ')
            self.shouter.shout(value)

    def backlight_up(self):
        if self.internal_board_state.backlighting_level < self.control_box_parameters.max_backlighting_level:
            self.internal_board_state.backlighting_level += 25
            if self.internal_board_state.backlighting_level > self.control_box_parameters.max_backlighting_level:
                self.internal_board_state.backlighting_level = self.control_box_parameters.max_backlighting_level
            self.c_set_backlighting_level(self.internal_board_state.backlighting_level)
        else:
            logging.debug("Backlighting is already at maximum.")

    def backlight_down(self):
        if self.internal_board_state.backlighting_level > 0:
            self.internal_board_state.backlighting_level += -25
            if self.internal_board_state.backlighting_level < 0:
                self.internal_board_state.backlighting_level = 0
            self.c_set_backlighting_level(self.internal_board_state.backlighting_level)
        else:
            logging.debug("Backlighting is already at minimum.")

    def mapped_controller_commands(self, command: str):
        commands = {
            "CHANGE_STYLUS": self.cycle_stylus,
            "UNITS_mm": self.change_length_units_mm,
            "UNITS_cm": self.change_length_units_cm,
            "CHANGE_OUTPUT_MODE": self.cycle_output_mode,
            "MODE_TOP": self._mode_top,
            "MODE_LENGTH": self._mode_length,
            "MODE_BOTTOM": self._mode_bottom,
            "BACKLIGHT_UP": self.backlight_up,
            "BACKLIGHT_DOWN": self.backlight_down,
        }
        commands[command]()

    def calibrate(self, pt: int) -> int:
        """

        Parameters
        ----------
        pt

        Returns
        -------
        1 for good calibration
        0 for failed calibration
        """

        logging.debug("Calibration Mode Enable.")

        was_listening = self.is_listening

        self.stop_listening()

        self.client.clear()
        self.client.send(f"&{pt}r#")
        self.client.set_timeout(5)
        msg = self.client.receive()
        logging.debug(f"Calibration message received: {msg}")
        try:
            if f"&{pt}r#\r" in msg:
                pt_value = self.internal_board_state.__dict__[f"cal_pt_{pt}"]
                logging.debug(f"Calibration for point {pt}. Set stylus down at {pt_value} mm ...")
                while f'&{pt}c' not in msg:
                    msg += self.client.receive()
                logging.debug(f'Point {pt} calibrated.')
                return 1
            else:
                return 0
        except KeyError:
            logging.debug('Calibration Failed.')
            return 0
        finally:
            self.client.socket.settimeout(self.client.default_timeout)
            if was_listening:
                self.start_listening()

    def c_ping(self):
        self.command_handler.queue_command("&a#", "%a#\r")

    def c_get_board_stats(self):
        self.command_handler.queue_command("b#", "regex_%b.*#\r")

    def c_get_battery_level(self):
        self.command_handler.queue_command('&q#', "regex_%q:\d+,\d+#\r")

    def c_get_temperature_humidity(self):
        self.command_handler.queue_command('&t#', "regex_%t,\d+,\d+#\r")

    def c_board_initialization(self):
        self.command_handler.queue_command("&init#", ["Setting EEPROM init flag.\r", "Rebooting in 2 seconds.\r"])
        time.sleep(1)
        self.close_client()

    def c_set_interface(self, value: int):
        """
        Notes
        -----
          Only the DCS5Linkstream Interface is now supported.
        """
        host_app = {0: 'DCSLinkstream', 1: "FEED"}[value]
        self.command_handler.queue_command(f"&pl,{value}#", [f'HostApp={host_app}\r', f"%pl,{value}#\r"])

    def c_flash_fuel_gauge(self):
        self.command_handler.queue_command("&ra#", "%ra#\r")

    def c_set_fuel_gauge(self, value: int, color: list = None):
        """
        Parameters
        ----------
        value :
            Int (byte) encoding the pattern e.g. int('00110000',2)
        color : for micro only.
            (r, g, b, w) Int representing hex value color value.
        """
        if self.devices_specifications.control_box.model == 'xt':
            self.command_handler.queue_command(f"&lf,{value}#", f"%lf,{value}#\r")
        else:
            color = list(map(str, color))
            self.command_handler.queue_command(
                f"&lf,{value},{','.join(color)}#", f"%lf,{value},{','.join(color)}#\r"
            )

    def c_set_fuel_gauge_tempory(self, delay: int, value: int, color: list = None):
        """
        Parameters
        ----------
        delay :
           Duration of the led pattern in second. (0-255)
        value :
            Int (byte) encoding the pattern e.g. int('00110000',2)
        color : for micro only.
            (r, g, b, w) Int representing hex value color value.
        """
        if self.devices_specifications.control_box.model == 'xt':
            self.command_handler.queue_command(f"&lt,{delay},{value}#", f"%lt,{delay},{value}#\r")
        else:
            color = list(map(str, color))
            self.command_handler.queue_command(
                f"&lt,{delay},{value},{','.join(color)}#", f"%lt,{delay},{value},{','.join(color)}#\r"
            )

    def c_set_backlighting_level(self, level: int):
        if level is None:
            level = self.control_box_parameters.max_backlighting_level
        if 0 <= level <= self.control_box_parameters.max_backlighting_level:
            # if self.devices_specifications.control_box.model == "micro":
            #     level = int(level * (255/95))
            self.command_handler.queue_command(f'&la,{level}#', f"%la,{level}#\r")
        else:
            logging.warning(f"Backlighting level range: (0, {self.control_box_parameters.max_backlighting_level})")

    def c_set_key_backlighting_level(self, level: int, key: int):
        if level is None:
            level = self.control_box_parameters.max_backlighting_level
        if 0 <= level <= self.control_box_parameters.max_backlighting_level:
            self.command_handler.queue_command(f'&lk,{level},{key}#', f"%lk,{level},{key}#\r")
        else:
            logging.warning(f"Backlighting level range: (0, {self.control_box_parameters.max_backlighting_level})")

    def c_set_backlighting_auto_mode(self, value: bool):  # NOT IMPLEMENTED IN THE CURRENT FIRMWARE FIXME
        logging.warning('Command not implemented in the current firmware')
        # self.command_handler.queue_command(f"&oa,{int(value)}", None)
        # self.internal_board_state.backlighting_auto_mode = {True: 'auto', False: 'manual'}

    def c_set_backlighting_sensitivity(self, value: int):  # NOT IMPLEMENTED IN THE CURRENT FIRMWARE FIXME
        logging.warning('Command not implemented in the current firmware')
        # if 0 <= value <= self.control_box_parameters.max_backlighting_sensitivity:
        #     self.command_handler.queue_command(f"&os,{value}", None)
        #     self.internal_board_state.backlighting_sensitivity = value
        # else:
        #     logging.warning(
        #         f"Backlighting sensitivity range: (0, {self.control_box_parameters.max_backlighting_sensitivity})")

    def c_set_stylus_detection_message(self, value: bool):
        """
        When disabled (false): %t0 %t1 are not sent
        """
        self.command_handler.queue_command(f'&sn,{int(value)}#', f'%sn:{int(value)}#\r')

    def c_set_stylus_settling_delay(self, value: int = 1):
        if self.control_box_parameters.min_settling_delay <= value <= self.control_box_parameters.max_settling_delay:
            self.command_handler.queue_command(f"&di,{value}#", f"%di:{value}#\r")
        else:
            logging.warning(
                f"Settling delay value range: ({self.control_box_parameters.min_settling_delay}, {self.control_box_parameters.max_settling_delay})")

    def c_set_stylus_max_deviation(self, value: int):
        if self.control_box_parameters.min_max_deviation <= value <= self.control_box_parameters.max_max_deviation:
            self.command_handler.queue_command(f"&dm,{value}#", f"%dm:{value}#\r")
        else:
            logging.warning(
                f"Settling delay value range: ({self.control_box_parameters.min_max_deviation}, {self.control_box_parameters.max_max_deviation})")

    def c_set_stylus_number_of_reading(self, value: int = 5):
        self.command_handler.queue_command(f"&dn,{value}#", f"%dn:{value}#\r")

    def c_restore_cal_data(self):
        self.command_handler.queue_command("&cr,m1,m2,raw1,raw2#", None)

    def c_clear_cal_data(self):
        self.command_handler.queue_command("&ca#", None)
        self.internal_board_state.calibrated = False

    def c_check_calibration_state(self):
        self.command_handler.queue_command('&u#', 'regex_%u:\d#\r')

    def c_set_calibration_points_mm(self, pt: int, pos: int):
        self.command_handler.queue_command(f'&{pt}mm,{pos}#', f'%{pt}mm,{pos}#\r')


class CommandHandler:
    def __init__(self, controller: Dcs5Controller):
        self.controller = controller

        self.send_queue = Queue()
        self.received_queue = Queue()
        self.expected_message_queue = Queue()

    def queue_command(self, command: str, message: Union[str, List[str]] = None):
        if message is not None:
            if isinstance(message, list):
                [self.expected_message_queue.put(msg) for msg in message]
            else:
                self.expected_message_queue.put(message)
        self.send_queue.put(command)
        logging.debug(f'Queuing: Command -> {[command]}, Expected -> {[message]}')

    def clear_queues(self):
        self.send_queue.queue.clear()
        self.received_queue.queue.clear()
        self.expected_message_queue.queue.clear()
        logging.debug("Handler Queues Cleared.")

    def processes_queues(self):
        self.clear_queues()
        self.controller.listener_handler_sync_barrier.wait()
        logging.debug('Command Handling Started')
        while self.controller.is_listening:

            if not self.received_queue.empty():
                self._process_commands()

            if not self.send_queue.empty():
                self._send_command()
                time.sleep(AFTER_SENT_SLEEP)

            time.sleep(HANDLER_SLEEP)
        barrier_value = self.controller.listening_stopped_barrier.wait()
        logging.debug(f"Wait Called. Wait value: {barrier_value}.")
        logging.debug('Command Handling Stopped')

    def _process_commands(self):
        received = self.received_queue.get()

        self._compared_with_expected(received)

        if "%a#" in received:
            self.controller.ping_event_check.set()
            logging.debug('Ping is set.')

        elif "%pl" in received:
            match = re.findall(f"%pl,(\d)#\r", received)
            if len(match) > 0:
                if match[0] == "0":
                    self.controller.internal_board_state.board_interface = "Dcs5LinkStream"
                    logging.debug(f'Interface set to DcsLinkStream')
                elif match[0] == "1":
                    self.controller.internal_board_state.board_interface = "FEED"
                    logging.debug(f'Interface set to FEED')

        elif "%sn" in received:
            match = re.findall(f"%sn:(\d)#\r", received)
            if len(match) > 0:
                if match[0] == "1":
                    self.controller.internal_board_state.stylus_status_msg = "enable"
                    logging.debug('Stylus Status Message Enable')
                else:
                    self.controller.internal_board_state.stylus_status_msg = "disable"
                    logging.debug('Stylus Status Message Disable')

        elif "%di" in received:
            match = re.findall(f"%di:(\d+)#\r", received)
            if len(match) > 0:
                self.controller.internal_board_state.stylus_settling_delay = int(match[0])
                logging.debug(f"Stylus settling delay set to {match[0]}")

        elif "%dm" in received:
            match = re.findall(f"%dm:(\d+)#\r", received)
            if len(match) > 0:
                self.controller.internal_board_state.stylus_max_deviation = int(match[0])
                logging.debug(f"Stylus max deviation set to {int(match[0])}")

        elif "%dn" in received:
            match = re.findall(f"%dn:(\d+)#\r", received)
            if len(match) > 0:
                self.controller.internal_board_state.number_of_reading = int(match[0])
                logging.debug(f"Stylus number set to {int(match[0])}")

        elif "%b" in received:
            match = re.findall("%b:(.*)#", received)
            if len(match) > 0:
                logging.debug(f'Board State: {match[0]}')
                self.controller.internal_board_state.board_stats = match[0]
                firmware_version = match[0].split(',')[1]
                self.controller.internal_board_state.firmware = firmware_version[:-2] + '.' + firmware_version[-2:]

        elif "%q" in received:
            match = re.findall("%q:(\d+),(\d+)#", received)
            if len(match) > 0:
                logging.debug(f'Battery level: {match[0][0]}')
                self.controller.internal_board_state.battery_level = int(match[0][0])
                self.controller.internal_board_state.is_charging = bool(int(match[0][1]))

        elif "%t" in received:
            match = re.findall("%t,(\d+),(\d+)#", received)
            if len(match) > 0:
                logging.debug(f'temperature: {match[0][0]}, humidity: {match[0][1]}')
                self.controller.internal_board_state.temperature = int(match[0][0])
                self.controller.internal_board_state.humidity = int(match[0][1])

        elif "%u:" in received:
            match = re.findall("%u:(\d)#", received)
            if len(match) > 0:
                if match[0] == '0':
                    logging.debug('Board is not calibrated.')
                    self.controller.internal_board_state.calibrated = False
                elif match[0] == '1':
                    logging.debug('Board is calibrated.')
                    self.controller.internal_board_state.calibrated = True
            else:
                logging.error(f'Calibration state {received}')

        elif "%la" in received:
            match = re.findall("%la,(\d+)#", received)
            if len(match) > 0:
                level = int(match[0])
                # if self.controller.devices_specifications.control_box.model == "micro":
                #     level = int(level * (95 / 255))
                self.controller.internal_board_state.backlighting_level = level
                logging.debug(f'Backlight level set to {level}')

        elif 'Cal Pt' in received:  # FOR MICRO #FIXME MAKE IT THE SAME IN THE FIRMWARE
            logging.debug(received.strip("\r") + " mm")
            match = re.findall("Cal Pt (\d+) set to: (\d+)", received)  # used to work on firmware v1.07 (I think) of XT.
            if len(match) > 0:
                self.controller.internal_board_state.__dict__[f'cal_pt_{match[0][0]}'] = int(match[0][1])

        elif 'mm' in received:
            logging.debug(received.strip("\r") + " mm")
            match = re.findall(f'%(\d+)mm,(\d+)#\r', received)
            if len(match) > 0:
                self.controller.internal_board_state.__dict__[f'cal_pt_{match[0][0]}'] = int(match[0][1])

    def _compared_with_expected(self, received: str):
        command_is_valid = False
        expected = self.expected_message_queue.get()
        logging.debug(f'Received: {[received]}, Expected: {[expected]}')

        if "regex_" in expected:
            match = re.findall("(" + expected.strip('regex_') + ")", received)
            if len(match) > 0:
                command_is_valid = True
        elif received == expected:
            command_is_valid = True

        if command_is_valid:
            logging.debug('Command Valid')
        else:
            logging.error(f'Unexpected: Command received: {[received]}, Command expected: {[expected]}')

    def _send_command(self):
        command = self.send_queue.get()
        self.controller.client.send(command)
        logging.debug(f'Command Sent: {[command]}')


class SocketListener:
    """The socket listener also do the command interpretation."""
    def __init__(self, controller: Dcs5Controller):
        self.controller = controller
        self.message_queue = Queue()
        self.buffer = ""
        self.swipe_triggered = False
        self.with_mode = False
        self.last_key = None
        self.last_command = None

    def reset(self):
        self.swipe_triggered = False
        self.with_mode = False
        self.last_key = None
        self.last_command = None

        self.controller.client.clear()
        self.clear_buffer()
        self.message_queue.queue.clear()

    def clear_buffer(self):
        self.buffer = ""

    def listen(self):
        self.reset()
        logging.debug("Listener Queue and Client Buffers Cleared.")
        self.controller.listener_handler_sync_barrier.wait()

        logging.debug('Listening started')
        while self.controller.is_listening:
            self.buffer += self.controller.client.receive()
            if len(self.buffer) > 0:
                logging.debug(f'Raw Buffer: {[self.buffer]}')
                self._split_board_message()
                self._process_board_message()
            time.sleep(LISTENER_SLEEP)

        barrier_value = self.controller.listening_stopped_barrier.wait()
        logging.debug(f"Wait Called. Wait value: {barrier_value}.")
        logging.debug('Listening stopped')

    def _split_board_message(self):
        msg = self.buffer.split(BOARD_MESSAGE_DELIMITER, 1)
        if len(msg) > 1:
            self.message_queue.put(msg[0] + BOARD_MESSAGE_DELIMITER)
            self.buffer = msg[1]

    def _process_board_message(self):
        """ANALYZE SOLICITED VS UNSOLICITED MESSAGE"""
        while not self.message_queue.empty():
            message = self.message_queue.get()
            logging.debug(f'Received Message: {message}')
            output_value = None
            msg_type, msg_value = self._decode_board_message(message)
            logging.debug(f"Message Type: {msg_type}, Message Value: {msg_value}")

            if msg_type == "controller_box_key":
                output_value = self._map_control_box_output(msg_value)
                logging.debug(f"Controller Box Output: {output_value}")

            elif msg_type == 'swipe':
                self.swipe_value = msg_value
                if msg_value > self.controller.config.output_modes.swipe_threshold:
                    self.swipe_triggered = True

            elif msg_type == 'length':
                if self.swipe_triggered is True:
                    self._check_for_stylus_swipe(msg_value)
                else:
                    output_value = self._map_board_length_measurement(msg_value)
            elif msg_type == "solicited":
                self.controller.command_handler.received_queue.put(msg_value)

            if output_value is not None:
                self.last_command = output_value
                self._process_output(output_value)

    @staticmethod
    def _decode_board_message(value: str):
        """
        """
        patterns = [
            "%t,([0-9])#",  # stylus up/down
            "%l,([0-9]*)#",  # length measurement
            "%s,(-?\d+)#",  # swipe
            "%hs,([0-9])#",  # Micro button
            "%k,([0-9]{2})#",  # Xt button v2.0.0+
            #",Battery charge-voltage-current-ttfull-ttempty:,(\d+),(\d+),(\d+),(\d+),(\d+)" #FIXME REMOVE COMPLETLY IF THE BUG DOESNT COME UP AGAIN

        ]
        match = re.findall("|".join(patterns), value)
        if len(match) > 0:
            if match[0][1] != "":
                return 'length', int(match[0][1])
            elif match[0][2] != "":
                return 'swipe', int(match[0][2])
            elif match[0][3] != "":
                return 'controller_box_key', match[0][3]
            elif match[0][4] != "":
                return 'controller_box_key', match[0][4]
            #elif match[0][5] != "":  # temporary fix FIXME REMOVE COMPLETLY IF THE BUG DOESNT COME UP AGAIN
            #    logging.debug(f"micro unsolicited battery state {value}") #FIXME REMOVE
            #    return None, None
        else:
            return 'solicited', value

    def _process_output(self, value):
        if isinstance(value, list):
            for _value in value:
                self._process_output(_value)
        else:
            if value == "MODE":
                self.set_with_mode(not self.with_mode)
            else:
                self.set_with_mode(False)
                if value in self.controller.controller_commands:
                    self.controller.mapped_controller_commands(value)
                else:
                    self.controller.to_keyboard(value)

    def set_with_mode(self, value: bool):
        if value is not self.with_mode:
            self.with_mode = not self.with_mode
            self.controller.mode_key_backlight_pattern(self.with_mode)
        else:
            pass

    def _map_control_box_output(self, value):
        key = self.controller.devices_specifications.control_box.keys_layout[value]
        self.last_key = key
        if self.with_mode:
            return self.controller.config.key_maps.control_box_mode[key]
        else:
            return self.controller.config.key_maps.control_box[key]

    def _map_board_length_measurement(self, value: int):
        if self.controller.output_mode == 'length':
            out_value = value - self.controller.stylus_offset
            self.last_key = out_value
            if self.controller.length_units == 'cm':
                out_value /= 10
            return out_value
        else:
            index = int(
                (value - self.controller.devices_specifications.board.relative_zero)
                / self.controller.devices_specifications.board.key_to_mm_ratio
            )
            if index < self.controller.devices_specifications.board.number_of_keys:
                key = self.controller.devices_specifications.board.keys_layout[self.controller.output_mode][index]
                self.last_key = key
                if self.with_mode:
                    return self.controller.config.key_maps.board_mode[key]
                else:
                    return self.controller.config.key_maps.board[key]

    def _check_for_stylus_swipe(self, value: str):
        self.swipe_triggered = False
        self.last_input = "swipe"
        segments_limits = self.controller.config.output_modes.segments_limits
        if value <= segments_limits[-1]:
            for l_max, l_min, mode in zip(segments_limits[1:],
                                          segments_limits[:-1],
                                          self.controller.config.output_modes.segments_mode):
                if l_max >= int(value) > l_min:
                    self.controller.change_board_output_mode(mode)
                    break
