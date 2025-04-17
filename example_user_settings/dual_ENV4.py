# basic strings
wifi_ssid     = '***'
wifi_password = '***'
mqtt_broker   = '***'

# Sensor and sampling definition
from core.mqtt import publish
from sensors.sht40 import SHT40
from sensors.bmp280 import BMP280

def cycle():
    publish({"machine":"pico_ENVIV_0"} | BMP280().sample() | SHT40().sample())   # both published to same broker, defined above
    publish({"machine":"pico_ENVIV_1"} | BMP280(1).sample() | SHT40(1).sample()) # both published to default topic
