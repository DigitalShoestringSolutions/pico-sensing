# Standard library imports
from time import sleep


class CT:
    
    def __init__(self, amps_per_volt, zero_current_voltage=0):
        """Model for current sensors (ac or dc) with an analogue voltage output.
        
        :param float amps_per_volt:        Gain: the amps flowing per 1 volt change from zero_current_voltage.
        :param float zero_current_voltage: (optional) Offset: the input voltage to the ADC when no current is flowing. Default 0.
        """

        # Save args
        self.amps_per_volt = amps_per_volt
        self.zero_current_voltage = zero_current_voltage


    def __call__(self, voltage, rounding_dp=3):
        """Given an input voltage, calculate the current flowing through the sensor. Returns a dictionary containing `current`.
        
        :param float voltage:   The input voltage to calculate the current from.
        :param int rounding_dp: (optional) The number of decimal places to round the current to. Default 3.
        """

        # Apply offset and gain
        current = self.amps_per_volt * (voltage - self.zero_current_voltage)

        # Package and return readings as dictionary
        data = dict()
        data['current'] = round(current, rounding_dp)
        return data


# test
if __name__ == '__main__':
    print("testing YHDC_CT for 3 phases")
    from sensors.adc import pico_adc
    adc = pico_adc()
    pins = 26, 27, 28
    myCT = CT(20)
    while True:
        for pin in pins:
            print(myCT(adc(pin)), end=' ')
        print()
        sleep(1)
