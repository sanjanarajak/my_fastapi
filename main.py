from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import pandas as pd
import os

app = FastAPI()

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Model
class Student(BaseModel):
    name: str
    education: str
    skills: str
    interests: str
    marks: str
    certifications: str
    ai_response: str

CSV_FILE = "career_data.csv"

# GET API
@app.get("/")
def home():
    return {
        "message": "FastAPI Career Guidance API Running"
    }

# POST API
@app.post("/career")
def save_data(student: Student):

    data = pd.DataFrame([student.dict()])

    if os.path.exists(CSV_FILE):
        data.to_csv(CSV_FILE, mode='a', header=False, index=False)
    else:
        data.to_csv(CSV_FILE, index=False)

    return {
        "message": "Data Saved Successfully"
    }