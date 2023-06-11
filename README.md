# Good-Enough.technology Air Quality Device
## Description
A [CircuitPython](https://www.circuitpython.org/) project to display and upload Air-Quality data to Adafruit IO via MQTT, with throttling.

Proof of concept for logging errors, rebooting automatically and displaying terminal plus user content.

Depends on the Sensirion SCD4x (CO2) and SEN5x (Particulate Matter) sensors, and a 240x135 pixel display.

Intended for use on an Adafruit ESP32-S2 or S3 Reverse TFT Feather, but any wifi/display enabled board on circuitpython should work with minor tweaks (display element positions).

Your circuitpython device should be running v8 or above, and the settings.toml file should be updated to have all the entries populated that are in this repository.

Includes the two linked libraries for Sensirion SEN5x (+ base i2c driver) in the lib folder, the remaining requirements should be installed with `circup install --auto`

Install circup with `pip install circup`

## Features

- Saves boot-reason/safemode-reason/errors to json files, waits for wifi (20s then reset), similar waiting for IO connection.
- Sends a sensible data rate, also handles throttling and bans in adafruit io (too much data per minute in case of multiple devices). 
- Displays log on half screen and metrics (plus health indicator circle) on other half (Metrics only rotate when repl/log/sensors are at sleep point of loop).
- Hold D2 during throttling, or during "Sleeping X seconds for Y datapoints", to skip sleep/throttle event

## TODO:

- TEST: Check free diskspace on boot, trim boot/safemode/errors.json - Deletes all but X entries
- Post errors to adafruit io during normal operation and mark posted. Then when diskspace clearing, kill off successfully posted events from json files. If offline, delete all but last 10 entries of each (configurable from settings.toml, default to 10 if missing, set at 30 in file).
- Turn off Automatic Baseline Calibration for CO2, pre-tune all sensors, allow turning on via config, but with manual reset and config change required. Idea is to connect external powersource, connect over wifi and turn on in settings.toml, reboot, leave running with ABC enabled in fresh air for over 24hrs, then turn off over wifi via settings.toml and reboot. Not sure auto calibration is saved automatically, and not lost by sudden reboot, so check. Should be fine if factory_reset never called.

## Case - Laser Cut - 3D Printed one is available by same author
### Onshape cad link:
https://cad.onshape.com/documents/6bc686011b7016b1f9cf4f36/w/be00425a47ebc57f8f53a4b4/e/f36a69b4b0d941c2df68cdbc
Go into the variables table of Onshape (right hand side has icons) and amend the material thickness value, the design should adapt. Then goto the drawing page, and choose update, then export that as an SVG or whatever you need to cut it out.

### Photos for instructions:
https://photos.app.goo.gl/qWk8Gv1RB1viL9Nz9


## Attribution
 - [https://github.com/rsms/inter](https://github.com/rsms/inter) Contains font file Inter, specifically the Windows Hinted version for Desktop, Thin. Using fontforge then exported to bdf.
 - [https://github.com/good-enough-technology/CircuitPython_sensirion_i2c_sen5x](https://github.com/good-enough-technology/CircuitPython_sensirion_i2c_sen5x) Contains SEN5x Driver code forked from Sensirion and modified for Circuitpython support
 - [https://github.com/good-enough-technology/CircuitPython_sensirion_i2c_driver](https://github.com/good-enough-technology/CircuitPython_sensirion_i2c_driver) Contains I2C Driver code forked from Sensirion and modified for Circuitpython support
 - [https://www.adafruit.com](https://www.adafruit.com) Uses drivers and software and hardware from Adafruit
