from fastapi import FastAPI, Request, HTTPException, status, Depends
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from typing import Annotated
from sqlalchemy import select, desc
from sqlalchemy.orm import Session
from database import Base, engine, get_db, SessionLocal
import models
import asyncio

## TEMP FAKE IMPORT 
from fake_sensor import sensor_simulator, generate_reading

Base.metadata.create_all(bind=engine)

app = FastAPI()

app.mount("/media", StaticFiles(directory="media"), name="media")
app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")


## Events ##
# Startup
@app.on_event("startup")
async def startup():
    # We define what tasks we want ran
    app.state.sensor_task = asyncio.create_task(sensor_simulator())



# Shutdown
@app.on_event("shutdown")
async def shutdown():
    app.state.sensor_task.cancel()


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



## TEMP FUNCTIONS
@app.post("/api/simulate")
def simulate_readings():
    generate_reading()

    return {
        "message": "Fake sensor readings generated successfully"
    }