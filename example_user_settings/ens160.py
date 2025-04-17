# basic strings
wifi_ssid     = '***'
wifi_password = '***'
mqtt_broker   = '***'
machine_name  = 'pico_ENS160'
mqtt_topic    = "airquality_monitoring/" + machine_name

# Sensor and sampling definition
from sensors.ens160 import ENS160
from core.mqtt import publish

def cycle():
    publish({"machine": machine_name} | ENS160().sample()) # no benefit to keeping sensor class instance in this case
