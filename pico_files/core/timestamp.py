# timestamp.py

# Standard library imports
import machine

# Startup
rtc=machine.RTC()

def get_timestamp():
    """Get a string containing the current local time in ISO8601 format using machine.RTC().datetime()"""

    timestamp=rtc.datetime()
    timestring="%04d-%02d-%02dT%02d:%02d:%02d+00:00"%(timestamp[0:3] + timestamp[4:7])

    return timestring

# test
if __name__ == '__main__':
    print(get_timestamp())
