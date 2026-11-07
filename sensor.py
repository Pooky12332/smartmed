# real_sensor.py
import threading
import time
from datetime import datetime

import adafruit_dht
import board

from database import SessionLocal
import models
from temperature_limits import check_temperature_limits


PIN = board.D4
MIN_INTERVAL = 2.0  # DHT11 datasheet minimum

device = None
lock = threading.Lock()      # DHT11 isn't thread-safe
last_read_at = 0.0


def _get_device():
    global device

    if device is None:
        device = adafruit_dht.DHT11(PIN)
    return device


def read_temperature():
    ## Blocking read. Returns temperature (°C) or None (throttled, or read error).
    global last_read_at

    with lock:
        now = time.monotonic()

        if now - last_read_at < MIN_INTERVAL:
            return None

        last_read_at = now

        try:
            return _get_device().temperature

        except RuntimeError as e:
            print(f"[!] DHT11 read error: {e}")
            return None

        except Exception as e:
            print(f"[!] DHT11 fatal error, resetting device: {e}")
            global device

            try:
                device.exit()
            except Exception:
                pass

            device = None
            return None


def read_and_save():
    ## Read the live sensor and persist a Reading. Returns the Reading or None.
    temp = read_temperature()

    if temp is None:
        return None

    db = SessionLocal()

    ## Save the readings to the database for reading
    try:
        sensor = db.query(models.Sensor).order_by(models.Sensor.id.asc()).first()
        
        if not sensor:
            print("[!] No Sensor row in DB; cannot store reading")
            return None

        ## Set up the reading for the database
        reading = models.Reading(
            sensor_id=sensor.id,
            temperature=temp,
            timestamp=datetime.utcnow(),
        )

        ## Actually sending the data to the database
        check_temperature_limits(reading)
        db.add(reading)
        db.commit()
        db.refresh(reading)

        return reading

    except Exception as e:
        db.rollback()
        print(f"[!] Failed to save reading: {e}")
        return None

    finally:
        db.close()


def shutdown():
    ## Release the GPIO pin. Call from app shutdown.
    global device

    with lock:
        if device is not None:
            try:
                device.exit()

            except Exception:
                pass

            device = None