import api, { getToken } from './api';

export const documentService = {
  list: (patientId) => api.get(`/api/documents/patient/${patientId}`),
  get: (documentId) => api.get(`/api/documents/${documentId}`),
  ocrResult: (documentId) => api.get(`/api/ocr/${documentId}`),
  reprocess: (documentId, isHandwritten) =>
    api.post(
      `/api/ocr/process?document_id=${documentId}` +
        (isHandwritten === undefined ? '' : `&is_handwritten=${isHandwritten}`),
    ),
  engines: () => api.get('/api/ocr/engines'),

  /** Fetch the stored file as an object URL so the token can travel in a header. */
  async fileUrl(documentId) {
    const token = getToken();
    const response = await fetch(`/api/documents/${documentId}/file`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
    if (!response.ok) return null;
    const blob = await response.blob();
    return { url: URL.createObjectURL(blob), type: blob.type };
  },
};

export default documentService;
