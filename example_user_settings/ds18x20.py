# basic strings
wifi_ssid     = '***'
wifi_password = '***'
mqtt_broker   = '***'
machine_name  = 'pico_DS18B20'

# Temperature detection thresholds (Shoestring Temperature Monitoring v1)
th_low = 20
th_high = 30

# Sensor and sampling definition
from core.mqtt import publish
from sensors.ds18x20 import DS18X20
mysensor = DS18X20(12) # Connect to GPIO pin 12. Keeping class instance in this case allows higher sample rate

def cycle():

    temp = mysensor.sample()["temperature"]

    if temp > th_high:
        AlertVal = 1
    elif temp < th_low:
        AlertVal = -1
    else:
        AlertVal = 0

    publish ({"machine"       : machine_name,
              "temp"          : temp,
              "AlertVal"      : AlertVal,
              "ThresholdLow"  : th_low,
              "ThresholdHigh" : th_high,
              "sensor"        : "DS18B20"
             },
             "temperature_monitoring/" + machine_name # MQTT topic can either be defined as a global variable mqtt_topic or supplied as 2nd arg to publish() like so
            )
