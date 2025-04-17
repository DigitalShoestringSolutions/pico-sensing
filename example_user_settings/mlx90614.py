# basic strings
wifi_ssid     = '***'
wifi_password = '***'
mqtt_broker   = '***'
machine_name  = "pico_mlx90614"

# Temperature detection thresholds (Shoestring Temperature Monitoring v1)
th_low = 20
th_high = 30

# Sensor and sampling definition
from core.mqtt import publish
from sensors.mlx90614 import MLX90614

def cycle():

    temp = MLX90614().sample()["temperature"] # Uses default pinout (Grove breakout board bus 0, sda on gpio 8, scl on gpio 9)
    
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
              "sensor"        : "MLX90614",
             },
            "temperature_monitoring/" + machine_name
            )
