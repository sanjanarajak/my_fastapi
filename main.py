from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
from fastapi import Body, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import AliasChoices, BaseModel, Field, ValidationError


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
    email: str | None = Field(
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


FIELD_ALIASES = {
    "name": {
        "name",
        "full_name",
        "full name",
        "student name",
        "student_name",
        "your name",
        "Name",
        "Full Name",
    },
    "email": {"email", "email address", "email_address", "Email", "Email Address"},
    "education": {"education", "qualification", "class", "degree", "Education"},
    "skills": {"skills", "technical skills", "skill", "Skills"},
    "streams": {"streams", "stream", "career stream", "branch", "Streams", "Stream"},
    "interests": {
        "interests",
        "interest",
        "career interests",
        "area of interest",
        "Interests",
        "Interest",
    },
    "marks": {
        "marks",
        "academic marks",
        "academic_marks",
        "score",
        "percentage",
        "Marks",
        "Academic Marks",
    },
    "certifications": {
        "certifications",
        "certification",
        "courses",
        "certificate",
        "Certifications",
    },
    "ai_response": {
        "ai_response",
        "ai response",
        "gemini_response",
        "gemini response",
        "career recommendation",
        "career_recommendation",
        "recommended career",
        "results",
        "result",
        "AI Response",
        "Gemini Response",
        "Career Recommendation",
    },
    "created_at": {"created_at", "created at", "timestamp", "Timestamp"},
    "source": {"source", "Source"},
}


def normalize_key(key: str) -> str:
    return str(key).strip().replace("_", " ").lower()


NORMALIZED_ALIASES = {
    normalize_key(alias): canonical
    for canonical, aliases in FIELD_ALIASES.items()
    for alias in aliases
}


def stringify_value(value: Any) -> str:
    if value is None:
        return ""

    if isinstance(value, list):
        return ", ".join(str(item).strip() for item in value if str(item).strip())

    if isinstance(value, dict):
        for key in ("value", "text", "label", "answer"):
            if key in value:
                return stringify_value(value[key])
        return ", ".join(
            stringify_value(item) for item in value.values() if stringify_value(item)
        )

    return str(value).strip()


def extract_payload(payload: Any) -> dict[str, Any]:
    if isinstance(payload, list):
        if not payload:
            return {}
        payload = payload[-1]

    if not isinstance(payload, dict):
        return {}

    for key in ("body", "payload", "data", "row", "record", "fields", "values"):
        nested = payload.get(key)
        if isinstance(nested, (dict, list)):
            return extract_payload(nested)

    return payload


def normalize_student_payload(payload: Any) -> dict[str, Any]:
    row = extract_payload(payload)
    normalized: dict[str, Any] = {}

    for key, value in row.items():
        canonical = NORMALIZED_ALIASES.get(normalize_key(key))
        if canonical:
            normalized[canonical] = stringify_value(value)

    if "source" not in normalized:
        normalized["source"] = "ActivePieces"

    return normalized


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


def save_student_record(student: Student) -> dict[str, Any]:
    existing_data = read_career_data()
    new_data = pd.DataFrame([student.model_dump()])
    data = pd.concat([existing_data, new_data], ignore_index=True)
    data.to_csv(CSV_FILE, index=False)

    return student.model_dump()


def parse_student(payload: Any) -> Student:
    normalized_payload = normalize_student_payload(payload)

    try:
        return Student.model_validate(normalized_payload or payload)
    except ValidationError as exc:
        raise HTTPException(
            status_code=422,
            detail={
                "message": "Webhook payload must include a student name.",
                "received_fields": list(extract_payload(payload).keys())
                if isinstance(extract_payload(payload), dict)
                else [],
                "errors": exc.errors(),
            },
        ) from exc


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
def save_data(payload: Any = Body(...)):
    student = parse_student(payload)
    saved_student = save_student_record(student)
    return {
        "status": "success",
        "message": "Career data saved successfully",
        "student": saved_student,
    }


@app.post("/webhook")
@app.post("/activepieces")
@app.post("/activepieces/webhook")
def activepieces_webhook(payload: Any = Body(...)):
    student = parse_student(payload)
    saved_student = save_student_record(student)
    return {
        "status": "success",
        "message": "ActivePieces webhook received",
        "student": saved_student,
    }
