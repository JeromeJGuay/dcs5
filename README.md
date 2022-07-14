Dcs5 Controller app
===================

This python application provides a command line interface and a server to interact with a BigFin Dcs5 XT measuring board via Bluetooth.
At the moment, the app only works on Unix machines due to some unresolved problems with the Bluetooth packages.
The application will turn stylus input on the measuring board into keyboard inputs basically turning the measuring board into a wireless keyboard.

Installation
------------
1) Install the linux package: python3.8-venv.
2) Install the python package pipx.
```shell
~$ pip install pipx
```
3) Install the application with pipx.
```shell
~$ pipx install "path/to/dcs5_folder/"
~$ pipx runpip dcs5 install -r "path/to/dcs5_folder/requirements.txt"
```


Calibration
-----------
Although the board sends measurements value in mm, a specific offset needs to be added for each stylus.
The offsets value are in `dcs5/devices_specifications/dcs5_default_devices_specification.json` files.



Usage
=====
To call the application ...
```shell
~$ dcs5 {cli_app, server}
```

cli app
-------
...

server
------
The application can be launch with a server to communicate with the board. This feature is working but still in development.

Configurations
--------------
3 json files are used to set different parameters for the application.
+ `configs/controller_configuration.json`
+ `config/devices_sepcification.json`
+ `configs/control_box_parameters.json`

The specific mapping for the controller keys are set in the `configs/controller_configuration.json` file.



