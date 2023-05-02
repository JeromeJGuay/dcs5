# Dcs5 Controller app

NOT UP TO DATE FOR THE CURRENT RELEASE. CONTACT ME FOR HELP

This python (python 3.10) application provides graphical interface to interact with a BigFin Dcs5 XT measuring board via Bluetooth.
The application will turn stylus input on the measuring board into keyboard inputs basically turning the dcs5 measuring board into a wireless keyboard.

# Download from releases
Downloading the Dcs5 Controller App from the latest release.
1. Download `dcs5.zip` from the last version here: https://github.com/JeromeJGuay/dcs5/releases.
2. Unzip `dcs5.zip`
3. Run `dcs5.exe`


## Requirements to install the python package. (not required to use the app as a standalone.)
1) python 3.10

## User Guide
See the [user_guide/UserGuide_fr.pdf](doc/UserGuide_fr.pdf). French only.

## Configurations

3 json files are used to set different parameters for the application.

for xt:
### [dcs5/default_configs/xt_controller_configuration.json](dcs5/default_configs/xt_controller_configuration.json)

for micro:
### [dcs5/default_configs/micro_controller_configuration.json](dcs5/default_configs/micro_controller_configuration.json)
The controller_configuration.json is used to configure the controller behavior.
+ client: Measuring board bluetooth information.
  - device_name: TODO
  - mac_address: TODO
  - marel_ip_address: TODO
+ launch_settings: setting used when the app is launch.
  - output_mode: TODO
  - reading_profile: TODO
  - dynamic_stylus_mode: (true/false) If true, reading profiles will change for each output mode as defined in the next section.
  - backlight_level: (0-95) Backlight intensity
  - length_units: TODO
  - stylus: TODO
  - auto_enter: TODO
  Notes: The reading profiles are defined in the next section.
+ reading_profiles:
  - settling_delay: (0-20) Delays after the stylus is first detected. (not seconds)
  - number_of_reading: Number of reading needed for a good measurements.
  - max_deviation: (1-100) Amount of deviation allowed between each reading.
  
  *Notes: For more information : [user_guide/Big-Fin-Scientific-Fish-Board-Integration-Guide-V2_0.pdf](doc/Big-Fin-Scientific-Fish-Board-Integration-Guide-V2_0.pdf)*
+ output_modes:
  - swipe_threshold: Minimal distance (mm) for a stylus swipe to be valid.
  - segments_limits: Define the limit of the different swipe segment.
  - segments_mode: The corresponding output_mode for each swipe segment.
  - mode_reading_profiles: The corresponding reading_profiles for each output modes.
+ keys_maps: Mapping of the key to either command or keyboard input.
  - control_box:
  - control_box_mode:
  - board:
  - board_mode:

  
  - Two commands for a key. One default and one for when MODE is activated.
  - The name of the keys are set in [dcs5/default_configs/devices_specification.json](dcs5/default_configs/xt_devices_specification.json).
  - Valid commands `"BACKLIGHT_UP", "BACKLIGHT_DOWN", "CHANGE_STYLUS", "UNITS_mm", "UNITS_cm", "CHANGE_OUTPUT_MODE", "MODE", "MODE_TOP", "MODE_LENGTH", "MODE_BOTTOM", print <string to print>]`
  - See the [dcs5/controller_configurations.py](dcs5/controller_configurations.py) module for the valid keyboard input.
  - List of commands are accepted and executed one at a time.

### [dcs5/default_configs/devices_specification.json](dcs5/default_configs/xt_devices_specification.json)
+ board:
  - number_of_keys: The keys correspond to the grey circle on the board.
  - key_to_mm_ratio: The distance in mm from one edge of a circle (larger one) to the next.
  - zero: The distance (mm) that would be the key 0 given that the first key on the board is key 1.
  - detection_range: Offset on the left in mm for stylus detection. 
  - keys_layout: Ordered lists for the name of the top keys and the for the bottom keys. These names are used to map command.
    * Top:
    * Bottom
  
  *Notes: The two list (top and bottom) should not contain identical names.*
+ control_box:
  - model: TODO
  - keys_layout: Mapping of the controller box key builtin id to meaningful name. These names are used to map command. 
+ stylus_offset: Offset in mm that is added ot the value measured by the board. 
  - Notes: These values will depend on the calibration.

### [control_box_parameters.json](dcs5/control_box_parameters.py)
Values of the builtin parameters of the control box.  Json file is written when a new config is created.
From BigFin documentation [user_guide/Big-Fin-Scientific-Fish-Board-Integration-Guide-V2_0.pdf](doc/Big-Fin-Scientific-Fish-Board-Integration-Guide-V2_0.pdf).




