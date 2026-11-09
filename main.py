from pathlib import Path

from fastapi import FastAPI, Request, HTTPException, status, Depends
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm
from starlette.exceptions import HTTPException as StarletteHTTPException
from typing import Annotated
from sqlalchemy import select, desc, or_
from sqlalchemy.orm import Session
from database import Base, engine, get_db, SessionLocal
from schemas import ReadingCreate, ReadingResponse, ReadingUpdate, UserCreate, UserResponse, UserUpdate, Token, HighTemperatureAlertResponse, LowTemperatureAlertResponse
from auth import hash_password, verify_password, create_access_token, get_current_user, DUMMY_HASH
from temperature_limits import check_temperature_limits, MIN_TEMPERATURE, MAX_TEMPERATURE
import models
import asyncio
from datetime import datetime

## REAL SENSOR IMPORT
from sensor import read_and_save, shutdown as shutdown_sensor

DEMO_TEMP_MIN_C = 2.0
DEMO_TEMP_MAX_C = 8.0

BASE_DIR = Path(__file__).resolve().parent
MEDIA_DIR = BASE_DIR / "media"
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"

# How often we ask the real sensor for a reading (seconds)
SENSOR_POLL_SECONDS = 5

MEDIA_DIR.mkdir(exist_ok=True)

Base.metadata.create_all(bind=engine)

app = FastAPI()

app.mount("/media", StaticFiles(directory=str(MEDIA_DIR)), name="media")
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
# Lets every template use the same temperature limits as the alerts
templates.env.globals["MIN_TEMPERATURE"] = MIN_TEMPERATURE
templates.env.globals["MAX_TEMPERATURE"] = MAX_TEMPERATURE


## Sensor loop ##
# Keeps grabbing data from the real sensor and saving it so the front end can show it
async def sensor_loop():
    while True:
        try:
            # We send the read_and_save to a diffrent thread
            await asyncio.to_thread(read_and_save)

        except Exception as e:
            print(f"[!] Sensor loop error: {e}")

        await asyncio.sleep(SENSOR_POLL_SECONDS)


## Events ##
# Startup
@app.on_event("startup")
async def startup():
    # We define what tasks we want ran
    app.state.sensor_task = asyncio.create_task(sensor_loop())



# Shutdown
@app.on_event("shutdown")
async def shutdown():
    app.state.sensor_task.cancel()
    # Release the GPIO pin used by the sensor
    shutdown_sensor()


## Web Pages ##
# Home page
@app.get("/", include_in_schema=False, name="home")
def home(request: Request, db: Session = Depends(get_db)):
    ## Get the current readings
    readings = (db.query(models.Reading)
        .order_by(models.Reading.timestamp.asc())
        .all()
    )

    ## Get the latest of them readings, if we were able to get readings in the first place
    latest_reading = readings[-1] if readings else None

    ## Create our sensor
    sensor = None

    if latest_reading:
        sensor = db.query(models.Sensor).filter(models.Sensor.id == latest_reading.sensor_id).first()

    ## Setting up the data for the chart
    chart_labels = [
        reading.timestamp.strftime("%H:%M:%S %d/%m/%Y")
        for reading in readings
    ]

    chart_values = [reading.temperature for reading in readings]

    return templates.TemplateResponse(
        request,
        "home.html",
        context={
            "sensor": sensor,
            "readings": readings,
            "latest_reading": latest_reading,
            "temp_min_c": DEMO_TEMP_MIN_C,
            "temp_max_c": DEMO_TEMP_MAX_C,
            "chart_labels": chart_labels,
            "chart_values": chart_values
        }
    )



# Readings page
@app.get("/readings", include_in_schema=False, name="sensor_readings")
def get_readings(request: Request, db: Session = Depends(get_db)):
    readings = (db.query(models.Reading)
        .order_by(desc(models.Reading.timestamp))
        .limit(75)
        .all()
    )

    return templates.TemplateResponse(
        request,
        "sensor_reading.html", 
        context={"readings": readings}
    )


def build_temperature_alerts(readings):
    alerts = []
    current_alert = None
    previous_state = "normal"

    for reading in readings:
        if reading.temperature < DEMO_TEMP_MIN_C:
            state = "low"
        elif reading.temperature > DEMO_TEMP_MAX_C:
            state = "high"
        else:
            state = "normal"

        if state == previous_state:
            continue

        if state == "normal":
            if current_alert is not None:
                current_alert["status"] = "Resolved"
                current_alert["severity"] = "Warning"
                current_alert = None

                alerts.append({
                    "reading_id": reading.id,
                    "temperature": reading.temperature,
                    "timestamp": reading.timestamp,
                    "type": "Temperature returned to normal",
                    "severity": "Resolved",
                    "status": "Resolved",
                    "message": (
                        f"Temperature returned to the acceptable demo range "
                        f"of {DEMO_TEMP_MIN_C:g}–{DEMO_TEMP_MAX_C:g}°C."
                    ),
                })
        else:
            if current_alert is not None:
                current_alert["status"] = "Resolved"
                current_alert["severity"] = "Warning"

            if state == "high":
                alert_type = "Temperature too high"
                message = (
                    f"{reading.temperature:.2f}°C is above the maximum demo "
                    f"limit of {DEMO_TEMP_MAX_C:g}°C."
                )
            else:
                alert_type = "Temperature too low"
                message = (
                    f"{reading.temperature:.2f}°C is below the minimum demo "
                    f"limit of {DEMO_TEMP_MIN_C:g}°C."
                )

            current_alert = {
                "reading_id": reading.id,
                "temperature": reading.temperature,
                "timestamp": reading.timestamp,
                "type": alert_type,
                "severity": "Critical",
                "status": "Active",
                "message": message,
            }
            alerts.append(current_alert)

        previous_state = state

    return alerts


