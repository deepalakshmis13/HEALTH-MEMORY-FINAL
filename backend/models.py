"""
Persistent health-memory data model (§33).

Design notes
------------
* `MemoryEvent` is the spine of the system: every clinically meaningful fact —
  whoever produced it — becomes a memory event carrying full provenance
  (source type, author, confidence, verification status, consent scope).
* Specialised tables (Medication, LabResult, ...) hang off memory events so the
  timeline and the RAG index never lose the link back to the original source.
"""

from datetime import datetime

from mongo_orm import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    relationship,
)

from database import Base


def _now():
    return datetime.utcnow()


# ---------------------------------------------------------------------------
# Identity
# ---------------------------------------------------------------------------
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    email = Column(String(160), unique=True, nullable=False, index=True)
    password_hash = Column(String(320), nullable=False)
    full_name = Column(String(160), nullable=False)
    role = Column(String(32), nullable=False)  # patient|doctor|caregiver|reviewer
    phone = Column(String(40))
    is_guardian = Column(Boolean, default=False)
    created_at = Column(DateTime, default=_now)

    patient = relationship("Patient", back_populates="user", uselist=False)
    doctor = relationship("Doctor", back_populates="user", uselist=False)
    caregiver = relationship("Caregiver", back_populates="user", uselist=False)
    reviewer = relationship("Reviewer", back_populates="user", uselist=False)


class Patient(Base):
    __tablename__ = "patients"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    full_name = Column(String(160), nullable=False)
    date_of_birth = Column(String(24))
    age = Column(Integer)
    gender = Column(String(24))
    blood_group = Column(String(8))
    phone = Column(String(40))
    address = Column(String(320))
    emergency_contact_name = Column(String(160))
    emergency_contact_phone = Column(String(40))
    emergency_contact_relation = Column(String(80))
    primary_doctor_id = Column(Integer, ForeignKey("doctors.id"))
    old_age_home_id = Column(Integer, ForeignKey("old_age_homes.id"))
    room_number = Column(String(24))
    guardian_name = Column(String(160))
    guardian_phone = Column(String(40))
    notes = Column(Text)
    created_at = Column(DateTime, default=_now)

    user = relationship("User", back_populates="patient")
    primary_doctor = relationship("Doctor", foreign_keys=[primary_doctor_id])
    old_age_home = relationship("OldAgeHome", back_populates="residents")
    memory_events = relationship(
        "MemoryEvent", back_populates="patient", cascade="all, delete-orphan"
    )
    medications = relationship("Medication", back_populates="patient")
    allergies = relationship("Allergy", back_populates="patient")
    documents = relationship("Document", back_populates="patient")
    consents = relationship("Consent", back_populates="patient")


class Doctor(Base):
    __tablename__ = "doctors"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    full_name = Column(String(160), nullable=False)
    specialty = Column(String(120))
    hospital = Column(String(160))
    registration_no = Column(String(80))
    phone = Column(String(40))
    # External = identified from a medical record but not a registered user (§17)
    is_registered = Column(Boolean, default=True)
    created_at = Column(DateTime, default=_now)

    user = relationship("User", back_populates="doctor")


class Caregiver(Base):
    __tablename__ = "caregivers"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    full_name = Column(String(160), nullable=False)
    care_type = Column(String(32), default="INDIVIDUAL")  # INDIVIDUAL|OLD_AGE_HOME
    old_age_home_id = Column(Integer, ForeignKey("old_age_homes.id"))
    staff_code = Column(String(40))
    phone = Column(String(40))

    user = relationship("User", back_populates="caregiver")
    old_age_home = relationship("OldAgeHome", back_populates="staff")


class OldAgeHome(Base):
    __tablename__ = "old_age_homes"

    id = Column(Integer, primary_key=True)
    name = Column(String(160), nullable=False)
    address = Column(String(320))
    phone = Column(String(40))
    license_no = Column(String(80))

    residents = relationship("Patient", back_populates="old_age_home")
    staff = relationship("Caregiver", back_populates="old_age_home")


class Reviewer(Base):
    __tablename__ = "reviewers"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    full_name = Column(String(160), nullable=False)
    organisation_name = Column(String(160))
    license_no = Column(String(80))

    user = relationship("User", back_populates="reviewer")


