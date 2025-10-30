# basic strings
wifi_ssid     = '***'
wifi_password = '***'
mqtt_broker   = '***'

# Configure sensors
from sensors.pulse_counters import FlowSensor
flow_sensor_1 = FlowSensor(pin_num=28,            # A flow sensor connected to pin 28 (GP numbering)
                           pulses_per_litre=7.5,  # that outputs 7.5 pulses per litre passed.
                           data_tags={"machine":"MyMachineName1", "source":"MySourceName1"})  # Name the sensor and the water source

# Load system to transmit data
from core.mqtt import publish

# Define regularly scheduled activity
cycle_interval = 3  # cycle() will run every n seconds. Defaults to 1 if this line is omitted.
def cycle():
    publish(flow_sensor_1.sample(), topic = "flow/" + flow_sensor_1.data_tags["machine"])  # Get topic name from sensor instance
