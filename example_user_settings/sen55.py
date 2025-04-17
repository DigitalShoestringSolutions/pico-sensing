# basic strings
wifi_ssid     = '***'
wifi_password = '***'
mqtt_broker   = '***'
machine_name  = '***'
mqtt_topic    = 'airparticle_monitoring/' + machine_name # MQTT topic can either be defined like so as a variable or supplied as 2nd arg to publish()

# Sensor and sampling definition
from sensors.sen55 import SEN55
mysen = SEN55(1) # Grove breakout board I2C bus 1. Keeping class instance allows for higher sample rate in this case.
from core.mqtt import publish

def cycle():
    publish({"machine": machine_name} | mysen.sample()) # mqtt payload. mysen.sample() is a dict containing particulate data.
