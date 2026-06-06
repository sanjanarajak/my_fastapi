from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import AliasChoices, BaseModel, EmailStr, Field


app = FastAPI(
    title="AI Career Guidance Workflow API",
    description="Receives ActivePieces career workflow data and exposes dashboard analytics.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path(__file__).resolve().parent
CSV_FILE = BASE_DIR / "career_data.csv"


class Student(BaseModel):
    name: str = Field(
        validation_alias=AliasChoices("name", "full_name", "Full Name", "Name")
    )
    email: EmailStr | None = Field(
        default=None,
        validation_alias=AliasChoices("email", "Email", "email_address", "Email Address"),
    )
    education: str = Field(
        default="",
        validation_alias=AliasChoices("education", "Education"),
    )
    skills: str = Field(default="", validation_alias=AliasChoices("skills", "Skills"))
    streams: str = Field(
        default="",
        validation_alias=AliasChoices("streams", "stream", "Streams", "Stream"),
    )
    interests: str = Field(
        default="",
        validation_alias=AliasChoices("interests", "interest", "Interests", "Interest"),
    )
    marks: str = Field(
        default="",
        validation_alias=AliasChoices("marks", "academic_marks", "Academic Marks", "Marks"),
    )
    certifications: str = Field(
        default="",
        validation_alias=AliasChoices("certifications", "Certifications"),
    )
    ai_response: str = Field(
        default="",
        validation_alias=AliasChoices(
            "ai_response", "gemini_response", "AI Response", "Gemini Response"
        ),
    )
    source: str = "ActivePieces"
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    model_config = {
        "populate_by_name": True,
        "str_strip_whitespace": True,
    }


def split_values(value: Any) -> list[str]:
    if pd.isna(value) or value is None:
        return []

    return [
        item.strip()
        for item in str(value).replace("|", ",").replace(";", ",").split(",")
        if item.strip()
    ]


def read_career_data() -> pd.DataFrame:
    columns = [
        "name",
        "email",
        "education",
        "skills",
        "streams",
        "interests",
        "marks",
        "certifications",
        "ai_response",
        "source",
        "created_at",
    ]

    if not CSV_FILE.exists():
        return pd.DataFrame(columns=columns)

    data = pd.read_csv(CSV_FILE)
    for column in columns:
        if column not in data.columns:
            data[column] = ""

    return data[columns].fillna("")


def value_counts(data: pd.DataFrame, column: str, multi_value: bool = False) -> list[dict[str, Any]]:
    if data.empty or column not in data:
        return []

    if multi_value:
        values = [item for value in data[column] for item in split_values(value)]
    else:
        values = [str(value).strip() for value in data[column] if str(value).strip()]

    if not values:
        return []

    counts = pd.Series(values).value_counts().head(10)
    return [{"label": label, "count": int(count)} for label, count in counts.items()]


@app.get("/")
def root():
    return {
        "status": "online",
        "project": "AI Career Guidance Workflow",
        "docs": "/docs",
    }


@app.get("/health")
def health_check():
    return {"status": "healthy"}


@app.get("/career/load-history")
def load_history():
    data = read_career_data()
    records = data.to_dict(orient="records")

    return {
        "status": "success",
        "count": len(records),
        "history": records,
    }


@app.get("/career/dashboard")
def dashboard():
    data = read_career_data()
    records = data.to_dict(orient="records")
    students_with_email = data["email"].astype(str).str.strip().ne("").sum() if not data.empty else 0
    students_with_ai_response = (
        data["ai_response"].astype(str).str.strip().ne("").sum() if not data.empty else 0
    )

    return {
        "status": "success",
        "summary": {
            "total_students": int(len(data)),
            "students_with_email": int(students_with_email),
            "students_with_ai_response": int(students_with_ai_response),
            "unique_streams": int(len({item for value in data["streams"] for item in split_values(value)}))
            if not data.empty
            else 0,
            "unique_skills": int(len({item for value in data["skills"] for item in split_values(value)}))
            if not data.empty
            else 0,
        },
        "charts": {
            "education": value_counts(data, "education"),
            "streams": value_counts(data, "streams", multi_value=True),
            "skills": value_counts(data, "skills", multi_value=True),
            "interests": value_counts(data, "interests", multi_value=True),
            "certifications": value_counts(data, "certifications", multi_value=True),
        },
        "recent_students": records[-8:][::-1],
        "students": records,
        "activepieces_recommendations": [
            "Send field names as name, email, education, skills, streams, interests, marks, certifications, ai_response.",
            "Keep multi-value fields comma-separated so the dashboard can count skills, streams, interests, and certifications.",
            "After Gemini creates guidance, POST the final payload to /career and include ai_response in the same request.",
            "Add created_at from ActivePieces if you want exact workflow timestamps; otherwise the API will create one.",
        ],
    }


@app.post("/career")
def save_data(student: Student):
    existing_data = read_career_data()
    new_data = pd.DataFrame([student.model_dump()])
    data = pd.concat([existing_data, new_data], ignore_index=True)

    data.to_csv(CSV_FILE, index=False)

    return {
        "status": "success",
        "message": "Career data saved successfully",
        "student": student.model_dump(),
    }
