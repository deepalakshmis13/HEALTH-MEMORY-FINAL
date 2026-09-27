import api from './api';

export const memoryService = {
  listPatients: () => api.get('/api/patients'),
  getPatient: (patientId) => api.get(`/api/patients/${patientId}`),
  overview: (patientId) => api.get(`/api/patients/${patientId}/overview`),

  memory: (patientId, params = {}) => {
    const query = new URLSearchParams();
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== '') {
        query.set(key, value);
      }
    });
    const suffix = query.toString() ? `?${query}` : '';
    return api.get(`/api/memory/${patientId}${suffix}`);
  },

  timeline: (patientId) => api.get(`/api/memory/${patientId}/timeline`),
  createEvent: (payload) => api.post('/api/memory', payload),
  emergencyCard: (patientId) => api.get(`/api/emergency/${patientId}`),
  audit: (patientId) =>
    api.get(`/api/audit${patientId ? `?patient_id=${patientId}` : ''}`),
  systemConfig: () => api.get('/api/system/config'),
};

export default memoryService;
