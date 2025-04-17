# This file contains default settings. Only for objects that need not be overwritten in user_settings.py

# wifi
wifi_ssid = None # will not attempt connection to wifi unless this is overwritten

# mqtt
mqtt_broker = None # In practice, the user must define the MQTT broker at some point. However, Having this here allows the publish() function to take the globally set variable it as a default arg
mqtt_topic = "shoestring-sensor"

# cycle
cycle_interval = 1 # seconds
def cycle():
    raise NotImplementedError("Cycle function is not defined in user_settings.py!")

# error handling
consecutive_error_count_limit = 10
wifi_error_count_limit = 20



# Finally, import the user-facing settings file to overwrite selected objects above
from user_settings import *