import network
import ubinascii

def get_mac() -> str:
    """Get the fixed MAC address of pico when connecting to WiFi."""
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True) # Must be active for wlan config to be loaded
    mac = ubinascii.hexlify(network.WLAN().config('mac'),':').decode()
    return mac

# test
if __name__ == '__main__':
    print("mac address is:", get_mac())