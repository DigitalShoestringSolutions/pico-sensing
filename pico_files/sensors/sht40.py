from machine import I2C, Pin
from time import sleep


class SHT40:

    _COMMAND_MEASURE_TRH = 0xFD # measure T & RH with high precision & repeatability

    def __init__(self, i2cbus_num=0, sda_pin_num=None, scl_pin_num=None, i2caddr=0x44):
        """Class for reading data over I2C from the SHT40 temperature and relative humidity sensor.

        Datasheet: https://sensirion.com/media/documents/33FD6951/6555C40E/Sensirion_Datasheet_SHT4x.pdf
        
        :param int i2c_bus_num: The I2C bus number. Default 0.
        :param int sda_pin_num: The pin number for the I2C data line. Default is suitable for specified bus if using the Grove breakout board for pico.
        :param int scl_pin_num: The pin number for the I2C clock line. Default is suitable for specified bus if using the Grove breakout board for pico.
        :param int i2c_addr:    The I2C address of the SHT40. Default 0x44.
        """

        # Default pin numbers depend on bus! This allows easy use on Grove breakout boards by supplying only the bus number.
        # Pin numbers are different on Gravity boards. I expect them to be less commonly used with the SHT40; all 3 numbers will need to be specified.
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
        self.i2c = I2C(i2cbus_num, sda=Pin(sda_pin_num), scl=Pin(scl_pin_num))

        # Save other args
        self.i2caddr = i2caddr


    def sample(self, rounding_dp=3, limit_rh=False):
        """Measure both temperature in celsius and relative humidity % and return in a dictionary.
        
        :param int rounding_dp: The number of decimal places to round the readings to. Default 3.
        :param bool limit_rh:   (optional) Restrict non-physical humidity readings (<0%, >100%) to real range. Default `False`
        """

        #readbytes = i2c.readfrom_mem(addr, reg, length) # cannot apply necessary delay between sending command and clocking readings out without stop condition on bus inbetween operations
        # Hence write and read must be done separately
        self.i2c.writeto(self.i2caddr, bytearray([self._COMMAND_MEASURE_TRH]))
        sleep(0.01)                                    # non-zero sleep is critical, but it can be as small as 8.3ms. See table 5 of https://sensirion.com/media/documents/33FD6951/6555C40E/Sensirion_Datasheet_SHT4x.pdf
        readbytes = self.i2c.readfrom(self.i2caddr, 6) # read 6 bytes. All SHT40 hardware methods have responses of length 6 bytes.

        # Post-process bytes into ints                               
        readints = [int(byte) for byte in readbytes]
        raw_temperature = (readints[0] << 8) | (readints[1])
        raw_humidity = (readints[3] << 8) | (readints[4])

        # Package and return readings as dictionary
        data = dict()
        data['temperature'] = round(self._calculate_temperature(raw_temperature), rounding_dp)          # degC
        data['humidity'] = round(self._calculate_relativehumidity(raw_humidity, limit_rh), rounding_dp) # %
        return data


    def _calculate_temperature(self, raw_temperature:int) -> float:
        """Calculate temperature in celsius from raw integer read from adc.
        
        :param int raw_temperature: Reading from the 
        """

        T_degC = -45 + (175*raw_temperature/65535)
        return T_degC


    def _calculate_relativehumidity(self, raw_humidity:int, limit=False) -> float:
        """Calculate relative humidity % from raw integer read from adc.
        
        :param int raw_humidity: T
        :param bool limit:       (optional) Restrict non-physical humidity readings (<0%, >100%) to real range. Default `False`.
        """

        RH = -6 + (125*raw_humidity/65535)

        if limit:
            if RH > 100:
                RH = 100
            elif RH < 0:
                RH = 0

        return RH


# test
if __name__ == '__main__':
    print("testing SHT40")
    mysht = SHT40()
    print(mysht.i2c.scan())
    while True:
        sleep(1)
        print(mysht.sample())



# ###
# in case you later want to play with CRC or heater...
#
# import time
# import struct
# from micropython import const
# 
# _RESET = const(0x94)
# 
# HEATER200mW = const(0)
# HEATER110mW = const(1)
# HEATER20mW = const(2)
#
# heat_time_values = (const(0), const(1))
# 
# wat_config = {
#     HEATER200mW: (0x39, 0x32),
#     HEATER110mW: (0x2F, 0x24),
#     HEATER20mW: (0x1E, 0x15),
# }
# 
# 
# class SHT4X:
#     """Driver for the SHT4X Sensor connected over I2C."""
# 
#     def __init__(...)
#         self._heater_power = HEATER20mW
#         self._heat_time = TEMP_0_1
# 
 
