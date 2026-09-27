import api from './api';

export const chatbotService = {
  agents: () => api.get('/api/chat/agents'),

  ask: (role, { patientId, message, history = [], shiftId }) => {
    const payload = {
      patient_id: patientId ?? null,
      message,
      history: history.slice(-6).map((turn) => ({
        role: turn.role,
        content: turn.content,
      })),
    };
    if (role === 'caregiver' && shiftId) {
      payload.history = [
        ...payload.history,
        { role: 'system', content: `shift:${shiftId}` },
      ];
    }
    return api.post(`/api/chat/${role}`, payload);
  },
};

export default chatbotService;
