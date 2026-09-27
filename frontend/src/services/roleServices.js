import api from './api';

/**
 * The patient's own care team. Only a patient (or their guardian) can call
 * these — the backend refuses every other role — so there is no doctor-side
 * counterpart to this service anywhere in the app.
 */
export const careTeamService = {
  search: (query, patientId) =>
    api.get(
      `/api/care-team/search?q=${encodeURIComponent(query || '')}` +
        (patientId ? `&patient_id=${patientId}` : ''),
    ),
  list: (patientId) => api.get(`/api/care-team/${patientId}`),
  add: (patientId, doctorId, makePrimary = false) =>
    api.post(`/api/care-team/${patientId}/doctors`, {
      doctor_id: doctorId,
      make_primary: makePrimary,
    }),
  remove: (patientId, doctorId) =>
    api.del(`/api/care-team/${patientId}/doctors/${doctorId}`),
  setPrimary: (patientId, doctorId) =>
    api.post(`/api/care-team/${patientId}/doctors/${doctorId}/primary`),
};

export const doctorService = {
  routing: () => api.get('/api/doctor/routing'),
  insights: (patientId) => api.get(`/api/doctor/insights/${patientId}`),
  caregiverFeed: (patientId) => api.get(`/api/doctor/caregiver-feed/${patientId}`),
  visitSummary: (patientId) =>
    api.post('/api/doctor/visit-summary', { patient_id: patientId }),
  saveVisitSummary: (summaryId, content) =>
    api.post('/api/doctor/visit-summary/save', {
      summary_id: summaryId,
      content,
    }),
  listSummaries: (patientId) => api.get(`/api/doctor/visit-summaries/${patientId}`),
};

export const caregiverService = {
  config: () => api.get('/api/caregiver/config'),
  setCareType: (careType, facilityId) =>
    api.post(
      `/api/caregiver/care-type?care_type=${careType}` +
        (facilityId ? `&facility_id=${facilityId}` : ''),
    ),
  startShift: ({ careType, shiftCode, facilityId, patientIds }) =>
    api.post('/api/caregiver/shift/start', {
      care_type: careType,
      shift_code: shiftCode,
      facility_id: facilityId || null,
      patient_ids: patientIds,
    }),
  shift: (shiftId) => api.get(`/api/caregiver/shift/${shiftId}`),
  shifts: () => api.get('/api/caregiver/shifts'),
  verifyMedication: (payload) => api.post('/api/caregiver/medication/verify', payload),
  addObservation: (payload) => api.post('/api/caregiver/observation', payload),
  updateTask: (taskId, status, notes) =>
    api.post(`/api/caregiver/task/${taskId}`, { status, notes: notes || null }),
  insights: (patientId) =>
    api.get(`/api/caregiver/insights${patientId ? `?patient_id=${patientId}` : ''}`),
  generateHandover: (shiftId, patientIds = []) =>
    api.post('/api/caregiver/shift-handover', {
      shift_id: shiftId,
      patient_ids: patientIds,
    }),
  saveHandover: (handoverId, content) =>
    api.post('/api/caregiver/shift-handover/save', {
      handover_id: handoverId,
      content,
    }),
  handovers: () => api.get('/api/caregiver/handovers'),
};

export const reviewerService = {
  queue: (status = 'PENDING_VERIFICATION') =>
    api.get(`/api/verification/queue?status=${status}`),
  task: (taskId) => api.get(`/api/verification/${taskId}`),
  verify: (taskId, note) => api.post(`/api/verification/${taskId}/verify`, { note }),
  correct: (taskId, correctedValue, clarification) =>
    api.post(`/api/verification/${taskId}/correct`, {
      corrected_value: correctedValue,
      clarification: clarification || null,
    }),
  reject: (taskId, reason) => api.post(`/api/verification/${taskId}/reject`, { reason }),
  patients: () => api.get('/api/reviewer/patients'),
  medications: (patientId) => api.get(`/api/reviewer/medications/${patientId}`),
  insights: () => api.get('/api/reviewer/insights'),
};

export default { doctorService, caregiverService, reviewerService };
