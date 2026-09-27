# AI-Agent-Powered Persistent Health Memory Layer for Elderly Patients

A persistent, longitudinal, **consent-aware**, **provenance-preserving** health-memory
layer that turns fragmented elderly-patient information — typed notes, voice diaries,
scanned reports and handwritten prescriptions — into trustworthy, reusable context for
doctors, caregivers, reviewers and patients.

The chatbots are not the product. The memory is. The four AI agents are interfaces and
reasoning layers on top of it.

---

## 1. The pipeline

```text
                    PATIENT / GUARDIAN
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
            TEXT         VOICE     SCAN & UPLOAD
              │            │            │
              │       Speech-to-Text   OCR
              └────────────┼────────────┘
                           ▼
                  DATA NORMALIZATION
                           ▼
                  CONFIDENCE ANALYSIS
              ┌────────────┴────────────┐
        HIGH CONFIDENCE           LOW / MEDIUM
              │                         ▼
              │                  VERIFICATION QUEUE
              │                         ▼
              │                  REVIEWER DASHBOARD
              └────────────┬────────────┘
                           ▼
                  VERIFIED HEALTH MEMORY
                           ▼
                       RAG INDEX
          ┌────────────────┼─────────────────┐
          ▼                ▼                 ▼
       DOCTOR          CAREGIVER         REVIEWER
       AGENT             AGENT              AGENT
          └────────────────┼─────────────────┘
                           ▼
                    PATIENT MEMORY CHATBOT
                           ▼
                    ANSWER + EVIDENCE
```

The system's priority order is deliberate:

```text
PERSISTENCE → PROVENANCE → OCR CONFIDENCE → HUMAN VERIFICATION →
CONSENT → AUTHORIZATION → RAG → ROLE-SPECIFIC AI → EVIDENCE-BACKED RESPONSE
```

---

## 2. Quick start

Two terminals. No API key required — the system is fully functional offline.

### Backend

The application stores everything in **MongoDB**. Point `MONGODB_URI` at your
deployment — a local server, a replica set, or an Atlas cluster:

```bash
export MONGODB_URI="mongodb://localhost:27017"     # or your Atlas SRV string
export MONGODB_DB_NAME="health_memory"
```

Never put credentials in the repository. Copy `.env.example` to `backend/.env`
(git-ignored) and set them there, or export them in your shell.

If `MONGODB_URI` cannot be reached, the backend falls back to a local
file-backed store under `backend/.mongo-local/` so a fresh checkout still runs;
it says so loudly in the log. Set `MONGODB_LOCAL_FALLBACK=0` in production so a
misconfigured URI fails instead of quietly writing somewhere else.

```bash
cd backend
python -m venv venv

# Windows
venv\Scripts\activate
# Linux / macOS
source venv/bin/activate

pip install -r requirements.txt
python seed.py                       # creates the collections and demo data
uvicorn main:app --reload            # http://127.0.0.1:8000  (docs at /docs)
```

**Seed before you serve.** MongoDB starts empty, so a server run against an
unseeded database shows every dashboard working and completely blank — no demo
logins, no patients on the caregiver screen. The backend now says so at startup
and reports it at `GET /api/health` under `database`:

```json
{ "store": "mongodb", "persistent": true, "seeded": true,
  "counts": { "users": 8, "patients": 3, "memory_events": 60 } }
```

Seeding is safe to repeat:

```bash
python seed.py              # rebuild the demo environment from scratch
python seed.py --if-empty   # seed only when the database has no users
python seed.py --keep       # refuses rather than duplicating existing records
```

### Frontend

```bash
cd frontend
npm install
npm run dev                          # http://localhost:5173
```

Open <http://localhost:5173> — you land on the public homepage. Use **Get Started**
to register, or **Login** with one of the seeded accounts listed in section 4.

### Verify the whole thing works

```bash
cd backend
python seed.py && python e2e_check.py
```

`e2e_check.py` drives the complete 17-step demo flow plus the security checks,
the patient-controlled care team, Tamil and mixed-language entries, and MongoDB
persistence through the real API, and prints a pass/fail report (~62 checks; the
exact count moves by one with the OCR run).

### Migrating an existing SQLite installation

The application no longer uses SQLite. An installation that already holds data
can carry it across — including the Pharmacist → Reviewer rename:

