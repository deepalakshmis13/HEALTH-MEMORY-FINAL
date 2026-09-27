"""Pydantic request/response contracts."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, EmailStr, Field


# ---------------------------------------------------------------- auth
class LoginRequest(BaseModel):
    email: str
    password: str


class RegisterRequest(BaseModel):
    email: str
    password: str = Field(min_length=6)
    full_name: str
    role: str
    phone: Optional[str] = None
    # patient-only extras
    age: Optional[int] = None
    gender: Optional[str] = None
    blood_group: Optional[str] = None
    guardian_name: Optional[str] = None


class UserOut(BaseModel):
    id: int
    email: str
    full_name: str
    role: str
    profile_id: Optional[int] = None
    patient_id: Optional[int] = None
    extra: Dict[str, Any] = {}


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# ---------------------------------------------------------------- ingestion
class TextIngestionRequest(BaseModel):
    patient_id: int
    text: str = Field(min_length=3)
    entry_date: Optional[str] = None
    note: Optional[str] = None


class VoiceIngestionRequest(BaseModel):
    patient_id: int
    transcript: str = Field(min_length=3)
    duration_seconds: Optional[float] = None
    recognition_confidence: Optional[float] = 0.9
    audio_ref: Optional[str] = None


class IngestionResult(BaseModel):
    memory_event_ids: List[int] = []
    entities: Dict[str, Any] = {}
    confidence: float = 1.0
    verification_tasks: List[int] = []
    message: str = ""


# ---------------------------------------------------------------- memory
class MemoryEventCreate(BaseModel):
    patient_id: int
    event_type: str
    title: str
    content: str
    event_date: Optional[str] = None
    severity: Optional[str] = "normal"
    tags: List[str] = []


class MemoryEventOut(BaseModel):
    id: int
    patient_id: int
    event_type: str
    title: str
    content: str
    event_date: datetime
    source_type: str
    trust_level: str
    author_role: Optional[str] = None
    author_name: Optional[str] = None
    doctor_name: Optional[str] = None
    confidence: float
    verification_status: str
    severity: str
    tags: List[str] = []
    document_id: Optional[int] = None
    original_text: Optional[str] = None
    extra: Dict[str, Any] = {}

    class Config:
        from_attributes = True


# ---------------------------------------------------------------- verification
class VerifyRequest(BaseModel):
    note: Optional[str] = None


class CorrectRequest(BaseModel):
    corrected_value: str
    clarification: Optional[str] = None


class RejectRequest(BaseModel):
    reason: str


# ---------------------------------------------------------------- consent
class ConsentUpdate(BaseModel):
    patient_id: int
    grantee_role: str
    grantee_id: Optional[int] = None
    grantee_name: Optional[str] = None
    scope: str
    granted: bool
    note: Optional[str] = None


# ---------------------------------------------------------------- caregiver
class ShiftStartRequest(BaseModel):
    care_type: str  # INDIVIDUAL | OLD_AGE_HOME
    shift_code: str
    facility_id: Optional[int] = None
    patient_ids: List[int] = []
    shift_date: Optional[str] = None


class MedicationVerifyRequest(BaseModel):
    administration_id: Optional[int] = None
    patient_id: Optional[int] = None
    medication_id: Optional[int] = None
    shift_id: Optional[int] = None
    status: str = "Administered"
    notes: Optional[str] = None
    scheduled_time: Optional[str] = None


class ObservationRequest(BaseModel):
    patient_id: int
    shift_id: Optional[int] = None
    category: str = "general"
    observation: str
    severity: str = "normal"


class CareTaskUpdate(BaseModel):
    status: str
    notes: Optional[str] = None


class HandoverRequest(BaseModel):
    shift_id: int
    patient_ids: List[int] = []


class SaveHandoverRequest(BaseModel):
    handover_id: int
    content: str


# ---------------------------------------------------------------- doctor
class VisitSummaryRequest(BaseModel):
    patient_id: int


class SaveVisitSummaryRequest(BaseModel):
    summary_id: int
    content: str


# ---------------------------------------------------------------- chat
class ChatRequest(BaseModel):
    patient_id: Optional[int] = None
    message: str
    history: List[Dict[str, str]] = []


class ChatSource(BaseModel):
    source_id: str
    title: str
    source_type: str
    date: Optional[str] = None
    trust_level: Optional[str] = None
    confidence: Optional[float] = None
    excerpt: Optional[str] = None


class ChatResponse(BaseModel):
    answer: str
    sources: List[ChatSource] = []
    agent: str
    provider: str
    explanation: str = ""


class CareTeamDoctorRequest(BaseModel):
    """Patient adding a doctor to their own care team."""

    doctor_id: int
    make_primary: bool = False
