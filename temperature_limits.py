import models

## Safe storage range for insulin in °C
MIN_TEMPERATURE = 2.0
MAX_TEMPERATURE = 8.0


# Records an alert if a reading is outside the safe range.
# Any old alert for the reading is cleared first, so this can be run again after a reading is updated.
def check_temperature_limits(reading: models.Reading):
    reading.high_temperature_alerts.clear()
    reading.low_temperature_alerts.clear()

    if reading.temperature > MAX_TEMPERATURE:
        reading.high_temperature_alerts.append(models.HighTemperatureAlert(
            sensor_id = reading.sensor_id,
            temperature = reading.temperature,
            temperature_limit = MAX_TEMPERATURE,
            amount_over = round(reading.temperature - MAX_TEMPERATURE, 2),
            timestamp = reading.timestamp
        ))

    elif reading.temperature < MIN_TEMPERATURE:
        reading.low_temperature_alerts.append(models.LowTemperatureAlert(
            sensor_id = reading.sensor_id,
            temperature = reading.temperature,
            temperature_limit = MIN_TEMPERATURE,
            amount_under = round(MIN_TEMPERATURE - reading.temperature, 2),
            timestamp = reading.timestamp
        ))
