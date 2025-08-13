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
    samples_3axis = ADXL345().sample(1024)

    # And now some post-processing
        # Compress 3 axes into one. List of tuples of floats -> list of floats
    samples = [sqrt(x**2 + y**2 + z**2) for x,y,z in samples_3axis]

        # Remove average (assume no net displacement, only vibrating in place)
    mean_sample = sum(samples) / len(samples)
    samples = [s - mean_sample for s in samples]


        # Get RMS of all samples
    rms_sample = sqrt(sum(s**2 for s in samples) / len(samples))


        # Perform DFT
    fft = {}
    for f, m in enumerate(simpledft(samples)):
        fft[f*3.125] = m  # frequency: magnitude. Frequencies are scaled by sample rate / window size = 3200 / 1024 = 3.125


        # Identify peak frequency bin
    peak_magnitude = 0.2 # to avoid noise creating a high preakFrequency, offset this threshold from 0.
    peak_frequency = 0 # is it possible all magnitudes could be <= 0 ? Ensure pf is defined
    for frequency, magnitude in fft.items():
        if magnitude > peak_magnitude:
            peak_magnitude = magnitude
            peak_frequency = frequency


    # Publish to MQTT
    publish ({
        "id" : machine_name,
        'acceleration'  : rms_sample,
        'fft'           : [{"frequency": f, "magnitude": m} for f, m  in fft.items()], # reformatting of float:float dict to a list of short dicts to suit Telegraf
        'peakFrequency' : peak_frequency,
        },
        "vibration_monitoring/" + machine_name
        )
