"""
Author : JeromeJGuay
Date : May 2022
This Module Contains functions to Scan Bluetooth devices and Find a specific bluetooth device.

June 22, 2022. Currently not used
"""

import click
from typing import *
#
# import bluetooth

#
# def scan_bluetooth_device():
#     devices = {}
#     click.secho("Scanning for bluetooth devices ...")
#     _devices = bluetooth.discover_devices(lookup_names=True, lookup_class=True)
#     number_of_devices = len(_devices)
#     click.secho(f"{number_of_devices} devices found")
#     for addr, name, device_class in _devices:
#         devices[name] = {'address': addr, 'class': device_class}
#         click.secho(f"Devices Name: {name}")
#         click.secho(f"Devices MAC Address: {addr}")
#         click.secho(f"Devices Class: {device_class}\n")
#     return devices
#
#
# def search_for_device(device_name: str) -> Optional[str]:
#     devices = scan_bluetooth_device()
#     if device_name in devices:
#         click.secho(f'{device_name}, found.')
#         return devices[device_name]['address']
#     else:
#         click.secho(f'{device_name}, not found.')
#         return None
#
