# Inspired by https://projects.raspberrypi.org/en/projects/get-started-pico-w/2

# Standard library imports
import network
import time
import ntptime               # Get time from network after connecting
import machine               # Onboard LED and rebooting

# Local imports
from core.logging import log # Writing messages to file

# Initialise
led = machine.Pin("LED", machine.Pin.OUT)

def connect(ssid:str, password:str, max_attempts:int=50):
    """Connect to WiFI and update time from Network Time Protocol.

    Wrapper for network.WLAN
    
    :param str ssid:         The name of the WiFi network to connect to.
    :param str password:     The pre-shared plaintext passkey to connect to this WiFi network with.
    :param int max_attempts: After this many failed attempts to connect, the device will reboot.
    """
    
    log(f"Local time before WiFi connection is {time.localtime()}")

    # Prepare connection
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(ssid, password)

    # Loop
    attempt_count = 0
    while wlan.isconnected() == False:

        # Reboot if no connection after many attempts
        if attempt_count >= max_attempts:
            log(f"Rebooting due to {attempt_count} failed attempts to connect to wifi!")
            time.sleep(5)   # allow time to see above message before rebooting
            machine.reset() # reboot the pico

        # Retry connection
        attempt_count += 1
        log(f'Attempt {attempt_count} to connect to wifi network {ssid}...')

        # Blink LED (mostly off) to visually indicate connection attempt in progress
        led.on()
        time.sleep(0.05)
        led.off() # mostly off blink while trying to connect
        time.sleep(0.95)

    # Report sucessful connection
    ip = wlan.ifconfig()[0]
    log(f'Connected to WiFi {ssid} as {ip}')
    
    # Set time
    try:
        ntptime.settime()
        time_update_message = "Clock sucessfully updated from network."
    except Exception:
        pass # ignore errors!
        time_update_message = "An exception occured while updating clock from network."
    log(f"{time_update_message} Local time is now {time.localtime()}")


# test
if __name__ == '__main__':
    from user_settings import wifi_ssid, wifi_password
    connect(wifi_ssid, wifi_password)