# pico-sensing
Minimal sensing system using the Raspberry Pi Pico

# Usage

- git clone (or download & extract zip of) this repository onto your computer 

- Install a program suitable for both transfering files onto the pico and viewing its serial output (eg [Thonny](https://thonny.org/))

- Put everything inside the `pico_files` folder on the pico

- Edit `user_settings.py` to suit your application. Read more below or examples of what can be done there can be found in `example_user_settings`.


# About

### `user_settings.py`
Everything that needs to be done to configure this code is done in one file: `user_settings.py`. An underlying set of default settings can be found in `core.default_settings.py`.  
Typically when a module loads the settings, it will first import * (all objects) from `core.default_settings`, then also import * from `user_settings`.  
This allows for a merged namespace while keeping `user_settings` short.  

### Timing, `cycle()` and `cycle_interval`
The only assumption imposed by using this repository is that the pico is to undertake a repetitive task at fixed intervals.  
The repetitive action is placed within the `cycle()` function in `user_settings.py`.  
Between each `cycle()`, the pico sleeps for `cycle_interval` seconds. This has a default value of 1 unless a different value is assigned in `user_settings.py`.  
Executing `cycle()` may take time. The sleep between cycles is shortened to compensate.

### WiFi & MQTT
To connect to wifi, define the strings `wifi_ssid` and `wifi_password` in `user_settings.py`. If WiFi is not required in your application, remove or comment out these lines.

MQTT messages can be sent using the `core.mqtt.publish()` function. The topic to publish to and the broker address can either be supplied as arguments to `publish()`, or the global variables `mqtt_topic` and `mqtt_broker` can be defined as global strings in `user_settings.py`.

### LED
The Raspberry Pi Pico has an onboard LED. It is here used to visualise the status of code execution.  
While connecting to WiFi, the LED is mostly off and briefly blinks on (50ms) after each attempt to connect.  
During normal operation (after connecting to WiFi if required), the LED is mostly on, briefly blinking off. During the time the LED is off, the `cycle()` function is taking place. When the LED is on, the device is sleeping between cycles.  
The LED should never be continously on for longer than `cycle_interval`.

### Error handling
A basic error handling system is implemented. Exceptions are contained to each cycle.   
If an error occurs during `cycle()`, a 3 second pause is implemented before the LED is turned back on. This gives a visual indication that an error occured but was contained. An error counter is also incremented. This error counter is reset to 0 after a cycle runs without error.  

If consecutive attempts to run `cycle()` result in errors, eventually the error counter will reach a limit after which the device will hard reboot. This is implemented to recover from certain situations where a reboot may help (e.g. lost WiFi connection). This limit can be changed by setting the variable `consecutive_error_count_limit` in `user_settings.py`. The default value is 10 (as seen in `core.default_settings.py`). A 5 second pause occurs before rebooting, both to indicate via the LED that this has happened and to allow time for the message to be read in the terminal.
A different limit can be defined for WiFi connection attempts, using the variable `wifi_error_count_limit` (default 20) in the same way.

### Log files
Log files are kept on device as plain text files.  
Each line begins with a timestamp and the current size of the log file.  
Log file size is limited. In total log files cannot take up more than 400MB (20% of Pico's flash). A minimal rotation system is implemented that deletes the oldest logs while ensuring recent logs are always available.  
There are only two log files. These are called `log.txt` and `log_old.txt`. Rotation is prompted only by file size, not time.  
There are no logger class instances nor logging levels, for simplicity. To change what is logged, comment out some log commands.  

Usually logging will not need to be considered in `user_settings.py`.  
Everything that appears in the serial terminal, including MQTT message payloads passed to `core.mqtt.publish()`, are logged by default (via `core.logging.log()` which prints to terminal by default).  


# Notes for developers

### Adding new sensors
To add support for a new sensor (family), create a file for it in `sensors.py`.  
Sensors should have a class with a `sample()` method that returns a dictionary containing their readings.  

### ADCs
Until the file gets too big to maintain, all adc interfaces go in `sensors.adcs.py`. Each ADC class should be a child of `GenericADC` and provide a `read_int_raw()` function. See more in docstrings in `sensors.adcs.py`.

### Wrapping I2C 
Despite some appeals, I have avoided creating a wrapper for i2c so far. Although it would reduce some code duplication (default sda/scl pin numbers perhaps), this would make the sensor files less standalone.
