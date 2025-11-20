# basic strings
wifi_ssid     = '***'
wifi_password = '***'
mqtt_broker   = '***'
machine_name  = "pico_power_3pu"

# Sensor and sampling definition
from sensors.adcs import pico_adc as adc
#from sensors.adcs import ads1115 as adc # To use a different ADC, adapt the import like so
from models.current_transformer import CT
from core.mqtt import publish

clamp_output_range = 2.63 # Blue YHDC current transformer clamps and amplifiers typically produce this many volts DC out at rated current input

phases = (
    ("A", CT(20/clamp_output_range), adc(0)), # 20A max current input rating, attached to pin 26
    ("B", CT(20/clamp_output_range), adc(1)),
    ("C", CT(20/clamp_output_range), adc(2)),
    )

def cycle():
    for ph in phases:
        publish(
            {"machine":machine_name, "phase":ph[0]} | ph[1](ph[2].sample()), # mqtt payload. CT.__call__() is a dict containing current. pico_adc.sample() returns median voltage from a burst of samples as float.
            "power_monitoring/" + machine_name + "/" + ph[0]                 # mqtt topic including both machine name and phase name
            )
