
import models

## Safe storage range for insulin in °C
MIN_TEMPERATURE = 2.0
MAX_TEMPERATURE = 8.0


# Records an alert if a reading is outside the safe range.
# Any old alerts are cleared first.
def check_temperature_limits(reading: models.Reading):

    # Clear existing alerts
    reading.high_temperature_alerts.clear()
    reading.low_temperature_alerts.clear()

    # Check for high temperature
    if reading.temperature > MAX_TEMPERATURE:

        reading.high_temperature_alerts.append(
            models.HighTemperatureAlert(
                sensor_id=reading.sensor_id,
                temperature=reading.temperature,
                temperature_limit=MAX_TEMPERATURE,
                amount_over=round(
                    reading.temperature - MAX_TEMPERATURE, 2
                ),
                timestamp=reading.timestamp
            )
        )

    # Check for low temperature
    elif reading.temperature < MIN_TEMPERATURE:

        reading.low_temperature_alerts.append(
            models.LowTemperatureAlert(
                sensor_id=reading.sensor_id,
                temperature=reading.temperature,
                temperature_limit=MIN_TEMPERATURE,
                amount_under=round(
                    MIN_TEMPERATURE - reading.temperature, 2
                ),
                timestamp=reading.timestamp
            )
        )
