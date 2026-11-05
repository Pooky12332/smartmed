import adafruit_dht
import board
import time

# Init device
temp_device = adafruit_dht.DHT11(board.D4)

print("[+] Reading data from 'temp_device'...")

def generate_reading():
    while True:
        try:
            # Grab the sensor values
            temp = temp_device.temperature

            if temp is None:
                return None

            print(f"Temp: {temp:.1f}")

            return temperature

        except RuntimeError as error:
            # The sensor usually throws errors before just reading again
            # So we just ignore it
            print(f"[!] Sensor reading error: {error}")
            return None

        except Exception as error:
            temp_device.exit()
            raise error

        time.sleep(2)