# 
#     @property
#     def measurements(self) -> Tuple[float, float]:
#         """both `temperature` and `relative_humidity`, read simultaneously
#         If you use t the heater function, sensor will be not give a response
#         back. Waiting time is added to the logic to account for this situation
#         """
# 
#         self._i2c.writeto(self._address, bytes([self._command]), False)
#         if self._command in (0x39, 0x2F, 0x1E):
#             time.sleep(1.2)
#         elif self._command in (0x32, 0x24, 0x15):
#             time.sleep(0.2)
#         time.sleep(0.2)
#         self._i2c.readfrom_into(self._address, self._data)
# 
#         temperature, temp_crc, humidity, humidity_crc = struct.unpack_from(
#             ">HBHB", self._data
#         )
# 
#         if temp_crc != self._crc(
#             memoryview(self._data[0:2])
#         ) or humidity_crc != self._crc(memoryview(self._data[3:5])):
#             raise RuntimeError("Invalid CRC calculated")
#
#         ... 
# 
#     @staticmethod
#     def _crc(buffer) -> int:
#         """verify the crc8 checksum"""
#         crc = 0xFF
#         for byte in buffer:
#             crc ^= byte
#             for _ in range(8):
#                 if crc & 0x80:
#                     crc = (crc << 1) ^ 0x31
#                 else:
#                     crc = crc << 1
#         return crc & 0xFF
# 
#     @property
#     def heater_power(self) -> str:
#         """
#         Sensor heater power
#         The sensor has a heater. Three heating powers and two heating
#         durations are selectable.
#         The sensor executes the following procedure:
#         1. The heater is enabled, and the timer starts its count-down.
#         2. Measure is taken after time is up
#         3. After the measurement is finished the heater is turned off.
#         4. Temperature and humidity values are now available for readout.
#         The maximum on-time of the heater commands is one second in order
#         to prevent overheating
#         
#         +-------------------------------+---------------+
#         | Mode                          | Value         |
#         +===============================+===============+
#         | :py:const:`sht4x.HEATER200mW` | :py:const:`0` |
#         +-------------------------------+---------------+
#         | :py:const:`sht4x.HEATER110mW` | :py:const:`1` |
#         +-------------------------------+---------------+
#         | :py:const:`sht4x.HEATER20mW`  | :py:const:`2` |
#         +-------------------------------+---------------+
#         
#         """
#         values = ("HEATER200mW", "HEATER110mW", "HEATER20mW")
#         return values[self._heater_power]
# 
#     @heater_power.setter
#     def heater_power(self, value: int) -> None:
#         if value not in heater_power_values:
#             raise ValueError("Value must be a valid heater power setting")
#         self._heater_power = value
#         self._command = wat_config[value][self._heat_time]
# 
#     @property
#     def heat_time(self) -> str:
#         """
#         Sensor heat_time
#         The sensor has a heater. Three heating powers and two heating
#         durations are selectable.
#         The sensor executes the following procedure:
#         1. The heater is enabled, and the timer starts its count-down.
#         2. Measure is taken after time is up
#         3. After the measurement is finished the heater is turned off.
#         4. Temperature and humidity values are now available for readout.
#         The maximum on-time of the heater commands is one second in order
#         to prevent overheating
# 
#         +----------------------------+---------------+
#         | Mode                       | Value         |
#         +============================+===============+
#         | :py:const:`sht4x.TEMP_1`   | :py:const:`0` |
#         +----------------------------+---------------+
#         | :py:const:`sht4x.TEMP_0_1` | :py:const:`1` |
#         +----------------------------+---------------+
#         """
#         values = ("TEMP_1", "TEMP_0_1")
#         return values[self._heat_time]
# 
#     @heat_time.setter
#     def heat_time(self, value: int) -> None:
#         if value not in heat_time_values:
#             raise ValueError("Value must be a valid heat_time setting")
#         self._heat_time = value
#         self._command = wat_config[self._heater_power][value]
# 
#     def reset(self):
#         """
#         Reset the sensor
#         """
#         self._i2c.writeto(self._address, bytes([_RESET]), False)
#         time.sleep(0.1)



