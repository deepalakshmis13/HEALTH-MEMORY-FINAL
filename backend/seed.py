"""
Demo data seeder (§40, §41).

Creates three fictional patients with a full longitudinal history and runs the
real ingestion pipeline over generated documents — including a handwritten
prescription whose OCR confidence lands below the low-confidence threshold, so
it appears in the Reviewer Verification Queue exactly as the demo requires.

    python seed.py            # reset and seed
    python seed.py --keep     # seed without dropping the existing database
"""

import random
import sys
from datetime import datetime, timedelta
from pathlib import Path

from config import STORAGE_DIR
from database import SessionLocal, drop_all, init_db, is_seeded, store_description

import models  # noqa: F401
from auth import Principal
from models import (
    Allergy,
    CareAssignment,
    Caregiver,
    CaregiverObservation,
    Diagnosis,
    Doctor,
    DoctorAssignment,
    DoctorConsultation,
    HospitalVisit,
    LabResult,
    Medication,
    MedicationAdministration,
    OldAgeHome,
    Patient,
    Reviewer,
    Shift,
    User,
)
from services import consent_service, document_service, ingestion_service, memory_service
from utils.security import hash_password

PASSWORD = "Demo@123"
NOW = datetime.utcnow()


def days(count: int) -> datetime:
    return NOW - timedelta(days=count)


# ---------------------------------------------------------------------------
# Document fixtures
# ---------------------------------------------------------------------------
HANDWRITTEN_PRESCRIPTION = """#legibility: 0.54
Dr. Arun Kumar  MBBS MD (Cardiology)
Sunrise Hospital, Chennai   Regn: TN/45021
Date: {date}

Patient: Radha Krishnan   Age: 72 / F

Rx
1. Amlodipine 5 mg  once daily  after food
2. Atorvastatin 10 mg  at bedtime

BP 148/92. Complains of dizziness on standing.
Monitor blood pressure daily. Review after 2 weeks.
"""

LAB_REPORT = """#legibility: 0.94
APOLLO DIAGNOSTICS, Chennai
LABORATORY REPORT
Date: {date}
Patient: Radha Krishnan, 72 / F
Referred by: Dr. Arun Kumar, Cardiology

HbA1c            : 7.4 %      (Ref 4.0 - 5.6)
Fasting Blood Sugar : 132 mg/dL  (Ref 70 - 100)
Serum Creatinine : 1.1 mg/dL  (Ref 0.6 - 1.2)
Haemoglobin      : 11.8 g/dL  (Ref 12.0 - 15.0)
Total Cholesterol: 196 mg/dL
LDL Cholesterol  : 118 mg/dL

Impression: Glycaemic control suboptimal. Mild anaemia.
Clinical correlation advised.
"""

DISCHARGE_SUMMARY = """#legibility: 0.93
CITY CARE CLINIC
DISCHARGE SUMMARY
Date: {date}
Patient: Ganesan Murugan, 78 / M
Consultant: Dr. Meera Raghavan, General Medicine

Admitted with breathlessness and cough for 4 days.
Known COPD and osteoarthritis.

Treatment given: nebulisation, oral steroids, oxygen support.
Discharge medication:
1. Salbutamol inhaler  twice daily
2. Paracetamol 500 mg  when required
3. Vitamin D3 60000 IU  once weekly

Advised: avoid dust exposure, breathing exercises daily.
Review after 3 weeks.
"""

HANDWRITTEN_THYROID = """#legibility: 0.72
Dr. Rajesh Iyer  MD
City Care Clinic, Chennai
Date: {date}

Patient: Lakshmi Narayanan  68 / F

TSH 8.2 - hypothyroidism
Rx
1. Levothyroxine 50 mcg  once daily  empty stomach
2. Ferrous sulphate 200 mg  once daily  after food

Repeat TSH after 6 weeks.
"""


