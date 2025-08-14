"""
logging.py
Logging system for Micropython.

Public API: the function log()

No log levels. Include them in your message if you want to.
Messages are cast to string, timestamped (microsecond resolution) and printed to serial and also written to file.
Automatic file size limitation, rotation and deletion.

sample usage:
from logging import log
mymsg = "Sensor recorded reading " + str(1234)
log(mymsg)

Inspired by http://www.d3noob.org/2024/03/logging-and-troubleshooting-on.html
"""

# Standard library imports
import os

# Local imports
from core.timestamp import get_timestamp

# settings
log_filename = "log.txt"
log_filename_old = "log_old.txt"
log_file_size_limit = 200000 # Bytes before rotating. 200kB, so both log files toogether will take max 20% of Pico's 2MB flash memory.
default_max_loginfo_size = 200 # Characters before log message is truncated

def _create_log_file():
    """Check to see if primary log file is present and create if necessary."""    
    try:
        os.stat(log_filename)
        print(f"Logger: log file {log_filename} already exists")
    except:
        print(f"Logger: log file {log_filename} missing - creating...")
        f = open(log_filename, "w")
        f.close()


# Public function
def log(loginfo:str, print_loginfo:bool=True, max_loginfo_size=default_max_loginfo_size):
    """Append a message to the plaintext log file. A timestamp from core.timestamp (rtc.datetime() + time_ns()) is added.
    
    :param str loginfo:              The message to be appended to the log file.
    :param bool=True print_loginfo:  (optional) If `True`, loginfo will be passed to print() to display in the serial terminal
    :param int=200 max_loginfo_size: (optional) The number of characters after which str(loginfo) will be truncated
    """

    # Get the timestamp as soon as called
    timestring = get_timestamp()

    # Check the file size
    filestats = os.stat(log_filename)
    filesize = filestats[6]           # File size in bytes

    # Truncate loginfo if long
    loginfo = str(loginfo) # if something other than a string is supplied, attempt to cast it.
    if len(loginfo) > max_loginfo_size:
        loginfo = loginfo[:max_loginfo_size] + "..."

    # Print to terminal if required
    if print_loginfo:
        print(loginfo)

    if(filesize < log_file_size_limit):
        try:

            # loginfo is recast to string. Add filesize (right aligned, padded to fit maximum)
            logline = timestring +" "+ f"{str(filesize):>{len(str(log_file_size_limit))}}"  +" "+ loginfo +"\n"

            # Write to file
            with open(log_filename, "at") as f:
                f.write(logline)

        except Exception as err:
            print("ERROR when logging: Problem saving file:", err)

    else:
        print("Logger: log file size " + str(filesize) + " exceed limit of " + str(log_file_size_limit) + ", rotating...")

        # Delete old log file if it exists
        try:
            os.remove(log_filename_old)
        except OSError:                           # it might not exist, so ignore failure
            pass

        os.rename(log_filename, log_filename_old) # Rename current log file to old
        _create_log_file()                        # Create new log file
        log(loginfo)                              # Try again. Should now find an empty file.


# Startup
_create_log_file() # Although when writing the file would be created as needed, this is done first so the filesize can be checked without error.


# Run this script directly to test
if __name__ == '__main__':
    print("testing logging")
    log("Did this appear in the logs?")
    log("How about this? Explicitly printed to terminal", True)
    log("Or this? Not printed.", False)
    print("logging test complete")
