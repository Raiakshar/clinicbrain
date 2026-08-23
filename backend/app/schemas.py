import datetime as dt
from typing import Literal

from pydantic import BaseModel, Field


class SignupRequest(BaseModel):
    clinic_name: str = Field(min_length=1, max_length=200)
    name: str = Field(min_length=1, max_length=200)
    phone: str = Field(min_length=5, max_length=20)
    password: str = Field(min_length=6, max_length=100)


class LoginRequest(BaseModel):
    phone: str
    password: str


class UserOut(BaseModel):
    id: int
    name: str
    role: str
    clinic_id: int

    model_config = {"from_attributes": True}


class AuthResponse(BaseModel):
    token: str
    user: UserOut


class PatientCreate(BaseModel):
    name: str = Field(min_length=1, max_length=300)
    phone: str | None = None
    dob: dt.date | None = None
    gender: str | None = None
    whatsapp_consent: bool = True


class PatientOut(PatientCreate):
    id: int
    whatsapp_consent: bool | None = None
    allergies: list[str] | None = None

    model_config = {"from_attributes": True}


class EventCreate(BaseModel):
    type: Literal["visit", "prescription", "lab", "document", "note"]
    event_date: dt.date | None = None
    payload: dict = {}


class EventOut(EventCreate):
    id: int
    created_at: dt.datetime

    model_config = {"from_attributes": True}


class ConfirmPayload(BaseModel):
    document_type: Literal["visit", "prescription", "lab", "letter", "report"]
    event_date: dt.date | None = None
    summary: str = ""
    content_text: str = ""


class SearchItem(BaseModel):
    source: str
    id: int
    patient_id: int
    title: str


class RxItemIn(BaseModel):
    drug_name: str = Field(min_length=1, max_length=200)
    dose_mg: float = Field(gt=0)
    frequency_per_day: int = Field(default=1, ge=1, le=12)
    duration_days: int | None = Field(default=None, ge=1)
    instructions: str | None = Field(default=None, max_length=1000)


class RxCheckRequest(BaseModel):
    items: list[RxItemIn] = Field(min_length=1)


class RxSaveRequest(RxCheckRequest):
    notes: str | None = Field(default=None, max_length=2000)
    followup_date: dt.date | None = None
    acknowledged_warnings: bool = False


class AllergiesUpdate(BaseModel):
    allergies: list[str]
