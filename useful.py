import storage
import supervisor
import time
import os
SAFEMODESET = 0x77
SAFEMODECLEAR = 0x00
NVM_INDEX_SAFEMODE = 0
SLEEP_MEMORY_ERROR=1
SLEEP_MEMORY_ERROR_SIZE=2 # 2 bytes for reason size
SLEEP_MEMORY_ERROR_REASON=4


# safemode.py & boot.py file write
def ensure_free_space(file, data):
    MAX_ENTRIES = int(os.getenv("GOOD_ENOUGH_MAX_LOG_ENTRIES", "10"))
    # calculate the size of the data in bytes
    data_size = len(data.encode('utf-8'))
    # get the free space in bytes

    def get_free_space():
        s = storage.getmount('/')
        return s.statvfs(0)[0] * s.statvfs(0)[3] 
        # consider 4 for non-priveleged free blocks
        # https://docs.circuitpython.org/en/latest/shared-bindings/os/index.html#os.statvfs

    def get_total_space():
        s = storage.getmount('/')
        return s.statvfs(0)[0] * s.statvfs(0)[2]

    free_space = get_free_space()
    print("Free space: {} bytes.".format(free_space), end="")
    if free_space < data_size:
        print("Need {} bytes.".format(data_size), end="")
        # check for 4x the space needed, MAX_ENTRIES * (errors/boot/safemode.json & code)
        if free_space < data_size * MAX_ENTRIES and get_total_space() > data_size * MAX_ENTRIES * 4:
            print("Keeping {} entries in file {}".format(MAX_ENTRIES,file))
            fHandle = os.open(file, os.O_RDWR)
            fStats = os.fstat(fHandle)
            os.close(fHandle)
            if(fStats.st_size > data * 10):
                # read in 10 lines, the lines are not consistent length, then read the next ten lines into another variable until the end of the file is reached, then use the last 10 lines from the two combined sets of lines (11 minimum, 20 maximum lines). Write this over the original filename
                storage.remount("/", False)  # writeable by CircuitPython
                lines = []
                with open(file, "r") as fp:
                    old_lines = lines
                    lines = fp.readlines(10)
                    if len(lines) < 10:
                        lines = old_lines[-(10-len(lines)):] + lines
                    fp.close()
                with open(file, "w") as fp:
                    fp.writelines(lines)
                    fp.flush()
                    fp.close()
                print(".")
        else:
            print("Not enough space to save 30 entries for each log file, removing {}".format(file))
            os.remove(file)

        
def precode_file_write(file, data):
    storage.remount("/", False)  # writeable by CircuitPython
    try:
        ensure_free_space(file, data)
    except Exception as e:
        print("Error ensuring free space:", e)
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
