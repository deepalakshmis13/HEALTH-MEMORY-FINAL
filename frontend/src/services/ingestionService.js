import api from './api';

export const ingestionService = {
  text: (patientId, text, entryDate) =>
    api.post('/api/ingestion/text', {
      patient_id: patientId,
      text,
      entry_date: entryDate || null,
    }),

  voice: (patientId, transcript, extras = {}) =>
    api.post('/api/ingestion/voice', {
      patient_id: patientId,
      transcript,
      duration_seconds: extras.durationSeconds ?? null,
      recognition_confidence: extras.recognitionConfidence ?? 0.9,
      audio_ref: extras.audioRef ?? null,
    }),

  upload: (patientId, file, { isHandwritten = false, documentType, notes } = {}) => {
    const form = new FormData();
    form.append('patient_id', String(patientId));
    form.append('file', file);
    form.append('is_handwritten', isHandwritten ? 'true' : 'false');
    if (documentType) form.append('document_type', documentType);
    if (notes) form.append('notes', notes);
    return api.upload('/api/ingestion/upload', form);
  },

  voiceEntries: (patientId) => api.get(`/api/voice/${patientId}`),
};

export default ingestionService;
