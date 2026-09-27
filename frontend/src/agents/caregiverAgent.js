export const caregiverAgent = {
  role: 'caregiver',
  name: 'Care Companion',
  icon: '🤝',
  intro:
    'Shift-focused help: what is due, what happened before, and what to watch. '
    + 'Only care information you are authorized to see.',
  quickActions: [
    'What medications are due?',
    'What happened during the previous shift?',
    'What should I watch today?',
    'Generate the shift handover.',
  ],
  disclaimer:
    'Care guidance only. Never change a dose. Escalate anything new or worsening '
    + 'to the nurse-in-charge or doctor.',
};

export default caregiverAgent;
