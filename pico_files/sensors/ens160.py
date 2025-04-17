from machine import I2C, Pin
from time import sleep


class ENS160:

    # Register addresses
    OPMODE_REG    = 0x10 # This 1-byte register sets the Operating Mode of the ENS160.
    DATA_AQI_REG  = 0x21 # This 1-byte register reports the calculated Air Quality Index according to the UBA.
    DATA_TVOC_REG = 0x22 # This 2-byte register reports the calculated TVOC concentration in ppb.
    DATA_ECO2_REG = 0x24 # This 2-byte register reports the calculated equivalent CO2-concentration in ppm, based on the detected VOCs and hydrogen.
    
    # Register values
    SLEEP_MODE    = 0x00 # Very low power deep sleep
    IDLE_MODE     = 0x01 # Low power standby
    STANDARD_MODE = 0x02 # Sensors running

    def __init__(self, i2c_bus_num=1, sda_pin_num=26, scl_pin_num=27, i2c_addr=0x53):
        """Class for reading data from the ENS160 air quality sensor.
        
        Default pin numbers chosen because of their proximity to the 3V3 out pin. 

        :param int i2c_bus_num: (optional) The I2C bus number. On the pico, each bus can take certain pins. Default is bus 1 as this allows data & clock pins close to 3V3 supply.
        :param int sda_pin_num: (optional) The pin number for the I2C data line. Default 26.
        :param int scl_pin_num: (optional) The pin number for the I2C clock line. Default 27.
        :param int i2c_addr:    (optional) The I2C address of the sensor. Default 0x53.
        """

        # machine.I2C object has no attribute '__exit__' i.e. can't be used with context manager at sample time, so save now
        self.i2c = I2C(i2c_bus_num, sda=Pin(sda_pin_num), scl=Pin(scl_pin_num))

        # Save other args
        self.i2c_addr = i2c_addr

        # Start the sensor. On-device defaults of 25 C and 50% RH are used.
        self.i2c.writeto_mem(self.i2c_addr, ENS160.OPMODE_REG, bytearray([ENS160.STANDARD_MODE]))
        sleep(0.02)


    def get_AQI(self):
        """Get the air quality index. 

        Uses a scale set by the German central environmental agency UBA. See https://www.umweltbundesamt.de/en/calculation-base-air-quality-index

        :return Return value range: 1-5 (Corresponding to five levels of Excellent, Good, Moderate, Poor and Unhealthy respectively)
        """
        return self.i2c.readfrom_mem(self.i2c_addr, ENS160.DATA_AQI_REG, 1)[0]


    def get_TVOC_ppb(self):
        """Get TVOC concentration in parts per billion.

        :return Return value range: 0-65000, unit: ppb
        """
        buf = self.i2c.readfrom_mem(self.i2c_addr, ENS160.DATA_TVOC_REG, 2)
        return ((buf[1] << 8) | buf[0])


    def get_ECO2_ppm(self):
        """Get CO2 equivalent concentration calculated according to the detected data of VOCs and hydrogen.

        Five levels: Excellent(400 - 600), Good(600 - 800), Moderate(800 - 1000), Poor(1000 - 1500), Unhealthy(> 1500)

        :return Return value range: 400-65000, unit: ppm
        """
        buf = self.i2c.readfrom_mem(self.i2c_addr, ENS160.DATA_ECO2_REG, 2)
        return ((buf[1] << 8) | buf[0])


    def sample(self, rounding_dp=3):
        """Take all measurements from the ENS160 and return as dictionary.
        
        :param int rounding_dp: (optional) The number of decimal places to round float readings to. Default 3.
        """

        return {
            'AQI'  : self.get_AQI(),                          # No rounding as integer
            'TVOC' : round(self.get_TVOC_ppb(), rounding_dp),
            'CO2'  : round(self.get_ECO2_ppm(), rounding_dp),
            }
        # should CO2 be tagged eCO2 instead? Since the existing AQM solution using ENS160 on a flagship pi is expecting CO2, copy that.


# test
if __name__ == '__main__':
    print("testing ENS160")
    mysensor = ENS160()
    while True:
        sleep(1)
        print(mysensor.sample())