class CareAssignment(Base):
    """Which caregiver looks after which patient."""

    __tablename__ = "care_assignments"

    id = Column(Integer, primary_key=True)
    caregiver_id = Column(Integer, ForeignKey("caregivers.id"), nullable=False)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    active = Column(Boolean, default=True)


class DoctorAssignment(Base):
    """Patient <-> doctor care relationship.

    One patient may have many doctors and one doctor many patients, so this is
    the join collection between them. The relationship is controlled by the
    patient: only a patient (or their guardian) creates an ACTIVE row, and only
    a patient removes one. Doctors can read their own rows but never write.

    ``status``
        ACTIVE    — the patient has added this doctor; the doctor sees them.
        SUGGESTED — a doctor named in an uploaded record (§17/§18). Grants no
                    access at all; it waits for the patient to accept it.
        REMOVED   — the patient removed the doctor. The row is kept, never
                    deleted, so the care history stays auditable.
    """

    __tablename__ = "doctor_assignments"

    id = Column(Integer, primary_key=True)
    doctor_id = Column(Integer, ForeignKey("doctors.id"), nullable=False)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    relationship_type = Column(String(48), default="TREATING")
    status = Column(String(24), default="ACTIVE", index=True)
    is_primary = Column(Boolean, default=False)
    routed_from_document_id = Column(Integer, ForeignKey("documents.id"))
    added_by_role = Column(String(32))
    added_by_user_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=_now)
    removed_at = Column(DateTime)

    doctor = relationship("Doctor")
    patient = relationship("Patient")


# ---------------------------------------------------------------------------
# Health memory
# ---------------------------------------------------------------------------
class MemoryEvent(Base):
    """One provenance-carrying fact in the persistent health memory."""

    __tablename__ = "memory_events"

    id = Column(Integer, primary_key=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False, index=True)

    event_type = Column(String(48), nullable=False)
    # CONSULTATION | MEDICATION | PRESCRIPTION | DIAGNOSIS | SYMPTOM | ALLERGY
    # | LAB_RESULT | HOSPITAL_VISIT | OBSERVATION | VOICE_ENTRY | DOCUMENT
    # | MEDICATION_ADMINISTRATION | MEDICATION_CHANGE | NOTE
    title = Column(String(240), nullable=False)
    content = Column(Text, nullable=False)
    event_date = Column(DateTime, default=_now, index=True)

    # --- provenance (§34/§35) ---
    source_type = Column(String(40), nullable=False)
    trust_level = Column(String(40), nullable=False, default="Patient Reported")
    author_role = Column(String(32))
    author_name = Column(String(160))
    author_user_id = Column(Integer, ForeignKey("users.id"))
    doctor_id = Column(Integer, ForeignKey("doctors.id"))
    document_id = Column(Integer, ForeignKey("documents.id"))
    confidence = Column(Float, default=1.0)
    verification_status = Column(String(32), default="NOT_REQUIRED")
    original_text = Column(Text)  # raw OCR / raw transcript
    consent_scope = Column(String(48), default="FULL_HEALTH_MEMORY")

    severity = Column(String(24), default="normal")  # normal|attention|critical
    tags = Column(JSON, default=list)
    extra = Column(JSON, default=dict)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=_now)

    patient = relationship("Patient", back_populates="memory_events")
    document = relationship("Document", back_populates="memory_events")
    doctor = relationship("Doctor")


class Medication(Base):
    __tablename__ = "medications"

    id = Column(Integer, primary_key=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False, index=True)
    memory_event_id = Column(Integer, ForeignKey("memory_events.id"))
    name = Column(String(160), nullable=False)
    dose = Column(String(80))
    frequency = Column(String(120))
    route = Column(String(48), default="Oral")
    instruction = Column(String(320))
    started_on = Column(DateTime, default=_now)
    stopped_on = Column(DateTime)
    status = Column(String(32), default="ACTIVE")  # ACTIVE|STOPPED|CHANGED
    prescriber_doctor_id = Column(Integer, ForeignKey("doctors.id"))
    source_type = Column(String(40), default="DOCTOR_DOCUMENT")
    confidence = Column(Float, default=1.0)
    verification_status = Column(String(32), default="NOT_REQUIRED")
    schedule_times = Column(JSON, default=list)  # ["08:00","20:00"]

    patient = relationship("Patient", back_populates="medications")
    prescriber = relationship("Doctor")