def render_document(folder: Path, name: str, body: str, handwritten: bool) -> Path:
    """Render a fixture as a PNG page (Pillow) with a ground-truth sidecar."""
    folder.mkdir(parents=True, exist_ok=True)
    lines = body.splitlines()
    legibility_line = lines[0] if lines and lines[0].startswith("#legibility") else None
    text_lines = lines[1:] if legibility_line else lines

    target = folder / name
    try:
        from PIL import Image, ImageDraw, ImageFont

        def load_font(size: int, italic: bool):
            candidates = (
                [
                    "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Italic.ttf",
                    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Oblique.ttf",
                    "/Library/Fonts/Georgia Italic.ttf",
                    "C:/Windows/Fonts/georgiai.ttf",
                ]
                if italic
                else [
                    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                    "/Library/Fonts/Arial.ttf",
                    "C:/Windows/Fonts/arial.ttf",
                ]
            )
            for candidate in candidates:
                try:
                    return ImageFont.truetype(candidate, size)
                except Exception:
                    continue
            return ImageFont.load_default()

        rng = random.Random(name)
        font = load_font(22, handwritten)
        line_height = 38
        width = 980
        height = max(460, 70 + len(text_lines) * line_height)
        image = Image.new("RGB", (width, height), "white")
        draw = ImageDraw.Draw(image)
        y = 34
        for line in text_lines:
            if handwritten:
                # Uneven baseline and spacing — what a recogniser struggles with.
                x = 46 + rng.randint(-3, 3)
                for char in line:
                    draw.text((x, y + rng.randint(-4, 4)), char,
                              font=font, fill=(22, 26, 92))
                    advance = draw.textlength(char, font=font)
                    x += advance * rng.uniform(0.84, 1.02)
            else:
                draw.text((46, y), line, font=font, fill=(12, 12, 12))
            y += line_height
        image.save(target)
    except Exception:
        target = folder / (Path(name).stem + ".txt")
        target.write_text("\n".join(text_lines), encoding="utf-8")

    sidecar = target.with_suffix(target.suffix + ".groundtruth.txt")
    sidecar.write_text(
        ((legibility_line + "\n") if legibility_line else "") + "\n".join(text_lines),
        encoding="utf-8",
    )
    return target


# ---------------------------------------------------------------------------
def make_user(db, email, name, role, password=PASSWORD, phone=None) -> User:
    user = User(
        email=email,
        password_hash=hash_password(password),
        full_name=name,
        role=role,
        phone=phone,
    )
    db.add(user)
    db.flush()
    return user


def event(db, patient_id, **kwargs):
    return memory_service.create_event(db, patient_id, commit=False, **kwargs)


