# Standard library imports
from machine import I2C, Pin
from time import sleep

# Local imports
from core.logging import log # Writing messages to file

class MLX90614:

    # RAM offsets with 16-bit data, MSB first
    REG_TOBJ1 = 0x07   # Radiant object 1 temperature
    GAIN = 50          # divide raw reading by this to get temperature in K

    def __init__(self, i2cbus_num=0, sda_pin_num=None, scl_pin_num=None, i2caddr=0x5a, unit="C"):
        """"Class for reading data from the MLX90614 infrared temperature sensor.

        Datasheet: https://www.melexis.com/en/documents/documentation/datasheets/datasheet-mlx90614
    
        :param int i2c_bus_num: The I2C bus number. Default 0.
        :param int sda_pin_num: The pin number for the I2C data line. Default is suitable for specified bus if using the Grove breakout board for pico.
        :param int scl_pin_num: The pin number for the I2C clock line. Default is suitable for specified bus if using the Grove breakout board for pico.
        :param int i2c_addr:    The I2C address of the MLX90614. Default 0x5a.
        :param str unit:        The unit to return temperature readings in. Can also be specified at sample time. Currently supported options are `K`, `C` and `F`. Default `C`.
        """

        # Default pin numbers depend on bus! This allows easy use on Grove breakout boards by supplying only the bus number.
        # Pin numbers are different on Gravity boards. I expect them to be less commonly used with the MLX; all 3 numbers will need to be specified.
        if sda_pin_num is None:
            if i2cbus_num == 0:
                sda_pin_num = 8
            elif i2cbus_num == 1:
                sda_pin_num = 6
        if scl_pin_num is None:
            if i2cbus_num == 0:
                scl_pin_num = 9
            elif i2cbus_num == 1:
                scl_pin_num = 7

        # machine.I2C object has no attribute '__exit__' i.e. can't be used with context manager at sample time, so save now
        self.i2c = I2C(i2cbus_num, sda=Pin(sda_pin_num), scl=Pin(scl_pin_num), freq=100000) # "The maximum frequency of the MLX90614 SMBus is 100 kHz" datasheet page 21

        self.i2caddr = i2caddr
        self.default_unit = unit


    def read_temperature_kelvin(self):
        """Read radiant object temperature from the MLX90614 sensor and return as float in Kelvin."""
        
        # Read 2 bytes from sensor
        readbytes = self.i2c.readfrom_mem(self.i2caddr, MLX90614.REG_TOBJ1, 2)

        # Decode bytes
        readints = [int(byte) for byte in readbytes]
        reading = (readints[1] << 8) | (readints[0])

        # Post-process gain
        temperature = reading / MLX90614.GAIN

        return temperature


    def sample(self, unit=None, rounding_dp=2):
        """Read radiant object temperature from the MLX90614 sensor and return in a dictionary under key `temperature`.
        
        :param unit:            The unit of temperature to return the reading in. Currently supported options are `K`, `C` and `F`. Defaults to the unit set at class instance creation, which defaults to C.
        :param int rounding_dp: The number of decimal places to round the temperature reading to. More than 2 are unlikely to be useful as readings are always a multiple of 0.02 K.
        """

        temperature = self.read_temperature_kelvin()

        # Convert unit if required
        if unit is None:
            unit = self.default_unit # Use default from class creation if not overridden in call arg
        if unit == "K":
            pass
        elif unit == "C":
            temperature -= 273.15
        elif unit == "F":
            temperature = ((temperature - 273.15) * 1.8) + 32
        else:
            log(f"Warning: MLX90614 unit {unit} not recognised - using Kelvin") # Raise error? Print a warning will do for now.

        # Package and return readings as dictionary
        data = dict()
        data['temperature'] = round(temperature, rounding_dp)
        return data


# test
if __name__ == '__main__':
    print("testing MLX90614")
    mymlx = MLX90614(0)            # Grove breakout board bus 0
    #mymlx = MLX90614(1)            # Grove breakout board bus 1
    #mymlx = MLX90614(0, 4, 5)      # Gravity breakout board bus 0
    #mymlx = MLX90614(1, 26, 27)    # Gravity breakout board bus 1.
    print("i2c scan:", mymlx.i2c.scan())
    while True:
        print("sample:", mymlx.sample())
        sleep(1)