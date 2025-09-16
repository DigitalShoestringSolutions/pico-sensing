"""adcs.py
Many different ADCs in one file, each as a separate class

Support for negative readings is implemented, but only one channel number can be specified at read time
"""


from time import sleep


class GenericADC:

    def __init__(self,
                positive_full_scale_voltage:float,
                positive_full_scale_int:int,
                default_channel=None
                ):
        """Bass class to build other ADCs on top of. Minimises the functionality that each needs to implement.

        Usage in a child class might look like the below:
        ```
        class HardwareADC(GenericADC):

            def __init__(self, fullscale_voltage=3.3):         # Allow fullscale voltage to be changed by user, if that is physically possible
                # Initialise parent class
                super().__init__(1023, fullscale_voltage)      # eg for a 10 bit ADC that outputs integers from 0 to 1023

                # other hardware init behaviour here

            def read_int_raw(self, channel):
                set_channel(channel)                           # if ADC has a mux and needs to be told in advance what channel to sample from
                extracted_int = "clock bits out of ADC and assemble into integer"
                return extracted_int
        ```
        To use:
        ```
        myadc = HardwareADC()
        voltage = myadc.read_voltage(2) # sample analogue voltage at channel 2
        ```

        The default_channel argument, not used in the example above,
        allows a channel number to be saved at creation time, rather than passed on every `read_`.
        The is an optional kwarg, hence it must be supplied to GenericADC last.
        However, it is recommended to make this the first arg of a child class so it can be the only one:

        ```
        class HardwareADC(GenericADC):
            def __init__(self, default_channel=None, fullscale_voltage=3.3):
                # Initialise parent class
                super().__init__(1023, fullscale_voltage, default_channel)
        ```
        This allows very neat usage such as
        ```
        with HardwareADC(4) as myadcinput:
            voltage = myadcinpupt.read_voltage()
        
        ```

        :param float positive_full_scale_voltage: Reference voltage. Much more plausible this will be changed by user than the bit depth, hence first position.
        :param int positive_full_scale_int:     The largest positive signal that can be output. 2^bit depth - 1 for single-ended ADCs, eg 1023, 4095, 65535
        :param default_channel:             Option to specify channel number at adc class instance creation time, rather than at sample time.
        """

        # Save args
        self.positive_full_scale_voltage = positive_full_scale_voltage
        self.positive_full_scale_int = positive_full_scale_int
        self.default_channel = default_channel


    # Convenience pointer for most common usage
    def __call__(self, channel=None) -> float:
        return self.read_voltage(channel)

    def sample(self, channel=None, n_samples=10, sample_interval=0.01) -> float: # average from 10 samples each 10ms apart
        """Median average of a burst of samples of the absolute voltage. Median average type is chosen over mean as it better resists anomalous data.

        :param channel:         The channel to sample from. If omitted, default_channel will be used.
        :param int n_samples:       The number of readings to take in this burst to find the median from
        :param float sample_interval: The time in seconds to sleep between taking each reading
        """
        # Collect samples
        voltages = []
        for _ in range(n_samples):
            voltages.append(self.read_voltage(channel))
            sleep(sample_interval)

        # Return median sample
        voltages.sort()
        mid_index = len(voltages) //2
        return (voltages[mid_index] + voltages[~mid_index]) / 2 # ~ operator makes inverts the sign of the following number and then subtracts one


    # Calculation functions 
    def read_voltage(self, channel=None) -> float:
        """Read the absolute voltage at an input to a single-ended ADC.
        
        :param channel: (optional) The channel to read from. If not specified, `default_channel` will be used.
        """
        return self.read_fraction(channel) * self.positive_full_scale_voltage

    def read_fraction(self, channel=None) -> float:
        """Returns a float from 0 (or -1 if the ADC supports differential measurements) to 1.

        Useful for sensors where the output relative to Vcc is important, but the absolute voltage is not (eg potentiometers)

        :param channel: (optional) The channel to read from. If not specified, `default_channel` will be used.
        """
        return self.read_int_signed(channel) / self.positive_full_scale_int

    def read_int_signed(self, channel=None) -> int:
        """Reads bits from the ADC that may be using 2's complement and returns a signed integer.

        Permits using a default channel number saved in the class instance.
        As the class instance is not available when the default value of the kwarg is evaluated (can't do channel=self.default_channel),
            something simple (like Nonetype) must be used figuratively.

        :param channel: (optional) The channel to read from. If not specified, `default_channel` will be used.
        """
        if channel is None:
            if self.default_channel is None:                   # If channel number is not specified to this function, try using class variable
                raise TypeError("Channel number must be supplied to `read_` functions or provided when initialising class instance")
            channel = self.default_channel

        int_signed = self.read_int_raw(channel)
        if int_signed > self.positive_full_scale_int:          # If digital output code is above positive full scale (i.e. using 2's complement),
            int_signed -= (2*self.positive_full_scale_int + 2) #    undo 2's complement
        return int_signed

    # Hardware interface placeholder
    def read_int_raw(self, channel):
        raise NotImplementedError("read_int_raw(channel) not overwritten by ADC class!")


