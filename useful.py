import storage
import supervisor
import time

SAFEMODESET = 0x77
SAFEMODECLEAR = 0x00
NVM_INDEX_SAFEMODE = 0
SLEEP_MEMORY_ERROR=1
SLEEP_MEMORY_ERROR_SIZE=2 # 2 bytes for reason size
SLEEP_MEMORY_ERROR_REASON=4


# safemode.py & boot.py file write
def precode_file_write(file, data):
    storage.remount("/", False)  # writeable by CircuitPython
    with open(file, "a+") as fp:
        fp.write(f"{data}\n")
        fp.flush()
    storage.remount("/", True)   # writeable by USB host


def update_restart_dict_time(things_dict):
    things_dict["timestamp"] = supervisor.ticks_ms()
    return things_dict

def update_restart_dict_traceback(things_dict):
    things_dict["traceback"] = supervisor.get_previous_traceback()
    return things_dict
