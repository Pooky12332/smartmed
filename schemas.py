from pydantic import BaseModel, ConfigDict, Field, EmailStr
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
    email: EmailStr = Field(max_length=320)
    phone_number: str = Field(min_length=7, max_length=20, pattern=r"^\+?[0-9 ]+$")
    diabetes_type: DiabetesType


class UserCreate(UserBase):
    password: str = Field(min_length=8, max_length=128)


class UserResponse(UserBase):
    model_config = ConfigDict(from_attributes=True)
    id: int


class UserUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=100)
    email: EmailStr | None = Field(default=None, max_length=320)
    phone_number: str | None = Field(default=None, min_length=7, max_length=20, pattern=r"^\+?[0-9 ]+$")
    diabetes_type: DiabetesType | None = Field(default=None)
    password: str | None = Field(default=None, min_length=8, max_length=128)
