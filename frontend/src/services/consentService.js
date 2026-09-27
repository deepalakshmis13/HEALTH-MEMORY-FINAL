import api from './api';

export const consentService = {
  meta: () => api.get('/api/consent/meta'),
  get: (patientId) => api.get(`/api/consent/${patientId}`),
  history: (patientId) => api.get(`/api/consent/${patientId}/history`),
  set: ({ patientId, granteeRole, scope, granted, granteeName, note }) =>
    api.post('/api/consent', {
      patient_id: patientId,
      grantee_role: granteeRole,
      scope,
      granted,
      grantee_name: granteeName || null,
      note: note || null,
    }),
};

export default consentService;
