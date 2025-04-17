"""Thin wrapper for driver that is already part of standard lib.
Sails painfully close to overwriting namespace but somehow doesn't self import"""

from machine import Pin
import onewire
from time import sleep
import ds18x20


class DS18X20:
    """DS18x20 temperature sensor.    
    Use read_temp() to get a float in celsius, or sample() to put that in a dictionary under key 'temperature'.
    """

    def __init__(self, pin_number):
        """Create a onewire bus and scan for DS18X20 temperature sensors.

        Supports only one sensor per pin / bus.
        
        :param int pin_number: GPIO pin number to look for a DS18X20 sensor on. 
        """

        ow = onewire.OneWire(Pin(pin_number)) # create a OneWire bus. Doesn't need to be saved after use below. Only classes self.dss and self.ds are reused.
        self.dss = ds18x20.DS18X20(ow)        # All ds18x20 sensors on bus
        scan = self.dss.scan()                # list of bytearrays
        if len(scan) == 0:
            raise IndexError(f"No DS18X20 devices detected on onewire bus {pin_number}. Is that the GPIO pin that the sensor is attached to?")
        self.ds = scan[0]                     # The first (and assumed only) sensor on the bus. Others ignored.

        # After a hard power cycle the first sample is invalid before sleeping for at least 0.75s
        self.first_sample = True

    def read_temp(self) -> float:
        """Read temperature in celsius."""
        self.dss.convert_temp()               # Send command to all ds18x20 sensors on bus to take a measurement
        if self.first_sample:
            sleep(0.75)                       # Recommended always but doesn't appear to be necessary after first sample.
            self.first_sample = False         # Delay is no longer needed
        return self.dss.read_temp(self.ds)

    def sample(self) -> dict:
        """Reads temperature in celsius and returns as a dictionary under the key `temperature`."""
        return {"temperature" : self.read_temp()}


# test
if __name__ == '__main__':
    print("testing DS18X20")
    mysensor = DS18X20(12)
    while True:
        sleep(1)
        print(mysensor.sample())