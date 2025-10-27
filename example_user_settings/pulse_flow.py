# basic strings
#wifi_ssid     = '***'
#wifi_password = '***'
#mqtt_broker   = '***'

# Configure sensors
from sensors.pulse_counters import FlowSensor
flow_sensor_1 = FlowSensor(pin_num=26, pulses_per_litre=7.5)  # A flow sensor connected to pin 26 (GP numbering) that outputs 7.5 pulses per litre passed.

# Load system to transmit data
from core.mqtt import publish

# Define regularly scheduled activity
cycle_interval = 3  # cycle() will run every n seconds. Defaults to 1 if this line is omitted.
def cycle():
    publish({"machine": "MyMachineName1", "source" : "MySourceName1" } | flow_sensor_1.sample())
