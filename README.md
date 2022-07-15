# Dcs5 Controller app

This python (python 3.8) application provides a command line interface and a server to interact with a BigFin Dcs5 XT measuring board via Bluetooth.
At the moment, the app only works on Unix machines due to some unresolved problems with the Bluetooth packages.
The application will turn stylus input on the measuring board into keyboard inputs basically turning the measuring board into a wireless keyboard.

## Requirement

1) Linux (It may work on macOS but it has not been tested)
2) python 3.8
3) A BigFin Dcs5 Board with XT Control Box (duh)

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
See the [user_guide/UserGuide_fr.pdf](user_guide/UserGuide_fr.pdf). French only.


## Calibration
With the cli app, use the `calpt1` and `calpt2` command to set calibration points. Then use the calibrate function and follow the instruction from the cli.
Although the board sends measurements value in mm, a specific offset needs to be added to at least one of the 2 stylus.
We suggest do the calibration with the finger stylus since the magnet of the pen is further away from its tips.
Calibrating with the pen would result in negative measurements when placing the finger stylus at 0 mm.
However, the measuring board cannot return values smaller than 0.
The offsets value are in [dcs5/configs/devices_specification.json](dcs5/configs/devices_specification.json) files.

## Configurations

3 json files are used to set different parameters for the application.
### [dcs5/configs/controller_configuration.json](dcs5/configs/controller_configuration.json)
The controller_configuration.json is used to configure the controller behavior.
+ client : Measuring board bluetooth information.
+ launch_settings : setting used when the app is launch.
  - dynamic_stylus_mode: (true/false) If true, reading profiles will change for each output mode as defined in the next section.
  - backlight_level: (0-95) Backlight intensity 
  - backlighting_auto_mode: (true/false) Automatic backlighting adjustment.
  - backlighting_sensitivity: (0-7) Auto mode sensitivity.
  - Notes: The reading profiles are defined in the next section.
+ reading_profiles : 
  - settling_delay: (0-20) Delays after the stylus is first detected. (not seconds)
  - number_of_reading: Number of reading needed for a good measurements.
  - max_deviation: (1-100) Amount of deviation allowed between each reading.
  - Notes: For more information : [user_guide/Big-Fin-Scientific-Fish-Board-Integration-Guide-V2_0.pdf](dcs5/configs/Big-Fin-Scientific-Fish-Board-Integration-Guide-V2_0.pdf)
+ output_modes :
  - swipe_threshold: Minimal distance (mm) for a stylus swipe to be valid.
  - segments_limits: Define the limit of the different swipe segment.
  - segments_mode: The corresponding output_mode for each swipe segment.
  - mode_reading_profiles: The corresponding reading_profiles for each output modes.
+ keys_maps: Mapping of the key to either command or keyboard input.
  - Notes: The name of the keys are set in [dcs5/configs/devices_sepcification.json](dcs5/config/devices_sepcification.json).
  - Notes: Valid commands `["BACKLIGHT_UP", "BACKLIGHT_DOWN", "CHANGE_STYLUS", "UNITS_mm", "UNITS_cm"]`
  - Notes: See the [dcs5/controller_configurations.py](dcs5/controller_configurations.py) module for the valid keyboard input.
  - Notes: List of command are accepted.

### [dcs5/configs/devices_sepcification.json](dcs5/config/devices_sepcification.json)
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

### [dcs5/configs/control_box_parameters.json](dcs5/configs/control_box_parameters.json)
Values of the builtin parameters of the control box. From BigFin documentation [user_guide/Big-Fin-Scientific-Fish-Board-Integration-Guide-V2_0.pdf](dcs5/configs/Big-Fin-Scientific-Fish-Board-Integration-Guide-V2_0.pdf).

## server

The application can be launch with a server to communicate with the board. This feature is working but still in development.
The server port and address are set ins the [dcs5/configs/server_configuration.json](dcs5/config/server_configuration.json) file. Contact me for more information,






