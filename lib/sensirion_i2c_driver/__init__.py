# -*- coding: utf-8 -*-
# (c) Copyright 2019 Sensirion AG, Switzerland

# from __future__ import absolute_import, division, print_function
from .version import version as __version__  # noqa: F401
from .device import I2cDevice  # noqa: F401
from .connection import I2cConnection  # noqa: F401

import sys
if sys.implementation.name.lower() == "circuitpython":
    from .circuitpython_i2c_transceiver import CircuitPythonI2cTransceiver as I2cTransceiver
else:
    from .linux_i2c_transceiver import LinuxI2cTransceiver as I2cTransceiver

from .command import I2cCommand  # noqa: F401
from .sensirion_command import SensirionI2cCommand  # noqa: F401
from .crc_calculator import CrcCalculator  # noqa: F401

__copyright__ = '(c) Copyright 2019 Sensirion AG, Switzerland'