```bash
cd backend
python migrate_sqlite_to_mongo.py                       # ./legacy_sqlite/health_memory.db
python migrate_sqlite_to_mongo.py --sqlite /path/to/your.db --drop-existing
```

It reads the old file with the standard library's `sqlite3` module only, keeps
every integer id, and reports any column it could not map rather than dropping
it silently.

---

## 3. The public homepage

`/` is the public landing page — a full healthcare product site: hero, value
propositions, the four-step workflow, the three ways to add information, the
retrieval architecture explained in plain language, the four roles, the
handwriting/verification differentiator, an elder-care section, a mock Emergency
Health Card and a closing call to action.

Two buttons lead into the application: **Login** goes to `/login`, **Get Started**
goes to `/register`. Signing in is unchanged.

**No demo accounts or credentials appear anywhere in the interface.** The
homepage, the sign-in screen and the footer expose no account cards, no
quick-login buttons and no passwords. The seeded fictional records still exist in
the database for development and testing — their credentials are in the table
below and in the `python seed.py` console output.

All homepage artwork is original inline SVG drawn for this project: no stock
photography, no third-party assets and nothing to license.

---

## 4. Demo credentials

*For developers and evaluators. These are not shown in the running application.*

Password for every account: **`Demo@123`**

| Email | Role | Who |
|---|---|---|
| `patient@demo.health` | Patient / Guardian | Radha Krishnan, 72 — has the low-confidence handwritten note |
| `patient2@demo.health` | Patient / Guardian | Ganesan Murugan, 78 — home care |
| `patient3@demo.health` | Patient / Guardian | Lakshmi Narayanan, 68 — medium-confidence prescription |
| `doctor@demo.health` | Doctor | Dr. Arun Kumar, Cardiology |
| `doctor2@demo.health` | Doctor | Dr. Meera Raghavan, General Medicine |
| `caregiver@demo.health` | Caregiver | Priya Sharma — Old Age Home (shift-based) |
| `caregiver2@demo.health` | Caregiver | Anitha Raj — Individual caregiver |
| `reviewer@demo.health` | Reviewer | Kavitha Menon, MedPlus Clinical Review Desk |
| `pharmacist@demo.health` | Reviewer | the pre-rename address; signs in to the same Reviewer account |

All patient data is fictional.

---

## 5. The demo flow (what to click)

1. **Sign in as the patient.** The Health Overview shows medications, allergies,
   conditions, labs and alerts — each carrying its source.
2. **Add Health Data** offers exactly three routes: **TEXT**, **VOICE**,
   **SCAN & UPLOAD**. All three enter the same pipeline.
3. Try TEXT: *"I visited Dr. Kumar on 10 August because of dizziness. He asked me to
   continue my blood pressure medicine."* The doctor, medication and symptom are
   extracted, the entry is stored as **Patient/Guardian entered**, and the record is
   routed to Dr. Kumar.
4. Open **Documents → Doctor_Handwritten_Note.png**. It was read by the handwriting
   engine at **54 %** confidence.
5. **Sign in as the reviewer.** The Verification Queue contains that reading:
   `Medication: "Amlodipine" — 54 % — HIGH PRIORITY`. Open it: the original page, the
   OCR text, the per-field confidence and the patient's medication context are all
   there. Correct it to `Amlodipine` and save.
6. **Sign in as the doctor.** The patient appears in *"New health memory routed to
   you"*. Click **Generate Visit Summary** — a longitudinal, evidence-backed draft
   appears, editable, clearly labelled AI-generated, and saved only when you say so.
7. **Sign in as the caregiver.** Choose **Old Age Home** → **Morning Shift** → your
   residents → **Start shift**. Medication rounds and care tasks are generated for the
   shift hours. Record a dose, add an observation, then **Generate Shift Handover**.
8. Ask each of the four chatbots its quick-action questions and open **"Why am I seeing
   this?"** under any answer.

---

## 6. Architecture

