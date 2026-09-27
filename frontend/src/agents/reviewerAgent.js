export const reviewerAgent = {
  role: 'reviewer',
  name: 'Medication Memory Assistant',
  icon: '💊',
  intro:
    'Medication-focused retrieval with direct access to the verification queue, '
    + 'OCR readings and their confidence scores.',
  quickActions: [
    'Which medication entries require verification?',
    'What medication changes are recorded?',
    'Show prescription history.',
    'What did the OCR extract?',
    'What needs confirmation?',
  ],
  disclaimer:
    'Never guess an illegible reading. If the source is unclear, reject it and '
    + 'ask the prescriber to confirm.',
};

export default reviewerAgent;
