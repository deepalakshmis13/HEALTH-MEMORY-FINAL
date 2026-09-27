export const patientAgent = {
  role: 'patient',
  name: 'My Health Memory Assistant',
  icon: '💬',
  intro:
    'Ask me anything about your health memory. I only use information that is '
    + 'saved in your record, and I always show you where it came from.',
  quickActions: [
    'What medicines am I taking?',
    'What happened during my last visit?',
    'What did my doctor recommend?',
    'What health information was recently added?',
    'What allergies are recorded?',
  ],
  disclaimer:
    'This assistant does not give medical advice and cannot change your treatment. '
    + 'Always follow what your doctor tells you.',
};

export default patientAgent;
