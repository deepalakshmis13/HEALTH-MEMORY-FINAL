/**
 * UI-side permission helpers.
 *
 * These only decide what to *render*. Every one of them is enforced again in
 * the backend — the interface is never the security boundary.
 */

export const SCOPE_LABELS = {
  FULL_HEALTH_MEMORY: 'Full Health Memory',
  MEDICATION_INFORMATION: 'Medication Information',
  EMERGENCY_INFORMATION: 'Emergency Information',
  RECENT_HISTORY: 'Recent History',
  CAREGIVER_NOTES: 'Caregiver Notes',
  DOCUMENTS: 'Documents',
  VOICE_DIARY: 'Voice Diary',
};

export const SCOPE_DESCRIPTIONS = {
  FULL_HEALTH_MEMORY: 'Everything in the health memory, including all sources.',
  MEDICATION_INFORMATION: 'Medicines, doses, prescriptions and allergies.',
  EMERGENCY_INFORMATION: 'Blood group, allergies, critical conditions and contacts.',
  RECENT_HISTORY: 'Consultations, conditions, symptoms and lab results.',
  CAREGIVER_NOTES: 'Observations recorded by caregivers during care.',
  DOCUMENTS: 'Uploaded and scanned medical documents.',
  VOICE_DIARY: 'Voice recordings and their transcripts.',
};

export function hasScope(scopes = [], scope) {
  return scopes.includes('FULL_HEALTH_MEMORY') || scopes.includes(scope);
}

export function canEditConsent(user, patientId) {
  return user?.role === 'patient' && user?.patient_id === patientId;
}

export function canVerify(user) {
  return user?.role === 'reviewer';
}

export function canRecordCare(user) {
  return user?.role === 'caregiver';
}

export function canGenerateVisitSummary(user) {
  return user?.role === 'doctor';
}

export function defaultRouteFor(role) {
  return (
    {
      patient: '/patient',
      doctor: '/doctor',
      caregiver: '/caregiver',
      reviewer: '/reviewer',
    }[role] || '/login'
  );
}
