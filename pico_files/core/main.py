"""Generic cycle supervisor for raspi pico.
Connects to WiFi if credentials supplied.
Repeatedly runs the function cycle() every cycle_interval
Blinks the LED every cycle
"""

# standard imports
import machine          # Onboard LED
from time import sleep
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

    try:
        cycle()                     # cycle() is imported from user_settings.py
        consecutive_error_count = 0 # reset count if good cycle

    except Exception as err:
        log(f"Unexpected {type(err)=}, {err=}") # otherwise ignore and skip unless below line is active
        #raise err
        consecutive_error_count += 1
        
        if consecutive_error_count >= consecutive_error_count_limit:
            log(f"Consecutive error count hitting limit of {consecutive_error_count_limit}, resetting MCU")
            sleep(5)        # Allow time to see above message before rebooting
            machine.reset() # reboot

        sleep(3) # slow blink to indicate issue

    # Normal blink pattern between cycles
    led.on()
    sleep(cycle_interval*0.95) # mostly on blink
    led.off()
    sleep(cycle_interval*0.05) # typically cycle function takes time so this is stretched. Even if not, 50ms still easily visible.
