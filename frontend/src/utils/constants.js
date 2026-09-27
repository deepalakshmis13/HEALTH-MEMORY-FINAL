/** Shared vocabulary — mirrors backend/config.py. */

export const HIGH_CONFIDENCE_THRESHOLD = 0.85;
export const MEDIUM_CONFIDENCE_THRESHOLD = 0.6;

export const ROLES = {
  patient: { label: 'Patient / Guardian', icon: '👤', home: '/patient' },
  doctor: { label: 'Doctor', icon: '🩺', home: '/doctor' },
  caregiver: { label: 'Caregiver / Old Age Home', icon: '🤝', home: '/caregiver' },
  reviewer: { label: 'Reviewer', icon: '💊', home: '/reviewer' },
};

export const SOURCE_LABELS = {
  PATIENT_TEXT: 'Patient/Guardian entered',
  PATIENT_VOICE: 'Voice diary',
  DOCTOR_DOCUMENT: 'Doctor document',
  SCANNED_DOCUMENT: 'Scanned document',
  HANDWRITTEN_DOCUMENT: 'Handwritten document',
  OCR: 'OCR extraction',
  DOCTOR_RECORDED: 'Doctor recorded',
  CAREGIVER_RECORDED: 'Caregiver recorded',
  REVIEWER_VERIFIED: 'Reviewer verified',
  AI_GENERATED: 'AI generated',
};

export const SOURCE_ICONS = {
  PATIENT_TEXT: '📝',
  PATIENT_VOICE: '🎙',
  DOCTOR_DOCUMENT: '📄',
  SCANNED_DOCUMENT: '📄',
  HANDWRITTEN_DOCUMENT: '✍️',
  OCR: '🔍',
  DOCTOR_RECORDED: '🩺',
  CAREGIVER_RECORDED: '🤝',
  REVIEWER_VERIFIED: '✅',
  AI_GENERATED: '✨',
};

export const TRUST_TONE = {
  'Reviewer Verified': 'ok',
  'Doctor Recorded': 'info',
  'Caregiver Recorded': 'primary',
  'OCR Extracted': 'warn',
  'Patient Reported': 'outline',
  'AI Extracted': 'outline',
};

export const EVENT_TYPE_LABELS = {
  CONSULTATION: 'Consultation',
  MEDICATION: 'Medication',
  MEDICATION_CHANGE: 'Medication change',
  MEDICATION_ADMINISTRATION: 'Medication given',
  PRESCRIPTION: 'Prescription',
  DIAGNOSIS: 'Condition',
  SYMPTOM: 'Symptom',
  ALLERGY: 'Allergy',
  LAB_RESULT: 'Lab result',
  HOSPITAL_VISIT: 'Hospital visit',
  OBSERVATION: 'Caregiver observation',
  VOICE_ENTRY: 'Voice diary',
  DOCUMENT: 'Document',
  NOTE: 'Note',
};

export const EVENT_TYPE_ICONS = {
  CONSULTATION: '🩺',
  MEDICATION: '💊',
  MEDICATION_CHANGE: '🔁',
  MEDICATION_ADMINISTRATION: '✔️',
  PRESCRIPTION: '🧾',
  DIAGNOSIS: '📋',
  SYMPTOM: '🌡',
  ALLERGY: '⚠️',
  LAB_RESULT: '🧪',
  HOSPITAL_VISIT: '🏥',
  OBSERVATION: '👁',
  VOICE_ENTRY: '🎙',
  DOCUMENT: '📄',
  NOTE: '📝',
};

export const VERIFICATION_LABELS = {
  PENDING_VERIFICATION: 'Pending verification',
  VERIFIED: 'Verified',
  CORRECTED: 'Corrected and verified',
  REJECTED: 'Rejected',
  NOT_REQUIRED: 'No verification needed',
};

export const ADMINISTRATION_STATUSES = [
  'Pending',
  'Administered',
  'Missed',
  'Skipped',
  'Delayed',
  'Needs Attention',
];

export const OBSERVATION_CATEGORIES = [
  { key: 'general', label: 'General' },
  { key: 'meal', label: 'Meal' },
  { key: 'sleep', label: 'Sleep' },
  { key: 'mood', label: 'Mood' },
  { key: 'mobility', label: 'Mobility' },
  { key: 'vitals', label: 'Vitals' },
  { key: 'incident', label: 'Incident' },
];

export const LOADING_MESSAGES = {
  document: 'Reading medical document…',
  handwriting: 'Recognising handwriting…',
  confidence: 'Calculating confidence…',
  memory: 'Updating health memory…',
  retrieval: 'Finding relevant records…',
  consent: 'Checking consent…',
  clinical: 'Retrieving clinical history…',
  summary: 'Generating visit summary…',
  handover: 'Generating shift handover…',
};
