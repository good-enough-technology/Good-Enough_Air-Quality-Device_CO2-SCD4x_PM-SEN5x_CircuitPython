import json
import microcontroller
import supervisor
import time
import alarm
import struct
from useful import *
#from alarm import sleep_memory as sleep_memory
from microcontroller import nvm as sleep_memory

if(supervisor.runtime.safe_mode_reason == supervisor.SafeModeReason.PROGRAMMATIC):
    # record deliberate reset reason
    if sleep_memory[SLEEP_MEMORY_ERROR] == 1:
        data_size = struct.unpack("H",bytes(sleep_memory[SLEEP_MEMORY_ERROR_SIZE:SLEEP_MEMORY_ERROR_SIZE+2]))[0]
        data = bytearray.decode(sleep_memory[SLEEP_MEMORY_ERROR_REASON:SLEEP_MEMORY_ERROR_REASON+data_size], 'utf-8')
        precode_file_write("/errors_s.json", data=data) 
        print("error saved to /errors_s.json")
        time.sleep(2)
# clear the error if present
sleep_memory[SLEEP_MEMORY_ERROR] = 0  



# safemode.py is the entry point for SAFE MODE (hard fault, etc.)
# store supervisor.runtime.safe_mode_reason since it won't be available during boot.py or code.py

# NVM Safe Mode - to cross-check against safemode reason
if microcontroller.nvm[NVM_INDEX_SAFEMODE] != SAFEMODESET:
    microcontroller.nvm[NVM_INDEX_SAFEMODE] = SAFEMODESET

# set up the safemode dict
safemode_dict = {}
safemode_dict["safemode_reason"] = str(supervisor.runtime.safe_mode_reason)
update_restart_dict_time(safemode_dict)  # add timestamp
update_restart_dict_traceback(safemode_dict)  # supervisor.get_previous_traceback


# write dict as JSON
print("safemode: ", safemode_dict["safemode_reason"])
precode_file_write("/safemode.json", json.dumps(safemode_dict))  # use storage.remount()
print("safemode reason saved to /safemode.json")
time.sleep(3)
if False:  # check for any safemode conditions where we shouldn't RESET
    pass
else:
    # RESET out of safe mode
    microcontroller.reset()  # or alarm.exit_and_deep_sleep()