```text
elder-health-memory/
├── backend/                 FastAPI + MongoDB (PyMongo)
│   ├── config.py            ← every threshold and constant lives here
│   ├── database.py          MongoDB connection, session and query layer
│   ├── mongo_orm.py         document mapper: columns, relationships, filters
│   ├── models.py            persistent health-memory schema (31 collections)
│   ├── auth.py              token auth + role guards
│   ├── routes/              13 route modules
│   ├── ocr/                 OCRService ├── PrintedOCR └── HandwritingOCR
│   ├── rag/                 chunker · embeddings · retriever · context_builder
│   ├── agents/              memory · patient · doctor · caregiver · reviewer
│   │                        + ai_provider (MockAIProvider / LLMProvider)
│   ├── services/            ingestion · verification · consent · authorization
│   │                        · memory · document · summarization · chatbot · audit
│   ├── seed.py              fictional demo data, run through the real pipeline
│   ├── migrate_sqlite_to_mongo.py   one-off import from a legacy SQLite file
│   └── e2e_check.py         end-to-end verification of the demo flow
└── frontend/                React 18 + Vite + React Router
    └── src/
        ├── i18n/            English/Tamil dictionary, provider, language switch
        ├── pages/           Home (public landing) · Login · Register
        │                    · 4 role dashboards
        ├── components/      home · common · health-memory · ingestion · chatbot
        │                    · consent · emergency · doctor · caregiver · reviewer
        ├── styles/          home.css (landing page, scoped under `.home`)
        ├── services/        API clients
        ├── agents/          per-role agent presentation
        └── utils/           permissions · formatters · constants
```

### Technology

| Layer | Choice | Why |
|---|---|---|
| API | FastAPI | typed request/response, automatic OpenAPI at `/docs` |
| Database | MongoDB via PyMongo, with a thin document mapper | one collection per entity, integer ids, no ORM to fight |
| Languages | English + தமிழ், keyed by the English source string | a missing translation falls back to English instead of breaking |
| OCR | pytesseract when installed, else a labelled demo engine | works on any machine |
| Embeddings | local hashed bag-of-words with character shingles | no API key, no model download, OCR-noise tolerant |
| AI | `MockAIProvider` / `LLMProvider` behind one interface | fully functional with no key |
| UI | React + Vite, hand-written CSS design system | no component library to fight with |

---

## 7. Persistent health memory

`MemoryEvent` is the spine. Every clinically meaningful fact — whoever produced it —
becomes a memory event carrying full provenance:

```text
source_type   PATIENT_TEXT | PATIENT_VOICE | DOCTOR_DOCUMENT | SCANNED_DOCUMENT
              | HANDWRITTEN_DOCUMENT | OCR | DOCTOR_RECORDED | CAREGIVER_RECORDED
              | REVIEWER_VERIFIED | AI_GENERATED

trust_level   Patient Reported | AI Extracted | OCR Extracted
              | Doctor Recorded | Reviewer Verified | Caregiver Recorded

confidence    0.00 – 1.00
verification  PENDING_VERIFICATION | VERIFIED | CORRECTED | REJECTED | NOT_REQUIRED
consent_scope which consent scope controls visibility
```

Specialised tables (`Medication`, `LabResult`, `Prescription`, `Diagnosis`, `Allergy`,
`HospitalVisit`, `DoctorConsultation`, `CaregiverObservation`, `VoiceEntry`, `Document`,
`OCRResult`, `VerificationTask`, `VerificationResult`, `Consent`,
`MedicationAdministration`, `Shift`, `ShiftHandover`, `AuditEvent`) hang off memory
events, so structured data never loses the link back to its source.

**A patient statement never becomes a confirmed diagnosis.** An OCR reading never
becomes a doctor-confirmed fact. Both are visible everywhere they are used.

---

## 8. OCR and handwriting

```text
OCRService
 ├── PrintedOCR       native PDF text · pytesseract · demo engine
 └── HandwritingOCR   pytesseract (calibrated down) · demo engine
```

Handwriting is detected from three signals, in order: an explicit declaration by the
uploader, filename hints, and — when Pillow is available — an ink-distribution
heuristic over the image (printed text has dense, regular rows; handwriting is sparse
and uneven). The UI always states which engine ran and why:

```text
Document Type:            Handwritten Doctor Report
OCR Status:               Processed
Recognition Confidence:   54%
```

**Real OCR is optional.** With `tesseract` installed, real recognition runs. Without it,
the engines fall back to a clearly-labelled demo mode that reproduces realistic
recognition noise — dropped strokes, `i`/`l` and `o`/`0` confusions — and the confidence
that goes with it. Either way the rest of the pipeline is identical.

Because handwriting rarely yields a clean drug name, medication extraction matches
**approximately** against a drug lexicon and *lowers its confidence by the similarity
gap*: `"Amlod!pine"` resolves to `Amlodipine`, and the raw reading is preserved so the
reviewer can see what was actually on the page.

