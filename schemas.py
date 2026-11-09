from pydantic import BaseModel, ConfigDict, Field, EmailStr, field_validator, model_validator
from datetime import datetime
from enum import Enum


class ReadingBase(BaseModel):
    temperature: float


class ReadingCreate(ReadingBase):
    sensor_id: int
    timestamp: datetime | None = Field(default=None)  # Leave empty to use the current time


class ReadingResponse(ReadingBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    sensor_id: int
    timestamp: datetime


class ReadingUpdate(BaseModel):
    temperature: float | None = Field(default=None)
    timestamp: datetime | None = Field(default=None)


class DiabetesType(str, Enum):
    type_1 = "Type 1"
    type_2 = "Type 2"
    gestational = "Gestational"
    prediabetes = "Prediabetes"
    other = "Other"


class UserBase(BaseModel):
    full_name: str = Field(min_length=1, max_length=100)
    # Usernames can't contain @, so logging in with either one is never confused
    username: str | None = Field(default=None, min_length=3, max_length=20, pattern=r"^[a-zA-Z0-9_.]+$")
    email: EmailStr | None = Field(default=None, max_length=320)
    phone_number: str = Field(min_length=7, max_length=20, pattern=r"^\+?[0-9 ]+$")
    diabetes_type: DiabetesType

    # Stored in lowercase so "Jane" and "jane" can't be two different accounts
    @field_validator("username", "email")
    @classmethod
    def make_lowercase(cls, value):
        return value.lower() if value else value


class UserCreate(UserBase):
    password: str = Field(min_length=8, max_length=128)

    @model_validator(mode="after")
    def check_email_or_username(self):
        if self.email is None and self.username is None:
            raise ValueError("Enter an email or a username")
        if self.email is not None and self.username is not None:
            raise ValueError("Use an email or a username, not both")
        return self


class UserResponse(UserBase):
    model_config = ConfigDict(from_attributes=True)
    id: int


class UserUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=100)
    username: str | None = Field(default=None, min_length=3, max_length=20, pattern=r"^[a-zA-Z0-9_.]+$")
    email: EmailStr | None = Field(default=None, max_length=320)
    phone_number: str | None = Field(default=None, min_length=7, max_length=20, pattern=r"^\+?[0-9 ]+$")
    diabetes_type: DiabetesType | None = Field(default=None)
    password: str | None = Field(default=None, min_length=8, max_length=128)

    @field_validator("username", "email")
    @classmethod
    def make_lowercase(cls, value):
        return value.lower() if value else value



class HighTemperatureAlertResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    reading_id: int
    sensor_id: int
    temperature: float
    temperature_limit: float
    amount_over: float
    timestamp: datetime


class LowTemperatureAlertResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    reading_id: int
    sensor_id: int
    temperature: float
    temperature_limit: float
    amount_under: float
    timestamp: datetime


class Token(BaseModel):
    access_token: str
    token_type: str
