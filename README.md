Dcs5 Controller app
===================

This python application provides a tool to interface with a BigFin Dcs5 XT measuring board via Bluetooth.
At the moment, the app only works on Unix machines due to some unresolved problems with the Bluetooth packages. 
When launched, the controller app emulates keyboard inputs when the measuring board detects stylus input.

The controller can be launched in 2 modes:
    + Command Line Application (cli app).
    + Server (server). To send some simple command to the controller from a remote device. 

When the board sends data to the controller app, it is mapped to different outputs:
    + Single key press. (Any keys from a standard keyboard.)
    + Multiple key press. (ex: When the board returns a length measurements.)
    + Sends back a command to the board. (Changing the backlight level.)

The controller can be set in 3 different modes: Top/Length/Bottom.
    + Top : The controller maps the measured length to specific key values for the top row.
    + Length : The controller returns the measured length in mm or cm depending on the units selected.
    + Bottom : The controller map measured length to specific key values for the bottom row.

Using the Boards
================
+ The board uses magnet in the stylus (pen/finger) to make input.
+ The Fuel Gauge / Action light will flash when the board detects an input.
+ Input can be simple press or swipes.
+ To change the board input mode you can swipe in one of the four regions.
    - Top : Blue Zone.
    - Length: Left or Right grey Zone.
    - Bottom: Green Zone.
  When a swipes are detected the controller box backlights will flash.

Calibration
-----------
Although the board sends measurements value in mm, a specific offset needs to be added for each stylus.
The offsets value are in `dcs5/devices_specifications/dcs5_default_devices_specification.json` files.
These offsets value were determined using the one flat edges of the finger stylus when calibrating.
Thus, you need to use the one of the flat edges of the finger stylus when calibrating the board.  


Usage
=====
To call the application ...
```bash
:~$ dcs5 {cli_app, server}
```

cli app
-------
After launching the cli app, it will try to connect the board. Use the help command to see all the available commands. 

server
------
TODO

Configurations
--------------
The specific mapping for the controller keys are set in the `dcs5/configs/controller_configuration.json` file.