Install real OCR:

```bash
# Ubuntu/Debian
sudo apt install tesseract-ocr
# macOS
brew install tesseract
# Windows: https://github.com/UB-Mannheim/tesseract/wiki
```

---

## 9. Confidence and the verification rule

Every extracted field carries its own score:

```text
Medication: Amlodipine     54%   ← clinically important, below threshold
Dose:       5 mg           62%
Frequency:  Once daily     54%
Doctor:     Dr. Arun Kumar 66%   ← not clinically critical
```

Thresholds live in exactly one place — `backend/config.py`, overridable by environment
variable:

```python
HIGH_CONFIDENCE_THRESHOLD  = 0.85
MEDIUM_CONFIDENCE_THRESHOLD = 0.60
```

| Band | Range | Behaviour |
|---|---|---|
| High | ≥ 85 % | accepted into health memory, provenance preserved |
| Medium | 60 – 84 % | `Needs Verification` → reviewer queue (normal) |
| Low | < 60 % | `High Priority Verification` → reviewer queue (urgent) |

**The reviewer does not receive every record.** A task is created only when *both*
conditions hold:

```text
IF   OCR confidence < HIGH_CONFIDENCE_THRESHOLD
AND  the field is clinically important
     (medication name, dose, frequency, prescription instruction,
      medication change, allergy, critical instruction)
THEN create a reviewer verification task
```

A doctor's name read at 66 % does not interrupt a reviewer. A dose read at 66 % does.

---

## 10. Reviewer verification workflow

The reviewer sees the original document, the OCR output, the confidence, every
extracted field, and the patient's existing medication context (consent-checked). They
can **confirm**, **correct**, **reject** or add a **clarification**.

Nothing is overwritten. Every resolution preserves:

```text
Original OCR      "Amlodipine"
Original confidence  54%
Corrected value   "Amlodipine 5 mg"
Reviewer        Kavitha Menon
Verification time 10 Sep 2026, 13:16
```

Statuses: `PENDING_VERIFICATION → VERIFIED | CORRECTED | REJECTED`.

A verified value is pushed into the structured medication record, the memory event is
re-indexed as `Reviewer Verified`, and only then does it become trusted retrieval
context. A rejected reading stays in the record for audit but is excluded from
retrieval entirely.

Until a medication is verified, the caregiver dashboard **refuses to record it as
administered** — the API returns 409, not just a UI warning.

---

## 11. RAG

Retrieval is not "dump the database into the prompt". Filters run **before** scoring, in
this order:

```text
1. patient isolation        WHERE patient_id = ?
2. authentication           route dependency
3. role authorization       care relationship required
4. consent restrictions     patient-granted scopes only
5. verification status      REJECTED sources excluded
6. relevance                0.62 semantic + 0.38 lexical
7. recency                  exponential decay, 120-day half-life
```

Final score = `relevance × 0.60 + recency × 0.22 + trust × 0.18`, where trust reflects
verification status and confidence. Unauthorised records are removed from the candidate
set — the model is never asked to ignore something it can see.

Indexed sources: doctor reports, consultations, prescriptions, lab results, hospital
documents, patient text, voice transcripts, caregiver observations, medication events,
verified OCR results and emergency information. Every chunk keeps
`patient_id · source_id · source_type · date · author · doctor · confidence ·
verification_status · consent_scope`.

Embeddings are a local hashed bag-of-words with character 4-gram shingles, so
`Amlodipme` still lands near `Amlodipine`. Swapping in a hosted embedding model means
replacing `rag/embeddings.py::embed()` and nothing else.

---

## 12. The four dashboards

### Patient / Guardian
Health Overview · My Health Memory Timeline · Add Health Data (Text / Voice / Scan) ·
Documents · **My Doctors** · Consent Control Center · Voice Health Diary ·
Emergency Health Card · My Health Memory AI. Rendered at a larger type scale with
big primary buttons and plain language throughout.

#### My Doctors — the patient owns the relationship

The patient decides who treats them. From this screen they search the directory,
add a doctor, keep several at once, choose which is primary, and remove any of
them. Adding a doctor is what puts the patient on that doctor's dashboard;
removing takes them off it.

There is no code path anywhere in the backend that lets a doctor add, remove or
alter a care relationship — including their own. Every `/api/care-team/*` route
is guarded by `require_roles("patient")` and then by `require_patient_access`, so
a doctor calling any of them gets a 403.

