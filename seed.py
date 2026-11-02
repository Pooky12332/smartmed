import random
from datetime import datetime, timedelta
from database import SessionLocal, engine
import models

## This is a temp file to populate the database with some data for testing reasons.
## You can run this again to reset and repopulate the database

## uv run seed.py

models.Base.metadata.create_all(bind=engine)

def seed_data():
    db = SessionLocal()

    try:
        sensor = db.query(models.Sensor).filter(
            models.Sensor.name == "Insulin Container Sensor"
        ).first()

        if not sensor:
            sensor = models.Sensor(
                name="Insulin Container Sensor",
                location="Inside insulin container"
            )
            db.add(sensor)
            db.commit()
            db.refresh(sensor)

        if db.query(models.Reading).filter(
            models.Reading.sensor_id == sensor.id
        ).first():
            print("Readings already exist.")
            return

        print("Generating fake insulin temperature readings...")

        temperature = 5.0
        base_time = datetime.utcnow()

        for i in range(50):
            temperature += random.uniform(-0.15, 0.15)

            temperature = max(2.0, min(8.0, temperature))

            reading = models.Reading(
                sensor_id=sensor.id,
                temperature=round(temperature, 2),
                timestamp=base_time - timedelta(minutes=10 * i)
            )

            db.add(reading)

        db.commit()

        print("Successfully generated 50 fake readings!")

    finally:
        db.close()


if __name__ == "__main__":
    seed_data()
