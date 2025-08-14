"""Generic cycle supervisor for raspi pico.
Connects to WiFi if credentials supplied.
Repeatedly runs the function cycle() every cycle_interval
Blinks the LED every cycle
"""

# standard imports
import machine          # Onboard LED
import time
from os import uname

# local imports
from core.default_settings import *
from user_settings import *     # Overwrite default settings as required
import core.wifi as wifi
from core.logging import log

# startup
log("starting up")
log(uname())                    # Log and display firmware version, platform etc.
if wifi_ssid is not None:       # Skip unless wifi_ssid has been overwritten in user_settings.py
    wifi.connect(wifi_ssid, wifi_password, wifi_error_count_limit) # blocking until sucessful. wifi_password must be defined in user_settings.py
led = machine.Pin("LED", machine.Pin.OUT)

# loop
log("starting main loop")
consecutive_error_count = 0

while True:
    
    last_cycle_start_time = time.ticks_us() # monotonic, add and diff below control overflow. Resample rather than offset previous. 
    time.sleep_ms(50)                       # Minimum cycle time. Even if cycle() is fast, 50ms is easily long enough to see the LED blinking off.
    led.off()

    try:
        cycle()                     # cycle() is imported from user_settings.py
        consecutive_error_count = 0 # reset count if good cycle

    except Exception as err:
        log(f"Unexpected {type(err)=}, {err=}") # otherwise ignore and skip unless below line is active
        #raise err
        consecutive_error_count += 1
        
        if consecutive_error_count >= consecutive_error_count_limit:
            log(f"Consecutive error count hitting limit of {consecutive_error_count_limit}, resetting MCU")
            time.sleep(5)   # Allow time to see above message before rebooting
            machine.reset() # reboot

        time.sleep(3) # slow blink (long off) to indicate issue

    # Normal blink pattern between cycles
    led.on() # mostly on blink
    while time.ticks_diff(time.ticks_add(last_cycle_start_time, int(cycle_interval*1000000)), time.ticks_us()) > 0: 
        pass # wait until loop has taken approximately long enough. 
