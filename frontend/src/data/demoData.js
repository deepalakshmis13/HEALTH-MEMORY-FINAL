/**
 * Reference data for the seeded development accounts.
 *
 * IMPORTANT: `DEMO_ACCOUNTS` is intentionally NOT rendered anywhere in the
 * public interface — no account cards, no quick-login buttons, no credentials
 * on the homepage or the sign-in screen. The seeded fictional records still
 * exist in the database for development and testing; the credentials live in
 * the README and in the `python seed.py` console output, where developers and
 * evaluators can find them.
 *
 * The list is kept here so it stays in step with `backend/seed.py`. Only
 * `DEMO_FLOW` is used by the UI.
 */

export const DEMO_PASSWORD = 'Demo@123';

export const DEMO_ACCOUNTS = [
  {
    email: 'patient@demo.health',
    name: 'Radha Krishnan, 72',
    role: 'patient',
    icon: '👤',
    note: 'Resident of Sunrise Senior Living — has a low-confidence handwritten note',
  },
  {
    email: 'patient2@demo.health',
    name: 'Ganesan Murugan, 78',
    role: 'patient',
    icon: '👤',
    note: 'Cared for at home by an individual caregiver',
  },
  {
    email: 'patient3@demo.health',
    name: 'Lakshmi Narayanan, 68',
    role: 'patient',
    icon: '👤',
    note: 'Resident with a medium-confidence handwritten prescription',
  },
  {
    email: 'doctor@demo.health',
    name: 'Dr. Arun Kumar — Cardiology',
    role: 'doctor',
    icon: '🩺',
    note: 'Treating doctor for Radha and Lakshmi',
  },
  {
    email: 'doctor2@demo.health',
    name: 'Dr. Meera Raghavan — General Medicine',
    role: 'doctor',
    icon: '🩺',
    note: 'Treating doctor for Ganesan',
  },
  {
    email: 'caregiver@demo.health',
    name: 'Priya Sharma — Old Age Home',
    role: 'caregiver',
    icon: '🤝',
    note: 'Sunrise Senior Living, shift-based care',
  },
  {
    email: 'caregiver2@demo.health',
    name: 'Anitha Raj — Individual Caregiver',
    role: 'caregiver',
    icon: '🤝',
    note: 'Single-patient home care',
  },
  {
    email: 'reviewer@demo.health',
    name: 'Kavitha Menon — MedPlus Clinical Review Desk',
    role: 'reviewer',
    icon: '💊',
    note: 'Verification queue owner',
  },
];

export const DEMO_FLOW = [
  'Patient adds health data by Text, Voice or Scan & Upload',
  'OCR reads the document and scores every field',
  'Low-confidence clinical fields go to the reviewer',
  'Reviewer verifies or corrects — provenance is preserved',
  'Verified memory is routed to the doctor named in the record',
  'Role-specific AI answers with evidence, under consent',
];

export default { DEMO_ACCOUNTS, DEMO_PASSWORD, DEMO_FLOW };
