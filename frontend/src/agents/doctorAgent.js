export const doctorAgent = {
  role: 'doctor',
  name: 'Clinical Health Memory Assistant',
  icon: '🩺',
  intro:
    'Longitudinal retrieval across this patient’s consented health memory. '
    + 'Provenance and verification status travel with every retrieved record.',
  quickActions: [
    "Summarize this patient's recent history.",
    'What changed since the last visit?',
    'Show recent medication changes.',
    'What caregiver observations are important?',
    'Generate a visit summary.',
  ],
  disclaimer:
    'Retrieved context only. AI output is a draft and never becomes the medical '
    + 'record until you review and save it.',
};

export default doctorAgent;
