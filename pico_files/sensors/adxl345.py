# adxl345.py
# datasheet: https://www.analog.com/media/en/technical-documentation/data-sheets/adxl345.pdf
# i2c only

# Standard library imports
from machine import I2C, Pin
import time


class ADXL345:

    g = 9.80665 # standard gravity
    gain = g/256 # multiply readings (in full res mode) by this to get m/s2.
    
    def __init__(self, device_i2c_addr=0x53, i2cbus_num=0, sda_pin_num=8,scl_pin_num=9):
        
        self.device_i2c_addr = device_i2c_addr
        self.i2c = I2C(i2cbus_num, sda=Pin(sda_pin_num), scl=Pin(scl_pin_num), freq=400000) # max 400 kHz datasheet page 17.
        
        self.prepare_sensor()


    def prepare_sensor(self):
        
        # Write measure bit to ensure sensor is not sleeping
        self.i2c.writeto_mem(self.device_i2c_addr, 0x2D, bytearray([0x08]))
        #print("power control set to", self.i2c.readfrom_mem(self.device_i2c_addr, 0x2D, 1)[0])

        # Write bandwidth - according to datasheet,
        # "Due to communication speed limitations, the maximum output data rate when using 400 kHz I2C is 800 Hz"
        # "Operation at an output data rate above the recommended maximum may result in undesirable effect
        # on the acceleration data, including missing samples or additional noise" 
        # However in my testing unique samples can be read at the full 3200 Hz. Hence set ODR to max (3200 Hz)
        self.i2c.writeto_mem(self.device_i2c_addr, 0x2C, bytearray([0x0F])) # 3200 Hz
        #self.i2c.writeto_mem(self.device_i2c_addr, 0x2C, bytearray([0x0D])) # 800 Hz
        #print("Output data rate set to", self.i2c.readfrom_mem(self.device_i2c_addr, 0x2C, 1)[0])
        
        # Write data format. Full res, right justified and 16g range (no motive to go smaller? No ENOB improvements)
        self.i2c.writeto_mem(self.device_i2c_addr, 0x31, bytearray([0x0B]))
        #print("data format set to", self.i2c.readfrom_mem(self.device_i2c_addr, 0x31, 1)[0])

        
    def get_raw_samples(self, nsamples:int=1) -> list:
        """Gather raw data from the accelerometer as fast as the sensor can produce it.
        Broken out into a separate function from sample() to ease measurement of read rate performance

        :param nsamples: number of samples to take

        Returns: a list of bytearrays
        """

        raw_samples = []
        for _ in range(nsamples):
            raw_samples.append(self.i2c.readfrom_mem(self.device_i2c_addr, 0x32, 6)) # read 6 bytes starting at mem 0x32
            # Unrestricted this loop runs in 285us i.e. 3.5 kHz. That's faster than the sensor can measure (3.2 kHz)!
            time.sleep_us(24) # slow down to match sensor speed. Subtract 3 for sleep function overhead. 
            # Do we want to be sampling just over or just under the sensor's rate? No PLL, no great oversampling available.
    
        return raw_samples
    

    def sample(self, nsamples:int=1) -> list: # at risk of becoming the odd one out, other sensor.sample() methods return a dict
        """Read a burst of samples from the accelerometer with minimum spacing (nom 800Hz)
        
        :param nsamples: number of samples to take

        Returns: a list of (x,y,z) tuples
        """
        
        self.prepare_sensor() # re-setup every time

        raw_samples = self.get_raw_samples(nsamples)

        # Pre-process
        samples = []
        for raw_sample in raw_samples:
            sample_ints = [int(byte) for byte in raw_sample] # debode bytes

            int_x = sample_ints[0] | (sample_ints[1] << 8) 
            if int_x > 0x7FFF: # if > positive full scale int i.e. 2's complement negative
                int_x -= (2*0x7FFF + 2) #    undo 2's complement. Note all bits of the byte participate.
            accu_x = int_x*self.gain

            int_y = sample_ints[2] | (sample_ints[3] << 8)
            if int_y > 0x7FFF:
                int_y -= (2*0x7FFF + 2) # bracket could be pre-computed for speed but this is clearer
            accu_y = int_y*self.gain

            int_z = sample_ints[4] | (sample_ints[5] << 8)
            if int_z > 0x7FFF:
                int_z -= (2*0x7FFF + 2)
            accu_z = int_z*self.gain

            samples.append((accu_x, accu_y, accu_z))

        return samples


    def speedtest(self, max_samples:int=4096): # memory allocation sometimes fails above 4096 samples
        """Test raw sampling rate"""

        sampling_start_time_1 = time.ticks_us()
        self.get_raw_samples(1)
        sampling_end_time_1 = time.ticks_us()
        sampling_time_1 = sampling_end_time_1 - sampling_start_time_1
        print(f"gathering 1 sample took {sampling_time_1} us")

        sampling_start_time_2 = time.ticks_us()
        self.get_raw_samples(max_samples)
        sampling_end_time_2 = time.ticks_us()
        sampling_time_2 = sampling_end_time_2 - sampling_start_time_2
        print(f"gathering {max_samples} samples took {sampling_time_2} us")

        print(f"gathering an additional {max_samples - 1} samples took an additional {sampling_time_2 - sampling_time_1} us")
        print(f"average time per additional sample was {(sampling_time_2 - sampling_time_1) / (max_samples - 1)} us")


if __name__ == '__main__':
    myadxl = ADXL345()
    #myadxl.speedtest()

    while True:
        for axis in myadxl.sample()[0]:
            print("{:6.2f}".format(axis), end=' ')
        print()
        time.sleep(0.1)
