# basic strings
wifi_ssid     = '***'
wifi_password = '***'
mqtt_broker   = '***'
machine_name  = 'pico_adxl345'

# Other imports
from math import sqrt
from core.mqtt import publish
from models.fft import simpledft

# Sensor and sampling definition
from sensors.adxl345 import ADXL345


def cycle():

    # Get a list of 3-axis accelerations
    samples_3axis = ADXL345().sample(1024) # Change this value with great care.
    # Not only does it need to be a power of 2, but this-1 needs to have a factor which is odd, hardcoded below.

    # And now some post-processing
        # Compress 3 axes into one. List of tuples of floats -> list of floats
    samples = [sqrt(x**2 + y**2 + z**2) for x,y,z in samples_3axis]

        # Remove average (assume no net displacement, only vibrating in place)
    mean_sample = sum(samples) / len(samples)
    samples = [s - mean_sample for s in samples]

        # Get RMS of all samples
    rms_sample = sqrt(sum(s**2 for s in samples) / len(samples))

        # Perform DFT
    magnitudes = simpledft(samples) # returns an array of half the length of the input
    
        # Downsample FFT result by summing magnitude across adjcent frequency bins
    magnitudes_downsampled = [magnitudes[0]] # keep dc result unchanged (should be approx 0 anyway as average removed above)
    for i in range(1, 74):                   # 511 non-0 original bins in groups of 7 --> 73 new bins + 0 Hz. i from 1 to 73 inclusive.
        j = i*7 - 6
        magnitudes_downsampled.append(sum(magnitudes[j:j+7])) # sum samples j to j+6 inclusive, last entry in slice is excluded

        # Identify peak frequency bin
    peak_magnitude = 0.2 # offset this threshold from 0 to avoid low-amplitude noise creating a high peak_frequency.
    peak_frequency = 0 # is it possible all magnitudes could be <= 0 ? Ensure pf is defined ahead of comparison below.
    for fbin, magnitude in enumerate(magnitudes): # note this is on raw FFT result, so another group of fbins might have a higher total. May be confusing in dashboard.
        if magnitude > peak_magnitude:
            peak_magnitude = magnitude
            peak_frequency = fbin*3.125 # Frequencies are scaled by sample rate / window size = 3200 / 1024 = 3.125


    # Publish to MQTT
    publish ({
        "id" : machine_name,
        'acceleration'  : rms_sample,
        'fft'           : [{"frequency": (fbin*7-3)*3.125 if fbin!=0 else 0, "magnitude": m} for fbin, m  in enumerate(magnitudes_downsampled)], # reformatting of float:float dict to a list of short dicts to suit Telegraf
        'peakFrequency' : peak_frequency,
        },
        "vibration_monitoring/" + machine_name
        )
