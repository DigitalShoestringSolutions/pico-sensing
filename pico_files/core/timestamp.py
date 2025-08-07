# timestamp.py

# Standard library imports
import machine
import time

# Startup
rtc=machine.RTC()

def get_timestamp():
    """Get a string containing the current local time in ISO8601 format using machine.RTC().datetime() assisted by time_ns()"""

    timestamp=rtc.datetime() # subsecond field is always 0, so use another clock interface for additional resolution.
    microseconds = str(time.time_ns())[-9:-3] # needs to be a string to do slicing to extract desired digits. Only us precision is available (last 3 digits of time_ns() are always 0).
    timestring="%04d-%02d-%02dT%02d:%02d:%02d"%(timestamp[0:3] + timestamp[4:7]) + "." + microseconds + "+00:00"

    return timestring

# test
if __name__ == '__main__':
    while True:
        print(get_timestamp())
        time.sleep(1)
