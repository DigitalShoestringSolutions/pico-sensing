# pulse_counters.py 

# Standard imports
import time

# Installed imports
from machine import Pin

# Local imports
#none

class PulseCounter:

    def __init__(self, pin_num: int, multiplier: float = 1):
        """Counts pulses on a button input.
        
        :param int pin_num:      Pin number to detect edges on. On Raspberry Pi Pico, this is the GP numbering scheme.
        :param float multiplier: Scale readings by this factor before returning them
        """
        # Setup input and callback
        self._input_pin = Pin(pin_num, mode=Pin.IN, pull=Pin.PULL_UP)
        self._input_pin.irq(self._on_pulse, Pin.IRQ_FALLING)

        # Save other args
        self.multiplier = multiplier

        # Init new variables
        self._count = 0
        self._old_count = 0
        self._old_time = time.ticks_us()


    def _on_pulse(self, pin):
        """Callback handler. Minimal activity here for fast callback.
        pin argument is not used, but is required to be handled
        """
        self._count += 1


    def recent_pulses_and_density(self, timescale: float = 1) -> tuple:
        """Returns the number of pulses since this function was last called.

        Also returns the same divided by the time since this function was last called, multipled by timescale.

        :param float timescale: (optional) Further scale the density measurement by this value, in addition to the usual scaling by `multipler` set when constructing
        """
        # Read count and timestamp. Copy once so pulses while this function is executing are not lost.
        new_count = self._count
        new_time = time.ticks_us()

        # Calculate detla
        delta_count = new_count - self._old_count
        delta_time = time.ticks_diff(new_time, self._old_time) / 1000000  # Handle overflow, convert microseconds to seconds
        density = delta_count / delta_time
        
        # Save data for next time
        self._old_count = new_count
        self._old_time = new_time

        # Scale the output values if multiplier used
        if self.multiplier != 1:
            delta_count *= self.multiplier  # If self.multipler == 1, don't multiply by 1 so it can stay an int
            density *= self.multiplier
        density *= timescale

        # Return values
        return delta_count, density


class FlowSensor(PulseCounter):

    def __init__(self, pin_num: int, pulses_per_litre: float):
        """Child of PulseCounter specalised for switch-output flow sensors.

        Uses units of litres and litres/hour, as that is what Grafana is currently interpreting the readings as.
        
        :param int pin_num:            Pin number to detect edges on. On Raspberry Pi Pico, this is the GP numbering scheme.
        :param float pulses_per_litre: Number of pulses the sensor emits for every litre of fluid that passes through it.
        """
        super().__init__(pin_num, multiplier=1/pulses_per_litre)

    def sample(self):
        volume, rate = self.recent_pulses_and_density(timescale=3600) # seconds -> hours
        return{
            "flow": volume,     # litres
            "flow_rate": rate,  # litres per hour
            }
