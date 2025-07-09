"""mqtt.py

Working assumptions:
    - The broker and port will not change during a session, but the topic could.
    - The user would like a one-line interaction with the MQTT system

Public API: only the function 'publish'

"""


# Standard imports
import json                             # For formatting dictionaries with double quotes
from machine import unique_id           # Hardware instance specific identifier, for MQTT
from ubinascii import hexlify           # For rendering bytes objects into strings

# Installed imports
#none

# Local imports
from core.umqttsimple import MQTTClient
from core.timestamp import get_timestamp
from core.logging import log
from core.default_settings import *
from user_settings import *     # Overwrite default settings as required



def publish(msg, topic=mqtt_topic, broker=mqtt_broker, add_timestamp=True):
    """Publish an MQTT message.
    
    Arg reordering allows omitting kwargs in common use.
    Connection to the broker is re-established before sending and closed after each message, for simplicity.

    :param dict/str msg:       The message to publish. If a dictionary, will be formatted as json.
    :param str topic:          (optional) The MQTT topic to publish to. If not supplied, the variable `mqtt_topic` will be used.
    :param str broker:         (optional) The MQTT broker to publish to. Usually an IPv4 address eg `192.168.31.41`. If not suppplied the variable `mqtt_broker` will be used.
    :param bool add_timestamp: (optional) If `True`, an ISO8601 timestamp will be added to the message. If `msg` is a dictionary, it will be under the key `timestamp`. Else it will be prepended as a string.
    """

    if add_timestamp:

        # Get the timestamp first, as soon as possible after sampling
        timestamp = get_timestamp()

        # format the message
        if type(msg) is dict:                               # preferred
            # The below ordering allows the user to specify their own timestamp in the message dict if desired.
            # If an entry with key "timestamp" is not provided, one will be added using time of publication.
            #
            # json.dumps(mydict) returns a string which is very similar to the output of str(mydict),
            #   but crucially with json.dumps() strings have double quotes as required by the json spec,
            #   while str(mydict) gives single quotes and is not recognised as json.
            payload = json.dumps({'timestamp': timestamp} | msg)

        else:                                               # failover
            payload = "timestamp: " + timestamp + " " + str(msg)
    
    else:
        payload = str(msg) # if add_timestamp is not set, the payload is simply the message supplied. In case it is not a string, attempt to cast it.

    # Display
    #log(f"publishing to {broker} {topic}")
    log(payload)

    # publish to mqtt
    client = MQTTClient(hexlify(unique_id()).decode(), broker, keepalive=3600) # single use MQTT connection instance
    client.connect()
    client.publish(topic, payload)
    client.disconnect()
    
    # Confirm above has completed
    #log("mqtt publication complete")



# test
if __name__ == '__main__':
    log("testing MQTT publication")
    publish("hi")
    log("hi was published to mqtt")