class pico_adc(GenericADC):
    """Convenience wrapper for using the Pico's internal ADCs."""

    def __init__(self, default_channel=None):
        """Reference voltage and bit depth cannot be changed for the pico.
        
        :param int default_channel: (optional) The channel to sample from if not specified when calling `read_` functions.
        """
        super().__init__(3.3, 65535, default_channel)
        import machine
        self._adc = machine.ADC # save pointer to class constructor

    def read_int_raw(self, channel=None):
        """Override: read from the Pico's ADC as an unsigned 16bit integer.
        
        :param int channel: (optional) The channel to read from. If not specified, `default_channel` will be used.
        """
        return self._adc(channel).read_u16()


class ads1115(GenericADC):
    """ADS1115 16 bit I2C ADC https://www.ti.com/lit/ds/symlink/ads1115.pdf"""

    def __init__(self, sda_pin_num, scl_pin_num, i2c_bus_num, i2c_addr=0x48, default_channel=None):
        """Single-ended use with range 6.144V only, but output code will not exceed supply voltage.

        :param int sda_pin_num: I2C Serial DAta pin number (GP numbering)
        :param int scl_pin_num: I2C Serial CLock pin number (GP numbering)
        :param int i2c_bus_num: I2C bus associated with these SDA and SCL pins. Must be 0 or 1.
        :param int i2c_addr: Device I2C address set by ADDR pin. Must be in range 72-75.
        :param int default_channel: (optional) The channel to sample from if not specified when calling `read_` functions.
        """

        from machine import Pin, I2C
        self.i2c_addr = i2c_addr
        super().__init__(6.144, 32767, default_channel) # always use max input range of 6.144V for simple compatibility, but set on hardware only at sample time.
        self.i2c = I2C(i2c_bus_num, sda=Pin(sda_pin_num), scl=Pin(scl_pin_num))

    def read_int_raw(self, channel=None):
        """Override: Read from the external ADS115 I2C ADC as a 16bit integer using two's complement.
        
        :param int channel: (optional) The channel to read from. If not specified, `default_channel` will be used.
        """

        # resend config before every sample rather than at init time, in case of hotplugging or corruption
        # prep config for single-ended conversion, FSR=6.144V, continous, 128SPS, comparator off. See datasheet p28.
        config = [(0b01 << 6) | (channel << 4) | (0b000 << 1) | (0b0), ( (0b100 << 5) | (0b00011) )]
        # write 2 config bytes to config word register at address 0x01
        self.i2c.writeto_mem(self.i2c_addr, 0x01, bytearray(config))

        # Wait while sample is taken. 1 cycle at 128SPS = 7.82ms, 15ms observed to not always be enough.
        sleep(0.020)

        # Read 2 bytes from register 0
        adc_bytes = self.i2c.readfrom_mem(self.i2c_addr, 0x00, 2)
        adc_int = (adc_bytes[0] << 8) | adc_bytes[1]
        return adc_int

# test
if __name__ == '__main__':
    print("testing ADCs")
    #myadc = pico_adc()
    #channels = [26, 27, 28]
    myadc = ads1115(26, 27, 1)
    channels = [0, 1, 2, 3]
    while True:
        for channel in channels:
            print(myadc.sample(channel))
            #print(myadc.read_voltage(channel))
            #print(myadc.read_int_raw(channel))
        print()
        sleep(1)