@app.get("/alerts", include_in_schema=False, name="alerts")
def get_alerts(request: Request, db: Session = Depends(get_db)):
    readings = (
        db.query(models.Reading)
        .order_by(models.Reading.timestamp.asc(), models.Reading.id.asc())
        .all()
    )
    alerts = build_temperature_alerts(readings)
    alerts.sort(
        key=lambda alert: (alert["timestamp"], alert["reading_id"]),
        reverse=True,
    )

    active_alerts = sum(alert["status"] == "Active" for alert in alerts)

    return templates.TemplateResponse(
        request,
        "alerts.html",
        context={
            "alerts": alerts,
            "total_alerts": len(alerts),
            "active_alerts": active_alerts,
            "resolved_alerts": len(alerts) - active_alerts,
            "temp_min_c": DEMO_TEMP_MIN_C,
            "temp_max_c": DEMO_TEMP_MAX_C,
        },
    )



## API Points ##
# Readings endpoint
@app.get("/api/readings")
def get_sensor_readings(db: Session = Depends(get_db)):
    return (db.query(models.Reading)
        .order_by(desc(models.Reading.timestamp))
        .limit(100)
        .all()
    )



# Sensors endpoint
@app.get("/api/sensors")
def get_sensors(db: Session = Depends(get_db)):
    return db.query(models.Sensor).all()



# Sensors get by id
@app.get("/api/sensors/{sensor_id}/readings")
def get_sensor_readings_by_id(sensor_id: int, db: Session = Depends(get_db)):
    sensor = (db.query(models.Sensor)
        .filter(models.Sensor.id == sensor_id)
        .first()
    )

    if not sensor:
        raise HTTPException(status_code=404, detail="Sensor not found")

    return (db.query(models.Reading)
        .filter(models.Reading.sensor_id == sensor_id)
        .order_by(desc(models.Reading.timestamp))
        .limit(100)
        .all()
    )



## Dealing With Readings ##
# Adding, updating and deleting readings needs a login (current_user)
# Add a reading (pass a timestamp to fill in a reading that was missed)
@app.post("/api/readings", response_model=ReadingResponse, status_code=status.HTTP_201_CREATED)
def create_reading(
    reading: ReadingCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[models.User, Depends(get_current_user)]
):
    result = db.execute(select(models.Sensor).where(models.Sensor.id == reading.sensor_id))
    sensor = result.scalars().first()

    if not sensor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sensor not found")

    new_reading = models.Reading(
        sensor_id = reading.sensor_id,
        temperature = reading.temperature,
        timestamp = reading.timestamp or datetime.utcnow()
    )

    check_temperature_limits(new_reading)
    db.add(new_reading)
    db.commit()
    db.refresh(new_reading)
    return new_reading



# Update a reading (all fields)
@app.put("/api/readings/{reading_id}", response_model=ReadingResponse)
def update_reading_full(
    reading_id: int,
    reading_data: ReadingCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[models.User, Depends(get_current_user)]
):
    result = db.execute(select(models.Reading).where(models.Reading.id == reading_id))
    reading = result.scalars().first()

    if not reading:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reading not found")

    if reading_data.sensor_id != reading.sensor_id:
        result = db.execute(select(models.Sensor).where(models.Sensor.id == reading_data.sensor_id))
        sensor = result.scalars().first()

        if not sensor:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sensor not found")

    reading.sensor_id = reading_data.sensor_id
    reading.temperature = reading_data.temperature

    if reading_data.timestamp is not None:
        reading.timestamp = reading_data.timestamp

    check_temperature_limits(reading)
    db.commit()
    db.refresh(reading)

    return reading



# Update a reading (only the fields sent)
@app.patch("/api/readings/{reading_id}", response_model=ReadingResponse)
def update_reading_partial(
    reading_id: int,
    reading_data: ReadingUpdate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[models.User, Depends(get_current_user)]
):
    result = db.execute(select(models.Reading).where(models.Reading.id == reading_id))
    reading = result.scalars().first()

    if not reading:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reading not found")
    
    update_data = reading_data.model_dump(exclude_unset=True)
    
    for field, value in update_data.items():
        setattr(reading, field, value)
    
    check_temperature_limits(reading)
    db.commit()
    db.refresh(reading)
    
    return reading



# Delete a reading
@app.delete("/api/readings/{reading_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_reading(
    reading_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[models.User, Depends(get_current_user)]
):
    result = db.execute(select(models.Reading).where(models.Reading.id == reading_id))
    reading = result.scalars().first()

    if not reading:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reading not found")

    db.delete(reading)
    db.commit()


