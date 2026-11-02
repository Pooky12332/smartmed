import asyncio
import random
from datetime import datetime

from database import SessionLocal
import models

## This is another temp file just to provide a fake sensor to call
## We will get rid of this and replae it with the real sensors

def generate_reading():
    db = SessionLocal()

    try:
        sensor = db.query(models.Sensor).filter(
            models.Sensor.name == "Insulin Container Sensor"
        ).first()

        if not sensor:
            return

        latest = (
            db.query(models.Reading)
            .filter(models.Reading.sensor_id == sensor.id)
            .order_by(models.Reading.timestamp.desc())
            .first()
        )

        temperature = latest.temperature if latest else 5.0

        # Simulate small temperature changes
        temperature += random.uniform(-0.2, 0.2)

        # Keep simulated readings within plausible test limits
        temperature = max(0.0, min(15.0, temperature))

        reading = models.Reading(
            sensor_id=sensor.id,
            temperature=round(temperature, 2),
            timestamp=datetime.utcnow()
        )

        db.add(reading)
        db.commit()

    finally:
        db.close()


async def sensor_simulator():
    while True:
        generate_reading()
        await asyncio.sleep(10)