A doctor named in a scanned record is **suggested**, not assigned: routing records
the doctor on the document and offers them to the patient, and they receive
nothing until the patient adds them.

**Removing a doctor never deletes clinical history.** The relationship row is kept
with `status="REMOVED"`, and every memory event, prescription, medication,
consultation, lab result, diagnosis, hospital visit and document that recorded
that doctor still points at them. Removal withdraws ongoing access and nothing
else; the doctor stays listed under "Doctors you have removed" with a count of
the records they contributed, and can be added again later.

### Doctor
Patient Selection (only patients who added this doctor) · Patient Health
Overview · One-click Visit Summary · Clinical Health Memory Timeline · Caregiver
Insight Feed · Doctor Documents · Clinical Insights · Clinical Health Memory AI.
The doctor has no control over which patients appear here.

### Caregiver / Old Age Home
Starts with a care-setting choice:

```text
Care Type
  ○ Individual Caregiver      one patient, continuous care
  ○ Old Age Home              multiple residents, shift-based
```

Then Patient Selection · Shift Management · Medication Administration Verification ·
Daily Care Tasks · Caregiver Insight Feed · Shift Handover AI · Patient Health
Overview · Alerts · Care Companion AI.

Shifts (configurable in `config.py`):

```text
Morning    06:00 – 14:00
Afternoon  14:00 – 22:00
Night      22:00 – 06:00
```

Starting a shift generates the medication rounds and care tasks that fall inside those
hours. Each recorded dose, observation and handover becomes persistent health memory
attributed to the caregiver, the shift and the time.

### Reviewer
Verification Queue · Low-Confidence Medical Data Review · OCR Verification ·
Medication Overview · Medication History · Prescription History · Medication Insights ·
Medication Memory AI.

---

### Language — English and தமிழ்

Every interface string is bilingual. The switch sits in the dashboard top bar,
the public navigation, and both auth screens, so a language can be chosen before
signing in; the choice is remembered per browser and dates and relative times
follow it.

Translation is keyed by the English source string — a component reads
`t('Add doctor')`, and `src/i18n/ta.js` maps that string to Tamil. There are no
invented key names to keep in sync, and a string missing from the dictionary
renders in English rather than as a blank or a key, so a gap degrades to
readable English instead of a broken screen.

Clinical content is never translated. Medication names, memory event text,
AI-generated drafts, OCR output and anything a user typed are patient data and
are shown exactly as recorded.

#### Voice in Tamil, English, and the two mixed

The voice diary offers three speaking modes: English (`en-IN`), Tamil (`ta-IN`),
and Tamil + English. The Web Speech API accepts one recognition locale at a
time, so mixed speech uses the Tamil recogniser, which keeps embedded English
words rather than discarding them.

`services/language_service.py` detects the language of any patient entry — typed
or spoken — and produces a plain English *assisted reading* of Tamil and mixed
text so extraction can work and an English-reading clinician can follow the
entry:

> `எனக்கு இரண்டு நாளாக தலை வலிக்குது` → *I have had a headache for two days.*

It is a reviewable phrase table, not a translation service: every mapping is a
fixed pair, so the reading is deterministic, works offline, and cannot invent a
clinical claim the patient did not make. Anything not in the table stays in the
patient's own words.

The patient's original wording is always what is stored. The reading is carried
alongside it as provenance (`assisted_reading` on the memory event), the entry
keeps `trust_level = "Patient Reported"`, and its confidence is capped at 0.88 to
say plainly that a reading is an aid and not a certainty. **A spoken symptom
never becomes a diagnosis** — it enters exactly the same human-review workflow as
any other patient entry, and only a doctor's record or a verified document can
make it more than reported.

---

## 13. The four chatbots

Four distinct agents, four system prompts, four registers — not one generic bot.

| Agent | Role | Register |
|---|---|---|
| **My Health Memory Assistant** | Patient | short sentences, everyday words, no jargon |
| **Clinical Health Memory Assistant** | Doctor | structured clinical sections |
| **Care Companion** | Caregiver | actionable, shift-focused, escalation-aware |
| **Medication Memory Assistant** | Reviewer | precise about readings, doses and confidence |

Each answer is composed by its role agent **directly from the retrieved records**, then
rendered by the AI provider. Every answer carries a *"Why am I seeing this?"* panel
listing the sources used, their dates, trust levels and verification status.

