import storage
import digitalio
import microcontroller
import time
import board
import busio
import os
import alarm

import json
import microcontroller
import struct
from useful import *
#from alarm import sleep_memory as sleep_memory
from microcontroller import nvm as sleep_memory

### Start of safemode portion of boot.py
# boot.py is the entry point for RESET (software, reset button, or power cycle)
# read and process safemode.json if desired


if(microcontroller.cpu.reset_reason == microcontroller.ResetReason.SOFTWARE):
    # record deliberate reset reason
    if sleep_memory[SLEEP_MEMORY_ERROR] == 1:
        data_size = struct.unpack("H",bytes(sleep_memory[SLEEP_MEMORY_ERROR_SIZE:SLEEP_MEMORY_ERROR_SIZE+2]))[0]
        data = bytearray.decode(sleep_memory[SLEEP_MEMORY_ERROR_REASON:SLEEP_MEMORY_ERROR_REASON+data_size], 'utf-8')
        precode_file_write("/errors_b.json", data=data) 
        print("error saved to /errors_b.json")
# clear the error if present
sleep_memory[SLEEP_MEMORY_ERROR] = 0  


# NVM Safe Mode - clear it for the next Safe Mode
if microcontroller.nvm[NVM_INDEX_SAFEMODE] != SAFEMODECLEAR:
    microcontroller.nvm[NVM_INDEX_SAFEMODE] = SAFEMODECLEAR

# set up the boot dict
boot_dict = {}
boot_dict["reset_reason"] = str(microcontroller.cpu.reset_reason)
update_restart_dict_time(boot_dict)  # add timestamp
update_restart_dict_traceback(boot_dict)  # supervisor.get_previous_traceback

# write dict as JSON
precode_file_write("/boot.json", json.dumps(boot_dict))  # use storage.remount()

### End of safemode portion of boot.py


## Main boot.py code for project

# if hasattr(board,'DISPLAY'):
#     # board.DISPLAY.brightness = 0.0  # turn off display to save power
#     # board.DISPLAY.auto_brightness = False  # turn off auto brightness
#     board.DISPLAY.rotation = 180  # rotate display 180 degrees

#Setup boot toggle pin, also timer skip pin
D2 = digitalio.DigitalInOut(board.D2)
D2.direction = digitalio.Direction.INPUT
D2.pull = digitalio.Pull.DOWN
print("D2.value=",D2.value)

# Check if the CircuitPython settings file exists -- MOVE TO BOOT.PY
if 'good-enough.toml' not in os.listdir():
    if(D2.value==True):
        # If it doesn't exist, create a default settings file
        print("Disabling usb drive to create settings.toml")
        try:
            # if storage.is_mounted():  # Check if the storage is mounted
            #     # Unmount the current filesystem
            #     storage.umount("/")

            # # Remount the filesystem with the desired writable status
            # storage.disable_usb_drive()
            storage.remount(False)
            # storage.mount(storage.VfsFat(board.FLASH), "/", readonly=False)
            with open('settings.toml', 'w') as f:
                f.write('CIRCUITPY_WIFI_SSID="free4all_2G"\n')
                f.write('CIRCUITPY_WIFI_PASSWORD="password"\n')
                f.write('CIRCUITPY_AIO_USERNAME="tyeth"\n')
                f.write('CIRCUITPY_AIO_KEY="API_KEY_HERE"\n')
            # time.sleep(0.1)
            with open('good-enough.toml', 'w') as f:
                f.write('GOOD_ENOUGH_SERIAL="PREPRODUCTION"\n')
            time.sleep(0.1)
        finally:
            # Re-enable USB mass storage
            print("Re-enabling usb drive after creating settings.toml")
            # storage.umount("/")
            # storage.mount(storage.VfsFat(board.FLASH), "/", readonly=True)
            # storage.enable_usb_drive()
            storage.remount(True)