## Temp Limits ##
# Get readings that went above the safe limit
@app.get("/api/alerts/high", response_model=list[HighTemperatureAlertResponse])
def get_high_temperature_alerts(db: Annotated[Session, Depends(get_db)]):
    result = db.execute(select(models.HighTemperatureAlert).order_by(desc(models.HighTemperatureAlert.timestamp)))
    return result.scalars().all()



# Get readings that went below the safe limit
@app.get("/api/alerts/low", response_model=list[LowTemperatureAlertResponse])
def get_low_temperature_alerts(db: Annotated[Session, Depends(get_db)]):
    result = db.execute(select(models.LowTemperatureAlert).order_by(desc(models.LowTemperatureAlert.timestamp)))
    return result.scalars().all()



## Deleting reading ##
# Deleting alerts needs a login (current_user)
# Delete a high temperature alert (the reading is kept)
@app.delete("/api/alerts/high/{alert_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_high_temperature_alert(
    alert_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[models.User, Depends(get_current_user)]
):
    result = db.execute(select(models.HighTemperatureAlert).where(models.HighTemperatureAlert.id == alert_id))
    alert = result.scalars().first()
    if not alert:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")
    db.delete(alert)
    db.commit()



# Delete a low temperature alert (the reading is kept)
@app.delete("/api/alerts/low/{alert_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_low_temperature_alert(
    alert_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[models.User, Depends(get_current_user)]
):
    result = db.execute(select(models.LowTemperatureAlert).where(models.LowTemperatureAlert.id == alert_id))
    alert = result.scalars().first()
    if not alert:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")
    db.delete(alert)
    db.commit()



# Create a user account
@app.post("/api/user", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(user: UserCreate, db: Annotated[Session, Depends(get_db)]):
    if user.username is not None:
        result = db.execute(select(models.User).where(models.User.username == user.username))
        existing_user = result.scalars().first()
        if existing_user:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already exists")
    if user.email is not None:
        result = db.execute(select(models.User).where(models.User.email == user.email))
        existing_email = result.scalars().first()
        if existing_email:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already exists")
    new_user = models.User(
        full_name = user.full_name,
        username = user.username,
        email = user.email,
        password_hash = hash_password(user.password),
        phone_number = user.phone_number,
        diabetes_type = user.diabetes_type.value
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user



# Log in with an email or a username
@app.post("/api/login", response_model=Token)
def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Annotated[Session, Depends(get_db)]
):
    login_name = form_data.username.strip().lower()
    result = db.execute(select(models.User).where(
        or_(models.User.email == login_name, models.User.username == login_name)
    ))
    user = result.scalars().first()
    # The password is always checked, and the error never says which part was wrong,
    # so nobody can use this to find out which emails or usernames have an account
    password_hash = user.password_hash if user else DUMMY_HASH
    if not verify_password(form_data.password, password_hash) or not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email/username or password",
            headers={"WWW-Authenticate": "Bearer"}
        )
    return {"access_token": create_access_token(user.id), "token_type": "bearer"}



# Get a user account (users can only see their own)
@app.get("/api/user/{user_id}", response_model=UserResponse)
def get_user(
    user_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[models.User, Depends(get_current_user)]
):
    if user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can only view your own account")
    result = db.execute(select(models.User).where(models.User.id == user_id))
    user = result.scalars().first()
    if user:
        return user
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")



# Update a user account (only the fields sent, and only your own account)
@app.patch("/api/user/{user_id}", response_model=UserResponse)
def update_user(
    user_id: int,
    user_data: UserUpdate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[models.User, Depends(get_current_user)]
):
    if user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can only change your own account")
    result = db.execute(select(models.User).where(models.User.id == user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    # An account uses an email or a username, so only the one it signed up with can be changed
    if user_data.username is not None and user.email is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This account uses an email, not a username")
    if user_data.email is not None and user.username is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This account uses a username, not an email")
    if user_data.username is not None and user_data.username != user.username:
        result = db.execute(select(models.User).where(models.User.username == user_data.username))
        existing_user = result.scalars().first()
        if existing_user:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already exists")
    if user_data.email is not None and user_data.email != user.email:
        result = db.execute(select(models.User).where(models.User.email == user_data.email))
        existing_email = result.scalars().first()
        if existing_email:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already exists")
    if user_data.full_name is not None:
        user.full_name = user_data.full_name
    if user_data.username is not None:
        user.username = user_data.username
    if user_data.email is not None:
        user.email = user_data.email
    if user_data.phone_number is not None:
        user.phone_number = user_data.phone_number
    if user_data.diabetes_type is not None:
        user.diabetes_type = user_data.diabetes_type.value
    if user_data.password is not None:
        user.password_hash = hash_password(user_data.password)
    db.commit()
    db.refresh(user)
    return user



# Delete a user account (only your own account)
@app.delete("/api/user/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[models.User, Depends(get_current_user)]
):
    if user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can only delete your own account")
    result = db.execute(select(models.User).where(models.User.id == user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    db.delete(user)
    db.commit()