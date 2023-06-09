# Good-Enough.technology Air Quality Device
A [CircuitPython](https://www.circuitpython.org/) project to display and upload Air-Quality data to Adafruit IO via MQTT, with throttling.

Proof of concept for logging errors, rebooting automatically and displaying terminal plus user content.

Depends on the Sensirion SCD4x (CO2) and SEN5x (Particulate Matter) sensors, and a 240x135 pixel display.

Intended for use on an Adafruit ESP32-S2 or S3 Reverse TFT Feather, but any wifi/display enabled board on circuitpython should work with minor tweaks (display element positions).

Includes the two linked libraries for Sensirion SEN5x (+ base i2c driver) in the lib folder, the remaining requirements should be installed with `circup install --auto`

Install circup with `pip install circup`

# Case - Laser Cut - 3D Printed one is available by same author
## Onshape cad link:
https://cad.onshape.com/documents/6bc686011b7016b1f9cf4f36/w/be00425a47ebc57f8f53a4b4/e/f36a69b4b0d941c2df68cdbc
## Photos for instructions:
https://photos.app.goo.gl/qWk8Gv1RB1viL9Nz9


# Attribution
 - [https://github.com/rsms/inter](https://github.com/rsms/inter) Contains font file Inter, specifically the Windows Hinted version for Desktop, Thin. Using fontforge then exported to bdf.
 - [https://github.com/good-enough-technology/CircuitPython_sensirion_i2c_sen5x](https://github.com/good-enough-technology/CircuitPython_sensirion_i2c_sen5x) Contains SEN5x Driver code forked from Sensirion and modified for Circuitpython support
 - [https://github.com/good-enough-technology/CircuitPython_sensirion_i2c_driver](https://github.com/good-enough-technology/CircuitPython_sensirion_i2c_driver) Contains I2C Driver code forked from Sensirion and modified for Circuitpython support
 - [https://www.adafruit.com](https://www.adafruit.com) Uses drivers and software and hardware from Adafruit