### AI provider

```text
AIProvider
 ├── MockAIProvider   deterministic, grounded, no API key
 └── LLMProvider      hosted model when LLM_API_KEY is set
```

`MockAIProvider` does not emit filler. It returns the grounded draft the role agent
assembled from real retrieved memory, which is why the demo is fully meaningful with no
key at all. `LLMProvider` sends the same context and draft to the model with strict
safety rules, and falls back to the grounded draft on any error.

---

## 14. Security model

* PBKDF2-SHA256 password hashing (120 000 iterations, per-user salt)
* HMAC-SHA256 signed bearer tokens with expiry
* Role-based route guards (`require_roles(...)`)
* **Patient-level authorization**: every patient-scoped route resolves the care
  relationship first — patient A cannot read patient B, and a doctor with no
  relationship gets 403 plus an `ACCESS_DENIED` audit entry
* **Consent enforced before RAG context is constructed**, never after
* File validation by extension and size; filenames sanitised before storage
* Input length limits and null-byte stripping
* No API keys in source — everything via environment variables
* Friendly errors only: raw exceptions are logged server-side and never returned

### Audit log

`LOGIN · REGISTER · DOCUMENT_UPLOAD · OCR_PROCESSING · HEALTH_MEMORY_CREATE ·
HEALTH_MEMORY_MODIFY · DOCTOR_ROUTING · CONSENT_GRANT · CONSENT_REVOKE ·
RAG_RETRIEVAL · AI_SUMMARY_GENERATION · MEDICATION_VERIFICATION ·
VERIFICATION_VERIFY/CORRECT/REJECT · SHIFT_HANDOVER_GENERATION · SHIFT_START ·
EMERGENCY_ACCESS · CHAT_QUERY · ACCESS_DENIED`

Readable at `GET /api/audit` (patients see only their own).

---

## 15. Consent

The patient (or guardian) controls access per **recipient** and per **scope**:

| Recipients | Scopes |
|---|---|
| Doctor · Caregiver · Old Age Home · Reviewer · Emergency access | Full Health Memory · Medication Information · Emergency Information · Recent History · Caregiver Notes · Documents · Voice Diary |

Each scope maps to the event types it covers, so revoking *Recent History* removes
consultations, diagnoses, symptoms and labs from every retrieval path — including the
doctor's chatbot and visit summary — immediately. Every change writes a consent-history
entry and an audit event.

By default caregivers are **not** granted the voice diary; the API returns 403 even if
the UI were to ask.

---

## 16. API

```text
POST   /api/auth/login                 POST /api/auth/register    GET /api/auth/me

GET    /api/patients                   GET  /api/patients/{id}
GET    /api/patients/{id}/overview

# Care team — patient-controlled. Every route requires the patient role.
GET    /api/care-team/search           GET  /api/care-team/{patient_id}
POST   /api/care-team/{pid}/doctors    DELETE /api/care-team/{pid}/doctors/{did}
POST   /api/care-team/{pid}/doctors/{did}/primary

POST   /api/ingestion/text             POST /api/ingestion/voice
POST   /api/ingestion/upload

POST   /api/ocr/process                GET  /api/ocr/{document_id}
GET    /api/ocr/engines

GET    /api/memory/{patient_id}        POST /api/memory
GET    /api/memory/{patient_id}/timeline
GET    /api/memory/event/{event_id}

GET    /api/documents/patient/{id}     GET  /api/documents/{id}
GET    /api/documents/{id}/file

GET    /api/verification/queue         GET  /api/verification/{id}
POST   /api/verification/{id}/verify
POST   /api/verification/{id}/correct
POST   /api/verification/{id}/reject

GET    /api/consent/meta               GET  /api/consent/{patient_id}
POST   /api/consent                    GET  /api/consent/{id}/history

GET    /api/emergency/{patient_id}
POST   /api/voice/entry                GET  /api/voice/{patient_id}

GET    /api/doctor/routing             GET  /api/doctor/insights/{id}
GET    /api/doctor/caregiver-feed/{id}
POST   /api/doctor/visit-summary       POST /api/doctor/visit-summary/save
GET    /api/doctor/visit-summaries/{id}

GET    /api/caregiver/config           POST /api/caregiver/care-type
POST   /api/caregiver/shift/start      GET  /api/caregiver/shift/{id}
GET    /api/caregiver/shifts           POST /api/caregiver/medication/verify
POST   /api/caregiver/observation      POST /api/caregiver/task/{id}
GET    /api/caregiver/insights
POST   /api/caregiver/shift-handover   POST /api/caregiver/shift-handover/save
GET    /api/caregiver/handovers

GET    /api/reviewer/queue           GET  /api/reviewer/patients
GET    /api/reviewer/medications/{id}
GET    /api/reviewer/insights

POST   /api/chat/patient               POST /api/chat/doctor
POST   /api/chat/caregiver             POST /api/chat/reviewer
GET    /api/chat/agents

GET    /api/health                     GET  /api/system/config   GET /api/audit
```