class Prescription(Base):
    __tablename__ = "prescriptions"

    id = Column(Integer, primary_key=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    doctor_id = Column(Integer, ForeignKey("doctors.id"))
    document_id = Column(Integer, ForeignKey("documents.id"))
    issued_on = Column(DateTime, default=_now)
    items = Column(JSON, default=list)
    instruction = Column(Text)
    source_type = Column(String(40), default="DOCTOR_DOCUMENT")
    verification_status = Column(String(32), default="NOT_REQUIRED")


class Diagnosis(Base):
    __tablename__ = "diagnoses"

    id = Column(Integer, primary_key=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    memory_event_id = Column(Integer, ForeignKey("memory_events.id"))
    name = Column(String(200), nullable=False)
    status = Column(String(32), default="ACTIVE")
    diagnosed_on = Column(DateTime, default=_now)
    doctor_id = Column(Integer, ForeignKey("doctors.id"))
    is_critical = Column(Boolean, default=False)
    source_type = Column(String(40), default="DOCTOR_RECORDED")


class Allergy(Base):
    __tablename__ = "allergies"

    id = Column(Integer, primary_key=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    substance = Column(String(160), nullable=False)
    reaction = Column(String(240))
    severity = Column(String(32), default="moderate")
    source_type = Column(String(40), default="DOCTOR_RECORDED")
    verification_status = Column(String(32), default="NOT_REQUIRED")

    patient = relationship("Patient", back_populates="allergies")


class LabResult(Base):
    __tablename__ = "lab_results"

    id = Column(Integer, primary_key=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    memory_event_id = Column(Integer, ForeignKey("memory_events.id"))
    test_name = Column(String(160), nullable=False)
    value = Column(String(80))
    unit = Column(String(40))
    reference_range = Column(String(80))
    flag = Column(String(24), default="normal")  # normal|high|low|critical
    tested_on = Column(DateTime, default=_now)
    lab_name = Column(String(160))
    document_id = Column(Integer, ForeignKey("documents.id"))


class HospitalVisit(Base):
    __tablename__ = "hospital_visits"

    id = Column(Integer, primary_key=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    hospital = Column(String(160))
    reason = Column(String(240))
    admitted_on = Column(DateTime)
    discharged_on = Column(DateTime)
    summary = Column(Text)
    doctor_id = Column(Integer, ForeignKey("doctors.id"))


class DoctorConsultation(Base):
    __tablename__ = "doctor_consultations"

    id = Column(Integer, primary_key=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    doctor_id = Column(Integer, ForeignKey("doctors.id"))
    memory_event_id = Column(Integer, ForeignKey("memory_events.id"))
    consulted_on = Column(DateTime, default=_now)
    reason = Column(String(240))
    findings = Column(Text)
    advice = Column(Text)
    follow_up_on = Column(DateTime)
    source_type = Column(String(40), default="DOCTOR_RECORDED")


class CaregiverObservation(Base):
    __tablename__ = "caregiver_observations"

    id = Column(Integer, primary_key=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    caregiver_id = Column(Integer, ForeignKey("caregivers.id"))
    shift_id = Column(Integer, ForeignKey("shifts.id"))
    memory_event_id = Column(Integer, ForeignKey("memory_events.id"))
    category = Column(String(48), default="general")  # meal|sleep|mood|incident|general
    observation = Column(Text, nullable=False)
    severity = Column(String(24), default="normal")
    observed_at = Column(DateTime, default=_now)


class VoiceEntry(Base):
    __tablename__ = "voice_entries"

    id = Column(Integer, primary_key=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    memory_event_id = Column(Integer, ForeignKey("memory_events.id"))
    transcript = Column(Text, nullable=False)
    audio_ref = Column(String(320))
    duration_seconds = Column(Float)
    recorded_at = Column(DateTime, default=_now)
    confidence = Column(Float, default=0.9)
    extracted_entities = Column(JSON, default=dict)
    source_type = Column(String(40), default="PATIENT_VOICE")


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False, index=True)
    filename = Column(String(320), nullable=False)
    stored_path = Column(String(400))
    mime_type = Column(String(120))
    size_bytes = Column(Integer, default=0)
    document_type = Column(String(64), default="SCANNED_DOCUMENT")
    # PRESCRIPTION | LAB_REPORT | DISCHARGE_SUMMARY | HANDWRITTEN_NOTE | OTHER
    is_handwritten = Column(Boolean, default=False)
    upload_date = Column(DateTime, default=_now)
    uploaded_by_user_id = Column(Integer, ForeignKey("users.id"))
    source_type = Column(String(40), default="SCANNED_DOCUMENT")
    ocr_status = Column(String(32), default="PENDING")  # PENDING|PROCESSED|FAILED
    ocr_engine = Column(String(48))
    confidence = Column(Float)
    verification_status = Column(String(32), default="NOT_REQUIRED")
    doctor_id = Column(Integer, ForeignKey("doctors.id"))
    doctor_name_raw = Column(String(160))
    notes = Column(Text)

    patient = relationship("Patient", back_populates="documents")
    memory_events = relationship("MemoryEvent", back_populates="document")
    ocr_result = relationship(
        "OCRResult", back_populates="document", uselist=False,
        cascade="all, delete-orphan",
    )


class OCRResult(Base):
    __tablename__ = "ocr_results"

    id = Column(Integer, primary_key=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    engine = Column(String(64))  # PrintedOCR | HandwritingOCR
    raw_text = Column(Text)
    overall_confidence = Column(Float, default=0.0)
    fields = Column(JSON, default=list)
    # [{field, label, value, confidence, clinically_important}]
    processed_at = Column(DateTime, default=_now)
    handwriting_detected = Column(Boolean, default=False)

    document = relationship("Document", back_populates="ocr_result")


class VerificationTask(Base):
    __tablename__ = "verification_tasks"

    id = Column(Integer, primary_key=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    document_id = Column(Integer, ForeignKey("documents.id"))
    ocr_result_id = Column(Integer, ForeignKey("ocr_results.id"))
    memory_event_id = Column(Integer, ForeignKey("memory_events.id"))
    field_key = Column(String(64))
    field_label = Column(String(120))
    extracted_value = Column(String(320))
    confidence = Column(Float)
    priority = Column(String(24), default="NORMAL")  # NORMAL|HIGH
    status = Column(String(32), default="PENDING_VERIFICATION")
    reason = Column(String(320))
    created_at = Column(DateTime, default=_now)

    document = relationship("Document")
    result = relationship(
        "VerificationResult", back_populates="task", uselist=False,
        cascade="all, delete-orphan",
    )


class VerificationResult(Base):
    __tablename__ = "verification_results"

    id = Column(Integer, primary_key=True)
    task_id = Column(Integer, ForeignKey("verification_tasks.id"), nullable=False)
    reviewer_id = Column(Integer, ForeignKey("reviewers.id"))
    reviewer_name = Column(String(160))
    action = Column(String(32))  # VERIFIED|CORRECTED|REJECTED
    original_value = Column(String(320))
    original_confidence = Column(Float)
    corrected_value = Column(String(320))
    clarification = Column(Text)
    verified_at = Column(DateTime, default=_now)

    task = relationship("VerificationTask", back_populates="result")


class Consent(Base):
    __tablename__ = "consents"

    id = Column(Integer, primary_key=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False, index=True)
    grantee_role = Column(String(32), nullable=False)
    # doctor | caregiver | old_age_home | reviewer | emergency
    grantee_id = Column(Integer)  # null => all holders of that role
    grantee_name = Column(String(160))
    scope = Column(String(48), nullable=False)
    granted = Column(Boolean, default=True)
    granted_at = Column(DateTime, default=_now)
    revoked_at = Column(DateTime)
    note = Column(String(320))

    patient = relationship("Patient", back_populates="consents")


class ConsentHistory(Base):
    __tablename__ = "consent_history"

    id = Column(Integer, primary_key=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    grantee_role = Column(String(32))
    grantee_name = Column(String(160))
    scope = Column(String(48))
    action = Column(String(24))  # GRANTED|REVOKED
    actor_name = Column(String(160))
    created_at = Column(DateTime, default=_now)


class Shift(Base):
    __tablename__ = "shifts"

    id = Column(Integer, primary_key=True)
    facility_id = Column(Integer, ForeignKey("old_age_homes.id"))
    caregiver_id = Column(Integer, ForeignKey("caregivers.id"))
    shift_code = Column(String(24))  # MORNING|AFTERNOON|NIGHT
    shift_date = Column(String(24))
    start_time = Column(String(12))
    end_time = Column(String(12))
    status = Column(String(24), default="ACTIVE")  # ACTIVE|CLOSED
    assigned_patient_ids = Column(JSON, default=list)
    created_at = Column(DateTime, default=_now)


class MedicationAdministration(Base):
    __tablename__ = "medication_administrations"

    id = Column(Integer, primary_key=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    medication_id = Column(Integer, ForeignKey("medications.id"), nullable=False)
    caregiver_id = Column(Integer, ForeignKey("caregivers.id"))
    shift_id = Column(Integer, ForeignKey("shifts.id"))
    memory_event_id = Column(Integer, ForeignKey("memory_events.id"))
    scheduled_time = Column(String(12))
    scheduled_date = Column(String(24))
    status = Column(String(32), default="Pending")
    # Pending|Administered|Missed|Skipped|Delayed|Needs Attention
    administered_at = Column(DateTime)
    notes = Column(Text)

    medication = relationship("Medication")


class CareTask(Base):
    __tablename__ = "care_tasks"

    id = Column(Integer, primary_key=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    shift_id = Column(Integer, ForeignKey("shifts.id"))
    caregiver_id = Column(Integer, ForeignKey("caregivers.id"))
    title = Column(String(240), nullable=False)
    category = Column(String(48), default="general")
    due_time = Column(String(12))
    status = Column(String(24), default="Pending")  # Pending|Done|Skipped
    notes = Column(Text)
    completed_at = Column(DateTime)


class ShiftHandover(Base):
    __tablename__ = "shift_handovers"

    id = Column(Integer, primary_key=True)
    shift_id = Column(Integer, ForeignKey("shifts.id"))
    caregiver_id = Column(Integer, ForeignKey("caregivers.id"))
    facility_id = Column(Integer, ForeignKey("old_age_homes.id"))
    patient_ids = Column(JSON, default=list)
    content = Column(Text)
    sources = Column(JSON, default=list)
    status = Column(String(24), default="DRAFT")  # DRAFT|SAVED
    generated_at = Column(DateTime, default=_now)
    saved_at = Column(DateTime)


class VisitSummary(Base):
    __tablename__ = "visit_summaries"

    id = Column(Integer, primary_key=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    doctor_id = Column(Integer, ForeignKey("doctors.id"))
    content = Column(Text)
    sources = Column(JSON, default=list)
    status = Column(String(24), default="DRAFT")  # DRAFT|SAVED
    generated_at = Column(DateTime, default=_now)
    saved_at = Column(DateTime)
    is_ai_generated = Column(Boolean, default=True)


class MemoryChunk(Base):
    """RAG index entry — one retrievable chunk plus its filtering metadata."""

    __tablename__ = "memory_chunks"

    id = Column(Integer, primary_key=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False, index=True)
    source_id = Column(String(64), nullable=False)  # e.g. "memory_event:12"
    source_type = Column(String(40), nullable=False)
    source_kind = Column(String(40))  # memory_event | document | observation ...
    text = Column(Text, nullable=False)
    title = Column(String(240))
    event_date = Column(DateTime, default=_now, index=True)
    author = Column(String(160))
    doctor_id = Column(Integer, ForeignKey("doctors.id"))
    confidence = Column(Float, default=1.0)
    verification_status = Column(String(32), default="NOT_REQUIRED")
    consent_scope = Column(String(48), default="FULL_HEALTH_MEMORY")
    trust_level = Column(String(40))
    vector = Column(JSON, default=list)
    created_at = Column(DateTime, default=_now)


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id = Column(Integer, primary_key=True)
    actor_user_id = Column(Integer, ForeignKey("users.id"))
    actor_name = Column(String(160))
    actor_role = Column(String(32))
    action = Column(String(64), nullable=False)
    patient_id = Column(Integer, ForeignKey("patients.id"))
    target = Column(String(160))
    detail = Column(Text)
    created_at = Column(DateTime, default=_now, index=True)