# ---------------------------------------------------------------------------
def seed(reset: bool = True, only_if_empty: bool = False):
    """Build the demo environment.

    reset          drop every collection first, so the result is exactly this
                   script's output and nothing accumulates across runs.
    only_if_empty  do nothing when the database already holds users. Safe to
                   run on every boot without duplicating patients, documents
                   or medications.
    """
    init_db()
    store = store_description()
    print(f"\nDatabase: {store['store']} ({store['detail']})")
    if not store["persistent"]:
        print(
            "  WARNING: this store is process-local. Seeding here will NOT be\n"
            "  visible to a server started in another terminal. Install "
            "'montydb'\n  or set MONGODB_URI to a real MongoDB instance.\n"
        )

    already = is_seeded()
    if only_if_empty and already:
        print("Database already contains users — leaving it untouched.\n")
        return
    if already and not reset:
        print(
            "Database already contains users. Re-running without --reset would\n"
            "duplicate patients, documents and medications, so nothing was "
            "written.\n"
            "  python seed.py            rebuild the demo environment\n"
            "  python seed.py --if-empty seed only when the database is empty\n"
        )
        return

    if reset:
        drop_all()
        for path in STORAGE_DIR.rglob("*"):
            if path.is_file():
                path.unlink()
    init_db()
    db = SessionLocal()

    try:
        # ---------------------------------------------------------- facility
        home = OldAgeHome(
            name="Sunrise Senior Living",
            address="14 Anna Salai, Chennai 600002",
            phone="+91 44 2345 6789",
            license_no="TN/OAH/2019/0412",
        )
        db.add(home)
        db.flush()

        # ---------------------------------------------------------- doctors
        arun_user = make_user(db, "doctor@demo.health", "Dr. Arun Kumar", "doctor",
                              phone="+91 98400 11223")
        arun = Doctor(
            user_id=arun_user.id, full_name="Dr. Arun Kumar", specialty="Cardiology",
            hospital="Sunrise Hospital", registration_no="TN/45021",
            phone="+91 98400 11223", is_registered=True,
        )
        meera_user = make_user(db, "doctor2@demo.health", "Dr. Meera Raghavan",
                               "doctor", phone="+91 98401 55667")
        meera = Doctor(
            user_id=meera_user.id, full_name="Dr. Meera Raghavan",
            specialty="General Medicine", hospital="City Care Clinic",
            registration_no="TN/51877", phone="+91 98401 55667", is_registered=True,
        )
        db.add_all([arun, meera])
        db.flush()

        # ---------------------------------------------------------- reviewer
        pharm_user = make_user(db, "reviewer@demo.health", "Kavitha Menon",
                               "reviewer", phone="+91 98402 33445")
        reviewer = Reviewer(
            user_id=pharm_user.id, full_name="Kavitha Menon",
            organisation_name="MedPlus Clinical Review Desk, Anna Nagar", license_no="TN/PH/2201",
        )
        db.add(reviewer)
        db.flush()

        # ---------------------------------------------------------- caregivers
        priya_user = make_user(db, "caregiver@demo.health", "Priya Sharma",
                               "caregiver", phone="+91 98403 77889")
        priya = Caregiver(
            user_id=priya_user.id, full_name="Priya Sharma",
            care_type="OLD_AGE_HOME", old_age_home_id=home.id, staff_code="SSL-071",
            phone="+91 98403 77889",
        )
        anitha_user = make_user(db, "caregiver2@demo.health", "Anitha Raj",
                                "caregiver", phone="+91 98404 22110")
        anitha = Caregiver(
            user_id=anitha_user.id, full_name="Anitha Raj",
            care_type="INDIVIDUAL", staff_code="IND-204", phone="+91 98404 22110",
        )
        db.add_all([priya, anitha])
        db.flush()

        # ---------------------------------------------------------- patients
        radha_user = make_user(db, "patient@demo.health", "Radha Krishnan",
                               "patient", phone="+91 98405 66778")
        radha = Patient(
            user_id=radha_user.id, full_name="Radha Krishnan", age=72,
            date_of_birth="1954-03-18", gender="Female", blood_group="B+",
            phone="+91 98405 66778", address="Sunrise Senior Living, Chennai",
            emergency_contact_name="Vijay Krishnan",
            emergency_contact_phone="+91 98406 12345",
            emergency_contact_relation="Son",
            primary_doctor_id=arun.id, old_age_home_id=home.id, room_number="12",
            guardian_name="Vijay Krishnan", guardian_phone="+91 98406 12345",
        )

        ganesan_user = make_user(db, "patient2@demo.health", "Ganesan Murugan",
                                 "patient", phone="+91 98407 45612")
        ganesan = Patient(
            user_id=ganesan_user.id, full_name="Ganesan Murugan", age=78,
            date_of_birth="1948-11-02", gender="Male", blood_group="O+",
            phone="+91 98407 45612", address="22 Gandhi Street, Adyar, Chennai",
            emergency_contact_name="Kamala Ganesan",
            emergency_contact_phone="+91 98408 99887",
            emergency_contact_relation="Wife",
            primary_doctor_id=meera.id,
            guardian_name="Kamala Ganesan", guardian_phone="+91 98408 99887",
        )

        lakshmi_user = make_user(db, "patient3@demo.health", "Lakshmi Narayanan",
                                 "patient", phone="+91 98409 32145")
        lakshmi = Patient(
            user_id=lakshmi_user.id, full_name="Lakshmi Narayanan", age=68,
            date_of_birth="1958-06-25", gender="Female", blood_group="A+",
            phone="+91 98409 32145", address="Sunrise Senior Living, Chennai",
            emergency_contact_name="Deepa Narayanan",
            emergency_contact_phone="+91 98410 77665",
            emergency_contact_relation="Daughter",
            primary_doctor_id=arun.id, old_age_home_id=home.id, room_number="08",
            guardian_name="Deepa Narayanan", guardian_phone="+91 98410 77665",
        )
        db.add_all([radha, ganesan, lakshmi])
        db.flush()

        for patient in (radha, ganesan, lakshmi):
            consent_service.ensure_default_consents(db, patient, commit=False)

        db.add_all([
            # Care-team links are always created by the patient (§ doctor
            # relationships are patient-controlled), never by the doctor.
            DoctorAssignment(doctor_id=arun.id, patient_id=radha.id,
                             status="ACTIVE", is_primary=True, added_by_role="patient"),
            DoctorAssignment(doctor_id=arun.id, patient_id=lakshmi.id,
                             status="ACTIVE", is_primary=True, added_by_role="patient"),
            DoctorAssignment(doctor_id=meera.id, patient_id=ganesan.id,
                             status="ACTIVE", is_primary=True, added_by_role="patient"),
            CareAssignment(caregiver_id=priya.id, patient_id=radha.id),
            CareAssignment(caregiver_id=priya.id, patient_id=lakshmi.id),
            CareAssignment(caregiver_id=anitha.id, patient_id=ganesan.id),
        ])

        # ------------------------------------------------- conditions & allergies
        db.add_all([
            Diagnosis(patient_id=radha.id, name="Hypertension", diagnosed_on=days(900),
                      doctor_id=arun.id, is_critical=True,
                      source_type="DOCTOR_RECORDED"),
            Diagnosis(patient_id=radha.id, name="Type 2 Diabetes",
                      diagnosed_on=days(1400), doctor_id=arun.id, is_critical=True,
                      source_type="DOCTOR_RECORDED"),
            Diagnosis(patient_id=ganesan.id, name="COPD", diagnosed_on=days(1100),
                      doctor_id=meera.id, is_critical=True,
                      source_type="DOCTOR_RECORDED"),
            Diagnosis(patient_id=ganesan.id, name="Osteoarthritis",
                      diagnosed_on=days(700), doctor_id=meera.id,
                      source_type="DOCTOR_RECORDED"),
            Diagnosis(patient_id=lakshmi.id, name="Hypothyroidism",
                      diagnosed_on=days(500), doctor_id=arun.id,
                      source_type="DOCTOR_RECORDED"),
            Diagnosis(patient_id=lakshmi.id, name="Anaemia", diagnosed_on=days(200),
                      doctor_id=arun.id, source_type="DOCTOR_RECORDED"),
            Allergy(patient_id=radha.id, substance="Sulpha drugs",
                    reaction="Skin rash and itching", severity="severe",
                    source_type="DOCTOR_RECORDED"),
            Allergy(patient_id=ganesan.id, substance="Penicillin",
                    reaction="Swelling of the face", severity="severe",
                    source_type="DOCTOR_RECORDED"),
            Allergy(patient_id=lakshmi.id, substance="Dust mites",
                    reaction="Sneezing and watery eyes", severity="mild",
                    source_type="PATIENT_TEXT"),
        ])

        # ------------------------------------------------- baseline medications
        base_medications = [
            (radha, "Metformin", "500 mg", "Twice daily", ["08:00", "20:00"],
             arun.id, "After food"),
            (radha, "Atorvastatin", "10 mg", "At night", ["21:00"], arun.id, None),
            (ganesan, "Salbutamol inhaler", "2 puffs", "Twice daily",
             ["08:00", "20:00"], meera.id, None),
            (ganesan, "Paracetamol", "500 mg", "When required (SOS)", ["14:00"],
             meera.id, "After food"),
            (ganesan, "Vitamin D3", "60000 IU", "Once weekly", ["09:00"], meera.id,
             None),
            (lakshmi, "Levothyroxine", "50 mcg", "Every morning", ["07:00"], arun.id,
             "Empty stomach"),
            (lakshmi, "Calcium carbonate", "500 mg", "Once daily", ["13:00"],
             arun.id, "After food"),
        ]
        for patient, name, dose, frequency, times, prescriber, instruction in base_medications:
            medication_event = event(
                db, patient.id,
                event_type="MEDICATION",
                title=f"Medication: {name} — {dose} — {frequency}",
                content=(
                    f"{name} {dose} {frequency}."
                    + (f" Instruction: {instruction}." if instruction else "")
                    + " Recorded by the treating doctor."
                ),
                source_type="DOCTOR_RECORDED",
                event_date=days(random.Random(name).randint(120, 400)),
                author_role="doctor",
                author_name="Dr. Arun Kumar" if prescriber == arun.id
                else "Dr. Meera Raghavan",
                doctor_id=prescriber,
                confidence=1.0,
                tags=["medication"],
                extra={"medication_name": name, "dose": dose, "frequency": frequency},
            )
            db.add(
                Medication(
                    patient_id=patient.id, memory_event_id=medication_event.id,
                    name=name, dose=dose, frequency=frequency,
                    instruction=instruction, started_on=medication_event.event_date,
                    status="ACTIVE", prescriber_doctor_id=prescriber,
                    source_type="DOCTOR_RECORDED", confidence=1.0,
                    verification_status="NOT_REQUIRED", schedule_times=times,
                )
            )

        # ------------------------------------------------- consultations & history
        consultations = [
            (radha, arun, days(120), "Routine hypertension review",
             "BP 138/86. Stable on current therapy.",
             "Continue Amlodipine. Reduce salt intake. Review in 3 months."),
            (radha, arun, days(35), "Dizziness on standing",
             "BP 148/92 sitting, 126/78 standing. Postural drop noted.",
             "Rise slowly from bed. Monitor BP daily. Review in 2 weeks."),
            (ganesan, meera, days(58), "Breathlessness and cough",
             "Reduced air entry both bases. SpO2 94% on room air.",
             "Continue inhaler. Avoid dust. Breathing exercises daily."),
            (lakshmi, arun, days(75), "Thyroid review",
             "TSH elevated at 8.2 mIU/L. Weight gain and fatigue reported.",
             "Increase Levothyroxine review after 6 weeks. Repeat TSH."),
        ]
        for patient, doctor, when, reason, findings, advice in consultations:
            consult_event = event(
                db, patient.id,
                event_type="CONSULTATION",
                title=f"Consultation with {doctor.full_name}",
                content=(
                    f"Reason: {reason}\nFindings: {findings}\nAdvice: {advice}\n"
                    f"Doctor: {doctor.full_name}\nSpecialty: {doctor.specialty}\n"
                    f"Hospital/Clinic: {doctor.hospital}"
                ),
                source_type="DOCTOR_RECORDED",
                event_date=when,
                author_role="doctor",
                author_name=doctor.full_name,
                doctor_id=doctor.id,
                confidence=1.0,
                tags=["consultation"],
            )
            db.add(
                DoctorConsultation(
                    patient_id=patient.id, doctor_id=doctor.id,
                    memory_event_id=consult_event.id, consulted_on=when,
                    reason=reason, findings=findings, advice=advice,
                    follow_up_on=when + timedelta(days=21),
                    source_type="DOCTOR_RECORDED",
                )
            )

        # ------------------------------------------------- labs
        lab_rows = [
            (radha, "HbA1c", "7.4", "%", "4.0 - 5.6", "high", days(26),
             "Apollo Diagnostics"),
            (radha, "Fasting Blood Sugar", "132", "mg/dL", "70 - 100", "high",
             days(26), "Apollo Diagnostics"),
            (radha, "Haemoglobin", "11.8", "g/dL", "12.0 - 15.0", "low", days(26),
             "Apollo Diagnostics"),
            (radha, "Serum Creatinine", "1.1", "mg/dL", "0.6 - 1.2", "normal",
             days(26), "Apollo Diagnostics"),
            (ganesan, "Haemoglobin", "13.2", "g/dL", "13.0 - 17.0", "normal",
             days(60), "City Care Lab"),
            (lakshmi, "TSH", "8.2", "mIU/L", "0.4 - 4.0", "high", days(78),
             "Apollo Diagnostics"),
            (lakshmi, "Haemoglobin", "10.4", "g/dL", "12.0 - 15.0", "low", days(78),
             "Apollo Diagnostics"),
        ]
        for patient, test, value, unit, reference, flag, when, lab in lab_rows:
            lab_event = event(
                db, patient.id,
                event_type="LAB_RESULT",
                title=f"Lab result: {test}",
                content=f"{test}: {value} {unit} (reference {reference}) — {flag}.",
                source_type="DOCTOR_DOCUMENT",
                event_date=when,
                author_role="doctor",
                author_name=lab,
                confidence=0.97,
                severity="attention" if flag in {"high", "low"} else "normal",
                tags=["lab"],
            )
            db.add(
                LabResult(
                    patient_id=patient.id, memory_event_id=lab_event.id,
                    test_name=test, value=value, unit=unit,
                    reference_range=reference, flag=flag, tested_on=when,
                    lab_name=lab,
                )
            )

        db.add(
            HospitalVisit(
                patient_id=ganesan.id, hospital="City Care Clinic",
                reason="Acute exacerbation of COPD",
                admitted_on=days(62), discharged_on=days(58),
                summary="Treated with nebulisation and oral steroids. Discharged stable.",
                doctor_id=meera.id,
            )
        )
        event(
            db, ganesan.id,
            event_type="HOSPITAL_VISIT",
            title="Hospital admission: City Care Clinic",
            content=(
                "Admitted for acute exacerbation of COPD. Treated with "
                "nebulisation, oral steroids and oxygen support. Discharged after "
                "four days in stable condition."
            ),
            source_type="DOCTOR_RECORDED",
            event_date=days(62),
            author_role="doctor",
            author_name=meera.full_name,
            doctor_id=meera.id,
            confidence=1.0,
            severity="attention",
            tags=["hospital"],
        )

        # ------------------------------------------------- caregiver observations
        observation_rows = [
            (radha, priya, days(3), "meal", "Ate about half of breakfast. "
             "Said she had no appetite.", "normal"),
            (radha, priya, days(2), "general",
             "Complained of dizziness when getting up from bed at 09:15.",
             "attention"),
            (radha, priya, days(1), "sleep", "Slept well through the night. "
             "No night-time wandering.", "normal"),
            (lakshmi, priya, days(2), "mood",
             "Low mood in the afternoon. Participated in group activity after tea.",
             "normal"),
            (lakshmi, priya, days(1), "general",
             "Reported feeling cold and tired through the morning.", "attention"),
            (ganesan, anitha, days(4), "general",
             "Breathing comfortable at rest. Used inhaler without help.", "normal"),
            (ganesan, anitha, days(1), "mobility",
             "Knee pain while climbing stairs. Needed support on the right side.",
             "attention"),
        ]
        for patient, caregiver, when, category, text, severity in observation_rows:
            observation_event = event(
                db, patient.id,
                event_type="OBSERVATION",
                title=f"Caregiver observation ({category})",
                content=text,
                source_type="CAREGIVER_RECORDED",
                event_date=when,
                author_role="caregiver",
                author_name=caregiver.full_name,
                confidence=1.0,
                severity=severity,
                tags=["observation", category],
            )
            db.add(
                CaregiverObservation(
                    patient_id=patient.id, caregiver_id=caregiver.id,
                    memory_event_id=observation_event.id, category=category,
                    observation=text, severity=severity, observed_at=when,
                )
            )

        db.commit()

        # ------------------------------------------------- closed previous shift
        yesterday = (NOW - timedelta(days=1)).strftime("%Y-%m-%d")
        previous_shift = Shift(
            facility_id=home.id, caregiver_id=priya.id, shift_code="NIGHT",
            shift_date=yesterday, start_time="22:00", end_time="06:00",
            status="CLOSED", assigned_patient_ids=[radha.id, lakshmi.id],
            created_at=NOW - timedelta(days=1),
        )
        db.add(previous_shift)
        db.flush()
        for patient in (radha, lakshmi):
            for medication in db.query(Medication).filter(
                Medication.patient_id == patient.id
            ):
                if "21:00" in (medication.schedule_times or []):
                    db.add(
                        MedicationAdministration(
                            patient_id=patient.id, medication_id=medication.id,
                            caregiver_id=priya.id, shift_id=previous_shift.id,
                            scheduled_time="21:00", scheduled_date=yesterday,
                            status="Administered",
                            administered_at=NOW - timedelta(days=1, hours=1),
                        )
                    )
        db.commit()

        # ------------------------------------------------- voice + text entries
        radha_principal = Principal(radha_user, radha)
        ganesan_principal = Principal(ganesan_user, ganesan)

        ingestion_service.ingest_voice(
            db, radha,
            transcript=(
                "I met Dr Arun Kumar last Monday and he changed my blood pressure "
                "medicine. Since then I feel dizziness when I stand up in the "
                "morning."
            ),
            actor=radha_principal,
            duration_seconds=11.4,
            recognition_confidence=0.88,
        )

        ingestion_service.ingest_text(
            db, ganesan,
            "I visited Dr. Meera Raghavan on 12 August because of breathlessness. "
            "She asked me to continue the Salbutamol inhaler twice daily and to "
            "avoid dust.",
            ganesan_principal,
        )

        # ------------------------------------------------- documents through OCR
        folder = STORAGE_DIR / "seed"
        fixtures = [
            (radha, radha_principal, "Doctor_Handwritten_Note.png",
             HANDWRITTEN_PRESCRIPTION.format(date=days(30).strftime("%d/%m/%Y")),
             True),
            (radha, radha_principal, "Apollo_Lab_Report.png",
             LAB_REPORT.format(date=days(26).strftime("%d/%m/%Y")), False),
            (ganesan, ganesan_principal, "Discharge_Summary_City_Care.png",
             DISCHARGE_SUMMARY.format(date=days(58).strftime("%d/%m/%Y")), False),
            (lakshmi, Principal(lakshmi_user, lakshmi),
             "Handwritten_Prescription_Thyroid.png",
             HANDWRITTEN_THYROID.format(date=days(75).strftime("%d/%m/%Y")), True),
        ]

        results = []
        for patient, actor, filename, body, handwritten in fixtures:
            source = render_document(folder, filename, body, handwritten)
            stored = document_service.store_upload(
                patient.id, source.name, source.read_bytes()
            )
            # Carry the ground-truth sidecar next to the stored copy.
            sidecar = source.with_suffix(source.suffix + ".groundtruth.txt")
            if sidecar.exists():
                Path(stored["path"] + ".groundtruth.txt").write_text(
                    sidecar.read_text(encoding="utf-8"), encoding="utf-8"
                )
            document = document_service.create_document(
                db, patient.id,
                filename=source.name,
                stored_path=stored["path"],
                mime_type="image/png" if source.suffix == ".png" else "text/plain",
                size_bytes=stored["size"],
                uploaded_by_user_id=actor.id,
                document_type=document_service.guess_document_type(source.name),
                is_handwritten=handwritten,
            )
            result = ingestion_service.ingest_document(
                db, patient, document, actor, declared_handwritten=handwritten
            )
            results.append((source.name, result))

        db.commit()

        # ------------------------------------------------- report
        print("\n" + "=" * 74)
        print("  DEMO DATA SEEDED")
        print("=" * 74)
        for name, result in results:
            ocr = result.get("ocr", {})
            print(
                f"  {name:<38} "
                f"{'handwritten' if ocr.get('handwriting_detected') else 'printed':<12} "
                f"confidence {round((ocr.get('overall_confidence') or 0) * 100)}%  "
                f"→ {len(result.get('verification_tasks', []))} verification task(s)"
            )
        from services import verification_service

        stats = verification_service.queue_stats(db)
        print("\n  Reviewer verification queue: "
              f"{stats['pending']} pending ({stats['high_priority']} high priority)")
        print("\n  Demo accounts (password for all: Demo@123)")
        print("  " + "-" * 70)
        for email, label in [
            ("patient@demo.health", "Patient / Guardian — Radha Krishnan, 72"),
            ("patient2@demo.health", "Patient / Guardian — Ganesan Murugan, 78"),
            ("patient3@demo.health", "Patient / Guardian — Lakshmi Narayanan, 68"),
            ("doctor@demo.health", "Doctor — Dr. Arun Kumar, Cardiology"),
            ("doctor2@demo.health", "Doctor — Dr. Meera Raghavan, General Medicine"),
            ("caregiver@demo.health", "Caregiver — Priya Sharma (Old Age Home)"),
            ("caregiver2@demo.health", "Caregiver — Anitha Raj (Individual)"),
            ("reviewer@demo.health", "Reviewer — Kavitha Menon"),
        ]:
            print(f"  {email:<26} {label}")
        print()
        print("  pharmacist@demo.health also signs in to the Reviewer account")
        print("  (the role was renamed Pharmacist -> Reviewer).")
        print("=" * 74 + "\n")
    finally:
        db.close()


if __name__ == "__main__":
    # --keep      add to an existing database instead of rebuilding it
    # --if-empty  seed only when the database has no users (safe on every boot)
    seed(
        reset="--keep" not in sys.argv and "--if-empty" not in sys.argv,
        only_if_empty="--if-empty" in sys.argv,
    )
