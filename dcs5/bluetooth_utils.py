"""
Author : JeromeJGuay
Date : May 2022
This Module Contains functions to Scan Bluetooth devices and Find a specific bluetooth device.
"""
from typing import *
import logging
import bluetooth


def scan_bluetooth_device():
    devices = {}
    logging.info("Scanning for bluetooth devices ...")
    _devices = bluetooth.discover_devices(lookup_names=True, lookup_class=True)
    number_of_devices = len(_devices)
    logging.info(f"{number_of_devices} devices found")
    for addr, name, device_class in _devices:
        devices[name] = {'address': addr, 'class': device_class}
        logging.info(f"Devices Name: {name}")
        logging.info(f"Devices MAC Address: {addr}")
        logging.info(f"Devices Class: {device_class}\n")
    return devices


def search_for_dcs5board(device_name: str) -> Optional[str]:
    devices = scan_bluetooth_device()
    if device_name in devices:
        logging.info(f'{device_name}, found.')
        return devices[device_name]['address']
    else:
        logging.info(f'{device_name}, not found.')
        return None
