from sqlalchemy import Column, Integer, Float, DateTime, String, ForeignKey
from sqlalchemy.orm import relationship, Mapped, mapped_column
from datetime import datetime
from database import Base
from encryption import EncryptedString

## Primary
class Sensor(Base):
    __tablename__ = "sensors"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    location = Column(String, nullable=True)

    readings = relationship("Reading", back_populates="sensor", cascade="all, delete-orphan")

## Secondary
class Reading(Base):
    __tablename__ = "readings"

    id = Column(Integer, primary_key=True, index=True)
    sensor_id = Column(Integer, ForeignKey("sensors.id"), nullable=False)
    temperature = Column(Float, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)

    sensor = relationship("Sensor", back_populates="readings")
    high_temperature_alerts = relationship("HighTemperatureAlert", back_populates="reading", cascade="all, delete-orphan")
    low_temperature_alerts = relationship("LowTemperatureAlert", back_populates="reading", cascade="all, delete-orphan")


## Users
class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    # Personal details are encrypted in the database (see encryption.py)
    full_name: Mapped[str] = mapped_column(EncryptedString, nullable=False)
    username: Mapped[str | None] = mapped_column(String(20), unique=True, nullable=True)
    email: Mapped[str | None] = mapped_column(String(320), unique=True, nullable=True)
    password_hash: Mapped[str] = mapped_column(String(200), nullable=False)
    phone_number: Mapped[str] = mapped_column(EncryptedString, nullable=False)
    diabetes_type: Mapped[str] = mapped_column(EncryptedString, nullable=False)



## Temperature alerts
# Readings that went above the maximum safe temperature
class HighTemperatureAlert(Base):
    __tablename__ = "high_temperature_alerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    reading_id: Mapped[int] = mapped_column(ForeignKey("readings.id"), nullable=False, index=True)
    sensor_id: Mapped[int] = mapped_column(ForeignKey("sensors.id"), nullable=False, index=True)
    temperature: Mapped[float] = mapped_column(Float, nullable=False)
    temperature_limit: Mapped[float] = mapped_column(Float, nullable=False)
    amount_over: Mapped[float] = mapped_column(Float, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    reading = relationship("Reading", back_populates="high_temperature_alerts")


# Readings that went below the minimum safe temperature
class LowTemperatureAlert(Base):
    __tablename__ = "low_temperature_alerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    reading_id: Mapped[int] = mapped_column(ForeignKey("readings.id"), nullable=False, index=True)
    sensor_id: Mapped[int] = mapped_column(ForeignKey("sensors.id"), nullable=False, index=True)
    temperature: Mapped[float] = mapped_column(Float, nullable=False)
    temperature_limit: Mapped[float] = mapped_column(Float, nullable=False)
    amount_under: Mapped[float] = mapped_column(Float, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    reading = relationship("Reading", back_populates="low_temperature_alerts")
