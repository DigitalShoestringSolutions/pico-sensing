# Replace the contents of this file with something from example_user_settings.
# Here is a template / minimal outline for making a new one.

wifi_ssid     = '***' # WiFi network name
wifi_password = '***'
mqtt_broker   = '***' # Usually an IPv4 address eg 192.168.31.41

from sensors.mysensor import MYSENSOR
from core.mqtt import publish

def cycle():                   # The pico will repeatedly run this function.
    publish(MYSENSOR.sample()) # Gather data and publish it to MQTT broker