Interactive docs: <http://127.0.0.1:8000/docs>

---

## 17. AI safety

The system will not, by construction:

* invent a medication, dose, diagnosis, date, result or doctor
* fabricate a doctor account — an unregistered prescriber is recorded as
  `External / Not Registered`
* silently change medical information — corrections sit *beside* the original
* present OCR uncertainty as fact
* prescribe or alter treatment
* let an AI-generated summary become the medical record: the doctor reviews, edits and
  saves it, and the saved copy is stored as `Doctor Recorded` with its AI origin noted
* let a caregiver administer medication that is still awaiting verification

---

## 18. Troubleshooting

| Symptom | Fix |
|---|---|
| `Unable to reach the health memory service` | the backend is not running — start `uvicorn main:app --reload` in `backend/` |
| Empty dashboards | run `python seed.py` in `backend/` |
| OCR confidence looks different from the README | you have a different tesseract version, or none — the behaviour and thresholds are identical, only the exact percentages move |
| `401` after a while | tokens expire after 12 hours; sign in again |
| Port already in use | `uvicorn main:app --port 8001` and set `VITE_API_BASE` accordingly |
| Every dashboard is empty / no demo login works | the database has not been seeded — run `python seed.py` in `backend/`. Check `GET /api/health` → `database.seeded` |
| Caregiver dashboard shows "No patients available" | either the database is unseeded (above), or that caregiver genuinely has no care assignment — the list is produced by the backend from `care_assignments` and facility membership, never by the browser |
| Seeded data is not visible to the server | you are on the in-memory fallback, which is process-local: seeding in one terminal cannot reach a server in another. Install `montydb`, or set `MONGODB_URI` |
| `MongoDB at MONGODB_URI is unreachable` in the log | the backend fell back to the local development store — start MongoDB, or set `MONGODB_URI`; set `MONGODB_LOCAL_FALLBACK=0` to make this an error instead |
| Data disappears on restart | the in-memory fallback is active because neither MongoDB nor the file-backed store was available — install `montydb`, or point `MONGODB_URI` at a real server |
| Reset everything | delete `backend/.mongo-local/` (or drop the MongoDB database) and `backend/storage/`, then `python seed.py` |
| Carrying data over from the old SQLite build | `python migrate_sqlite_to_mongo.py` in `backend/` |

---

## 19. Validation

`backend/e2e_check.py` exercises the whole system through the HTTP API — patient login,
all three ingestion routes, OCR and handwriting, the verification-routing rule, the
reviewer correction with provenance preserved, doctor routing, RAG retrieval, visit
summary generation and saving, caregiver shift creation, medication administration,
shift handover, all four chatbots, and the security boundaries (patient isolation,
unauthenticated access, consent revocation, voice-diary scope, audit trail).

It also covers the patient-controlled care team (search, add, multiple doctors,
remove, re-add; a doctor refused on every write; full medical history preserved
after removal), Tamil and mixed Tamil-English entries (detection, assisted
English reading, and that a spoken symptom stays patient-reported rather than
becoming a diagnosis), and MongoDB persistence.

```text
62 passed, 0 failed
```

(The total moves by one between runs because one check depends on the OCR
confidence produced for a seeded document; the failure count stays at zero.)

A browser pass over the homepage, both auth screens and all four dashboards — each
in English and Tamil, at desktop and 390 px widths — reports 45 UI checks passing
with zero console errors: the language switch on every surface, Tamil rendering
with no horizontal overflow, the language choice surviving a reload, the patient
adding and removing doctors with the doctor's list updating to match, no
doctor-side relationship control, the Reviewer dashboard with its verification
queue intact and no "Pharmacist" wording anywhere, and no demo credentials in the
interface.
