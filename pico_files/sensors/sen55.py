from machine import I2C, Pin
from time import sleep

class SEN55:
    
    def __init__(self, i2c_bus_num=0, sda_pin_num=None, scl_pin_num=None, i2c_addr=0x69):
        """Class for reading data over I2C from the SEN55 air sensor.
        
        Datasheet: https://sensirion.com/media/documents/6791EFA0/62A1F68F/Sensirion_Datasheet_Environmental_Node_SEN5x.pdf
        As the sensor takes a few seconds to start up, a higher sample rate can be achieved by keeping this class instance.
        
        :param int i2c_bus_num: The I2C bus number. Default 0.
        :param int sda_pin_num: The pin number for the I2C data line. Default is suitable for specified bus if using the Grove breakout board for pico.
        :param int scl_pin_num: The pin number for the I2C clock line. Default is suitable for specified bus if using the Grove breakout board for pico.
        :param int i2c_addr:    The I2C address of the SEN55. Default 0x69.
        """

        # Default pin numbers depend on bus! This allows easy use on Grove breakout boards by supplying only the bus number.
        # Pin numbers are different on Gravity boards. I expect them to be less commonly used with the SEN55; all 3 numbers will need to be specified.
        if sda_pin_num is None:
            if i2c_bus_num == 0:
                sda_pin_num = 8
            elif i2c_bus_num == 1:
                sda_pin_num = 6
        if scl_pin_num is None:
            if i2c_bus_num == 0:
                scl_pin_num = 9
            elif i2c_bus_num == 1:
                scl_pin_num = 7

        # machine.I2C object has no attribute '__exit__' i.e. can't be used with context manager at sample time, so save now
        self.i2c = I2C(i2c_bus_num, sda=Pin(sda_pin_num), scl=Pin(scl_pin_num), freq=10000)
        # SEN55 Max. speed: standard mode, 100 kbit/s according to datasheet. But underclock for significant reliability improvement.

        # Save other args
        self.i2c_addr = i2c_addr

        # wait 1 s for sensor start up (> 1000 ms according to datasheet)
        sleep(1)

        # send init commands
        self.i2c.writeto(self.i2c_addr, bytearray([0x00, 0x21]))

        # wait for first measurement to be finished.
        sleep(2)


    @property
    def data_ready(self) -> int:
        """Is the Data Ready flag currently set?"""
        self.i2c.writeto(self.i2c_addr, bytearray([0x02, 0x02]))
        readbytes = self.i2c.readfrom(self.i2c_addr, 3) # 1 empty byte + 1 containing target bit + 1 CRC
        drdy = readbytes[1]
        return drdy # int 0 or 1


    def sample(self):
        """Take all measurements from the SEN55 and return as dictionary."""

        if not self.data_ready:
            self.__init__(self.DEVICE_BUS, self.DEVICE_ADDR)
            raise ValueError("SEN5x data is not ready")      # wait and retry? Recursion limit needed.

        # Request data
        self.i2c.writeto(self.i2c_addr, bytearray([0x03, 0xC4]))

        # wait 10 ms for data ready
        sleep(0.01)

        # read 24 bytes; each three bytes in as a sequence of MSB, LSB, CRC. CRC not used.
        # Reading from this reg resets the Data-Ready Flag
        readbytes = self.i2c.readfrom(self.i2c_addr, 24)

        # merge particulate bytes into integers
        pm1p0 = (readbytes[0] << 8 | readbytes[1])/10
        pm2p5 = (readbytes[3] << 8 | readbytes[4])/10
        pm4p0 = (readbytes[6] << 8 | readbytes[7])/10
        pm10p0 = (readbytes[9] << 8 | readbytes[10])/10

        # Merge Compensated Ambient Humidity [%RH] bytes into integer
        humidity = readbytes[12] << 8 | readbytes[13]
        # calculate relative humidity according to datasheet
        humidity /= 100

        # merge Compensated Ambient Temperature [°C] bytes into integers
        temperature = readbytes[15] << 8 | readbytes[16]
        # calculate temperature  according to datasheet
        temperature /= 200

        # Decode VOC and NOX index points
        voc = (readbytes[18] << 8 | readbytes[19]) / 10
        nox = (readbytes[21] << 8 | readbytes[22]) / 10

        return {
            "mc_1p0"     : pm1p0,
            "mc_2p5"     : pm2p5,
            "mc_4p0"     : pm4p0,
            "mc_10p0"    : pm10p0,
            "voc_index"  : voc,
            "nox_index"  : nox,
            "ambient_t"  : temperature,
            "ambient_rh" : humidity,
            }

# test
if __name__ == '__main__':
    print("testing MYSENSOR")
    mysensor = SEN55()
    print(mysensor.i2c.scan())
    while True:
        sleep(1)
        print(mysensor.sample())