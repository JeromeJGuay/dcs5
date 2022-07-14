# Dcs5 Controller app

This python application provides a command line interface and a server to interact with a BigFin Dcs5 XT measuring board via Bluetooth.
At the moment, the app only works on Unix machines due to some unresolved problems with the Bluetooth packages.
The application will turn stylus input on the measuring board into keyboard inputs basically turning the measuring board into a wireless keyboard.

## Installation
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


## Usage

To call the application ...
```shell
~$ dcs5 {cli_app, server}
```

## cli app
See the `user_guide/UserGuide_fr.odf`. French only.


## Calibration
With the cli app, use the `calpt1` and `calpt2` command to set calibration points. Then use the calibrate function and follow the instruction from the cli.
Although the board sends measurements value in mm, a specific offset needs to be added to at least one of the 2 stylus.
We suggest do the calibration with the finger stylus since the magnet of the pen is further away from its tips.
Calibrating with the pen would result in negative measurements when placing the finger stylus at 0 mm.
However, the measuring board cannot return values smaller than 0.
The offsets value are in `dcs5/devices_specifications/dcs5_default_devices_specification.json` files.

## Configurations

3 json files are used to set different parameters for the application.
### `configs/controller_configuration.json`
The controller_configuration.json is used to configure the controller behavior.
+ client : Measuring board bluetooth information.
+ launch_settings : setting used when the app is launch.
  - dynamic_stylus_mode: TODO
  - backlight_level: TODO
  - backlighting_auto_mode: TODO
  - backlighting_sensitivity: TODO
  - Notes: The reading profiles are defined in the next section.
+ reading_profiles :
  - settling_delay: TODO
  - number_of_reading: TODO
  - max_deviation: TODO
+ output_modes :
  - swipe_threshold: TODO
  - segments_limits: Define the limit of the different swipe segment.
  - segments_mode: The corresponding output_mode for each swipe segment.
  - mode_reading_profiles: The corresponding reading_profiles for each output modes.
+ keys_maps: Mapping of the key to either command or keyboard input.
  - Notes: The name of the keys are set in `config/devices_sepcification.json`.
  - Notes: Valid commands `["BACKLIGHT_UP", "BACKLIGHT_DOWN", "CHANGE_STYLUS", "UNITS_mm", "UNITS_cm"]`
  - Notes: See the `controller_configurations.py` module for the valid keyboard input.
  - Notes: List of command are accepted.

### `config/devices_sepcification.json`
+ board:
  - number_of_keys: The keys correspond to the grey circle on the board.
  - key_to_mm_ratio: The distance in mm from one edge of a circle (larger one) to the next.
  - zero: The distance (mm) that would be the key 0 given that the first key on the board is key 1.
  - detection_range: Offset on the left in mm for stylus detection. 
  - keys_layout: Ordered lists for the name of the top keys and the for the bottom keys. These names are used to map command.
    - Notes: The two list (top and bottom) should not contain identical names.  
+ control_box:
  - keys_layout: Mapping of the controller box key builtin id to meaningful name. These names are used to map command. 
+ stylus_offset: Offset in mm that is added ot the value measured by the board. 
  - Notes: These values will depend on the calibration.

### `configs/control_box_parameters.json`
Values of the builtin parameters of the control box. From Bigfin documentation.

## server

The application can be launch with a server to communicate with the board. This feature is working but still in development.
The server port and address are set ins the `config/server_configuration.json` file.






