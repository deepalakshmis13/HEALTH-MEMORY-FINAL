import { useEffect } from 'react';
import { Link } from 'react-router-dom';

import HomeNav, { scrollToSection } from '../components/home/HomeNav';
import HomeFooter from '../components/home/HomeFooter';
import useReveal from '../components/home/useReveal';
import {
  ElderCareScene,
  HeroScene,
  Icon,
  ScanArt,
  ScanDocumentScene,
  TextArt,
  VoiceArt,
} from '../components/home/illustrations';
import { useT } from '../i18n/LanguageContext';
import { defaultRouteFor } from '../utils/permissions';
import '../styles/home.css';

/* -------------------------------------------------------------------------- */
const VALUE_CARDS = [
  {
    icon: 'memory',
    tone: 'blue',
    title: 'Persistent Health Memory',
    body: 'Keep important health information organised across visits, hospitals and care settings — so nothing has to be explained from scratch again.',
  },
  {
    icon: 'shield',
    tone: 'lav',
    title: 'Consent-Aware Sharing',
    body: 'Control exactly which doctors, caregivers and reviewers can see which parts of the record. Permission is checked before anything is retrieved.',
  },
  {
    icon: 'spark',
    tone: 'teal',
    title: 'AI-Powered Understanding',
    body: 'Turn fragmented notes, prescriptions and recordings into useful, evidence-backed summaries that always show where each fact came from.',
  },
  {
    icon: 'users',
    tone: 'blush',
    title: 'Safer Elder Care',
    body: 'Connect patients, families, doctors, caregivers and reviewers around the same trusted health context, at the same moment.',
  },
];

const STEPS = [
  {
    tag: 'Add',
    body: 'Add information through text, voice, or scan & upload — whichever is easiest that day.',
  },
  {
    tag: 'Understand',
    body: 'OCR, extraction and AI organise what was added into structured, persistent health memory.',
  },
  {
    tag: 'Verify',
    body: 'Low-confidence medical information is reviewed and confirmed by an authorised reviewer before it is trusted.',
  },
  {
    tag: 'Connect',
    body: 'Authorised doctors, caregivers and reviewers receive the relevant part through consent-aware retrieval.',
  },
];

const INPUT_METHODS = [
  {
    art: <TextArt />,
    artClass: 'a',
    icon: 'text',
    tone: 'blue',
    title: 'Text',
    body: 'Enter health information naturally using simple, everyday sentences. No forms, no medical vocabulary required.',
  },
  {
    art: <VoiceArt />,
    artClass: 'b',
    icon: 'mic',
    tone: 'lav',
    title: 'Voice',
    body: 'Record your health experience in your own words. Speaking is often easier than typing — and the wording is kept exactly as spoken.',
  },
  {
    art: <ScanArt />,
    artClass: 'c',
    icon: 'scan',
    tone: 'amber',
    title: 'Scan & Upload',
    body: 'Upload medical reports, prescriptions, scanned documents and handwritten records straight from a phone camera.',
  },
];

const ROLES = [
  {
    id: 'for-patients',
    tag: 'Patient / Guardian',
    title: 'My Health Memory',
    body: 'A calm, readable view of your medicines, visits, tests and documents — with larger type, plain language and an assistant that answers in everyday words.',
    icon: 'heart',
    tone: 'blush',
    accent: '#d1607a',
    cta: 'Start your health memory',
  },
  {
    id: 'for-doctors',
    tag: 'Doctor',
    title: 'Clinical Health Memory',
    body: 'Longitudinal context before the consultation begins: what changed since the last visit, current medications, caregiver observations, and a one-click visit summary you review and edit.',
    icon: 'stethoscope',
    tone: 'blue',
    accent: '#12617c',
    cta: 'See the clinical view',
  },
  {
    id: 'for-caregivers',
    tag: 'Caregiver / Old Age Home',
    title: 'Connected Daily Care',
    body: 'Shift-based medication rounds, care tasks, observations and an AI-assisted handover — for an individual caregiver at home or a full facility rota.',
    icon: 'clipboard',
    tone: 'teal',
    accent: '#0d8f7d',
    cta: 'See the care workflow',
  },
  {
    id: 'for-reviewers',
    tag: 'Reviewer',
    title: 'Medication Memory & Verification',
    body: 'A focused queue of only the medication details that were read with low confidence — with the original document, the reading and its score side by side.',
    icon: 'pill',
    tone: 'lav',
    accent: '#6b60c4',
    cta: 'See the verification queue',
  },
];

const ELDER_FEATURES = [
  'Easier access to full health history',
  'Continuity between care teams',
  'Caregiver observations recorded daily',
  'Medication administration tracking',
  'Structured shift handovers',
  'Emergency information always ready',
  'Voice-first interaction',
  'Family and guardian involvement',
];

const OCR_CHAIN = [
  { label: 'Scanned prescription', note: 'Uploaded', tone: 'hp-note-info' },
  { label: 'OCR & handwriting recognition', note: 'Automatic', tone: 'hp-note-info' },
  { label: 'Confidence score per field', note: 'Below threshold', tone: 'hp-note-warn' },
  { label: 'Reviewer verification', note: 'Human review', tone: 'hp-note-warn' },
  { label: 'Verified health memory', note: 'Trusted', tone: 'hp-note-ok' },
];

const FLOW = [
  { title: 'Patient information', sub: 'Text, voice and documents', icon: 'text', tone: 'blue' },
  { title: 'Health memory', sub: 'Structured, with its source kept', icon: 'memory', tone: 'teal' },
  { title: 'Consent + authorization', sub: 'Checked before anything is read', icon: 'lock', tone: 'lav', emphasis: true },
  { title: 'Retrieval', sub: 'Only the relevant, permitted records', icon: 'link', tone: 'blue' },
  { title: 'Role-specific assistant', sub: 'Answers in the right register', icon: 'spark', tone: 'blush' },
];

/* -------------------------------------------------------------------------- */
export function Home({ user }) {
  const t = useT();
  useReveal();

  useEffect(() => {
    document.title =
      'Health Memory — AI-Powered Persistent Health Memory for Better Elder Care';
  }, []);

  const dashboardPath = user ? defaultRouteFor(user.role) : '/login';

  return (
    <div className="home">
      <HomeNav user={user} dashboardPath={dashboardPath} />

      {/* ==================================================== HERO */}
      <section className="hp-hero" id="top">
        <div className="hp-shell hp-hero-inner">
          <div className="hp-reveal">
            <span className="hp-eyebrow">{t('AI-Powered Health Memory')}</span>
            <h1>
              {t('Your Health Story,')}
              <br />
              <span className="hp-accent">{t('Remembered for Life.')}</span>
            </h1>
            <p className="hp-hero-sub">
              {t(
                'One secure place for your medical history, medications, doctor records, caregiver observations and important health information — intelligently connected through AI.',
              )}
            </p>

            <div className="hp-hero-cta">
              {user ? (
                <Link className="hp-btn hp-btn-primary hp-btn-lg" to={dashboardPath}>
                  {t('Open my dashboard')}
                  <Icon name="arrowRight" size={19} />
                </Link>
              ) : (
                <Link className="hp-btn hp-btn-primary hp-btn-lg" to="/register">
                  {t('Get Started')}
                  <Icon name="arrowRight" size={19} />
                </Link>
              )}
              <button
                type="button"
                className="hp-btn hp-btn-ghost hp-btn-lg"
                onClick={() => scrollToSection('how-it-works')}
              >
                {t('See How It Works')}
              </button>
            </div>

            <div className="hp-hero-proof">
              <span className="hp-proof-item">
                <Icon name="lock" size={18} /> {t('Consent-controlled by the patient')}
              </span>
              <span className="hp-proof-item">
                <Icon name="check" size={18} /> {t('Human-verified medication data')}
              </span>
              <span className="hp-proof-item">
                <Icon name="clipboard" size={18} /> {t('Every answer shows its source')}
              </span>
            </div>
          </div>

          <div className="hp-hero-visual hp-reveal">
            <div className="hp-hero-frame">
              <HeroScene />
            </div>

            <div className="hp-float hp-float-a">
              <span className="hp-float-icon" style={{ background: '#e3f4f0', color: '#0d8f7d' }}>
                <Icon name="link" size={18} />
              </span>
              <span className="hp-float-text">
                <span className="hp-float-title">{t('Health Memory Connected')}</span>
                <span className="hp-float-sub">{t('Across every care setting')}</span>
              </span>
            </div>

            <div className="hp-float hp-float-b">
              <span className="hp-float-icon" style={{ background: '#eeecfb', color: '#6b60c4' }}>
                <Icon name="shield" size={18} />
              </span>
              <span className="hp-float-text">
                <span className="hp-float-title">{t('Consent Protected')}</span>
                <span className="hp-float-sub">{t('You choose who sees what')}</span>
              </span>
            </div>

            <div className="hp-float hp-float-c">
              <span className="hp-float-icon" style={{ background: '#e7f1f5', color: '#12617c' }}>
                <Icon name="spark" size={18} />
              </span>
              <span className="hp-float-text">
                <span className="hp-float-title">{t('AI-Assisted')}</span>
                <span className="hp-float-sub">{t('Evidence-backed answers')}</span>
              </span>
            </div>
          </div>
        </div>
      </section>

      {/* ==================================================== TRUST / VALUE */}
      <section className="hp-section" id="health-memory">
        <div className="hp-shell">
          <div className="hp-section-head center hp-reveal">
            <span className="hp-eyebrow plain">{t('Why it matters')}</span>
            <h2>{t('One Health Memory. Every Care Moment Connected.')}</h2>
            <p>
              {t(
                'Elderly patients rarely see one doctor in one place. Their health story is spread across clinics, prescriptions, hospital stays and the people who care for them every day. This brings it back together.',
              )}
            </p>
          </div>

          <div className="hp-grid hp-grid-4">
            {VALUE_CARDS.map((card) => (
              <article className="hp-card hp-reveal" key={card.title}>
                <span className={`hp-icon ${card.tone}`}>
                  <Icon name={card.icon} size={25} />
                </span>
                <h3>{t(card.title)}</h3>
                <p>{t(card.body)}</p>
              </article>
            ))}
          </div>
        </div>
      </section>

      {/* ==================================================== HOW IT WORKS */}
      <section className="hp-section cream" id="how-it-works">
        <div className="hp-shell">
          <div className="hp-section-head center hp-reveal">
            <span className="hp-eyebrow plain">{t('How it works')}</span>
            <h2>{t('From Health Information to Connected Care')}</h2>
            <p>
              {t(
                'Four steps, every time — whether the information arrives as a spoken sentence or a handwritten prescription photographed on a phone.',
              )}
            </p>
          </div>

          <div className="hp-steps">
            {STEPS.map((step, index) => (
              <article className="hp-step hp-reveal" key={step.tag}>
                <span className="hp-step-num">{`0${index + 1}`}</span>
                <h3>{t(step.tag)}</h3>
                <p>{t(step.body)}</p>
              </article>
            ))}
          </div>
        </div>
      </section>

      {/* ==================================================== INPUT METHODS */}
      <section className="hp-section" id="add-information">
        <div className="hp-shell">
          <div className="hp-section-head center hp-reveal">
            <span className="hp-eyebrow plain">{t('Getting information in')}</span>
            <h2>{t('Add Your Health Information Your Way')}</h2>
            <p>
              {t(
                'All three routes lead to the same health memory, and each one keeps a permanent record of where the information came from.',
              )}
            </p>
          </div>

          <div className="hp-grid hp-grid-3">
            {INPUT_METHODS.map((method) => (
              <article className="hp-input-card hp-reveal" key={method.title}>
                <div className={`hp-input-art ${method.artClass}`}>{method.art}</div>
                <div className="hp-input-body">
                  <span className={`hp-icon ${method.tone}`} style={{ width: 44, height: 44, marginBottom: 16 }}>
                    <Icon name={method.icon} size={21} />
                  </span>
                  <h3>{t(method.title)}</h3>
                  <p>{t(method.body)}</p>
                </div>
              </article>
            ))}
          </div>
        </div>
      </section>

      {/* ==================================================== INTELLIGENCE / RAG */}
      <section className="hp-section mist" id="intelligence">
        <div className="hp-shell hp-arch">
          <div className="hp-reveal">
            <span className="hp-eyebrow">{t('The intelligence layer')}</span>
            <h2 style={{ fontSize: 'clamp(1.9rem, 3.4vw, 2.6rem)', marginTop: 16 }}>
              {t('One Memory. Smarter Care.')}
            </h2>
            <p style={{ color: 'var(--hp-muted)', fontSize: '1.06rem', marginTop: 16 }}>
              {t(
                'The assistant never reads the whole record and never guesses. It looks only at the parts that are relevant to the question, belong to that patient, and the viewer is permitted to see.',
              )}
            </p>

            <div className="hp-check-list">
              <div className="hp-check">
                <span className="hp-check-mark">
                  <Icon name="check" size={15} />
                </span>
                <div>
                  <strong>{t('Relevance')}</strong>
                  <p>{t('Only the records that actually answer the question are used.')}</p>
                </div>
              </div>
              <div className="hp-check">
                <span className="hp-check-mark">
                  <Icon name="check" size={15} />
                </span>
                <div>
                  <strong>{t('Identity and permission')}</strong>
                  <p>
                    {t(
                      'One patient at a time, and only for someone with a real care relationship and granted consent.',
                    )}
                  </p>
                </div>
              </div>
              <div className="hp-check">
                <span className="hp-check-mark">
                  <Icon name="check" size={15} />
                </span>
                <div>
                  <strong>{t('Source confidence')}</strong>
                  <p>
                    {t(
                      'Verified information outranks an uncertain reading — and an unverified one is always labelled as such.',
                    )}
                  </p>
                </div>
              </div>
            </div>
          </div>

          <div className="hp-flow hp-reveal">
            {FLOW.map((node, index) => (
              <div key={node.title}>
                <div className={`hp-flow-node${node.emphasis ? ' emphasis' : ''}`}>
                  <span
                    className="hp-flow-dot"
                    style={
                      node.emphasis
                        ? { background: 'rgba(255,255,255,0.18)', color: '#fff' }
                        : {
                            background: {
                              blue: '#e7f1f5',
                              teal: '#e3f4f0',
                              lav: '#eeecfb',
                              blush: '#fbecf0',
                            }[node.tone],
                            color: {
                              blue: '#12617c',
                              teal: '#0d8f7d',
                              lav: '#6b60c4',
                              blush: '#d1607a',
                            }[node.tone],
                          }
                    }
                  >
                    <Icon name={node.icon} size={17} />
                  </span>
                  <span>
                    <strong style={node.emphasis ? { color: '#fff' } : undefined}>
                      {t(node.title)}
                    </strong>
                    <br />
                    <span>{t(node.sub)}</span>
                  </span>
                </div>
                {index < FLOW.length - 1 && (
                  <div className="hp-flow-arrow">
                    <Icon name="arrowDown" size={17} />
                  </div>
                )}
              </div>
            ))}

            <div className="hp-flow-arrow">
              <Icon name="arrowDown" size={17} />
            </div>
            <div className="hp-flow-roles">
              {[
                { label: 'Patient', icon: 'heart' },
                { label: 'Doctor', icon: 'stethoscope' },
                { label: 'Caregiver', icon: 'clipboard' },
                { label: 'Reviewer', icon: 'pill' },
              ].map((role) => (
                <span className="hp-flow-role" key={role.label}>
                  <Icon name={role.icon} size={16} />
                  {t(role.label)}
                </span>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* ==================================================== ROLES */}
      <section className="hp-section" id="roles">
        <div className="hp-shell">
          <div className="hp-section-head center hp-reveal">
            <span className="hp-eyebrow plain">{t('Built for every role')}</span>
            <h2>{t('One Memory, Four Ways of Working')}</h2>
            <p>
              {t(
                'The same trusted record, presented in the language and level of detail each role actually needs.',
              )}
            </p>
          </div>

          <div className="hp-grid hp-grid-4">
            {ROLES.map((role) => (
              <article
                className="hp-role hp-reveal"
                key={role.id}
                id={role.id}
                style={{ '--hp-role-accent': role.accent }}
              >
                <span className={`hp-icon ${role.tone}`}>
                  <Icon name={role.icon} size={24} />
                </span>
                <span className="hp-role-tag">{t(role.tag)}</span>
                <h3>{t(role.title)}</h3>
                <p>{t(role.body)}</p>
                <Link className="hp-link" to={user ? dashboardPath : '/register'}>
                  {t(role.cta)}
                  <span className="hp-arrow">
                    <Icon name="arrowRight" size={16} />
                  </span>
                </Link>
              </article>
            ))}
          </div>
        </div>
      </section>

      {/* ==================================================== OCR / VERIFICATION */}
      <section className="hp-section cream" id="verification">
        <div className="hp-shell hp-ocr">
          <div className="hp-reveal">
            <span className="hp-eyebrow">{t('Handwriting, handled')}</span>
            <h2 style={{ fontSize: 'clamp(1.85rem, 3.2vw, 2.5rem)', marginTop: 16 }}>
              {t('Even Handwritten Records Can Become Part of Your Health Memory')}
            </h2>
            <p style={{ color: 'var(--hp-muted)', fontSize: '1.06rem', marginTop: 18 }}>
              {t(
                'Medical documents are processed using OCR and handwriting recognition. When confidence is low, clinically important information is routed for reviewer verification before it becomes trusted structured memory.',
              )}
            </p>
            <p style={{ color: 'var(--hp-muted)', fontSize: '1.02rem', marginTop: 14 }}>
              {t(
                'A doctor’s name read imperfectly is not worth interrupting anyone over. A dose read imperfectly is. That distinction is built into the system, not left to judgement.',
              )}
            </p>

            <div className="hp-ocr-chain" style={{ marginTop: 30 }}>
              {OCR_CHAIN.map((step, index) => (
                <div key={step.label}>
                  <div className="hp-chain-step">
                    <span className="hp-chain-idx">{index + 1}</span>
                    <strong>{t(step.label)}</strong>
                    <span className={`hp-chain-note ${step.tone}`}>{t(step.note)}</span>
                  </div>
                  {index < OCR_CHAIN.length - 1 && <div className="hp-chain-link" />}
                </div>
              ))}
            </div>
          </div>

          <div className="hp-ocr-stage hp-reveal">
            <span className="hp-eyebrow plain" style={{ color: 'var(--hp-faint)' }}>
              {t('Illustrative example')}
            </span>
            <ScanDocumentScene />
          </div>
        </div>
      </section>

      {/* ==================================================== ELDER CARE */}
      <section className="hp-section" id="elder-care">
        <div className="hp-shell hp-split reverse">
          <div className="hp-split-visual hp-reveal">
            <ElderCareScene />
          </div>
          <div className="hp-reveal">
            <span className="hp-eyebrow">{t('For the people it is for')}</span>
            <h2 style={{ fontSize: 'clamp(1.85rem, 3.2vw, 2.5rem)', marginTop: 16 }}>
              {t('Designed Around the Real Needs of Elder Care')}
            </h2>
            <p style={{ color: 'var(--hp-muted)', fontSize: '1.06rem', marginTop: 18 }}>
              {t(
                'Elder care is not one appointment — it is a daily rhythm of medication, observation, family involvement and handovers between people who have never met each other. The platform is shaped around that reality.',
              )}
            </p>

            <div className="hp-feature-grid">
              {ELDER_FEATURES.map((feature) => (
                <span className="hp-feature" key={feature}>
                  <Icon name="check" size={16} />
                  {t(feature)}
                </span>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* ==================================================== EMERGENCY */}
      <section className="hp-section mist" id="emergency">
        <div className="hp-shell hp-split">
          <div className="hp-reveal">
            <span className="hp-eyebrow">{t('Emergency mode')}</span>
            <h2 style={{ fontSize: 'clamp(1.85rem, 3.2vw, 2.5rem)', marginTop: 16 }}>
              {t('Critical Information, When Every Second Matters')}
            </h2>
            <p style={{ color: 'var(--hp-muted)', fontSize: '1.06rem', marginTop: 18 }}>
              {t(
                'In an emergency, nobody should be searching through a record. The Emergency Health Card strips everything back to what a paramedic or an unfamiliar doctor needs in the first thirty seconds — readable at arm’s length, and printable.',
              )}
            </p>
            <p style={{ color: 'var(--hp-muted)', fontSize: '1.02rem', marginTop: 14 }}>
              {t(
                'Medication still awaiting verification is deliberately left off the card. Only confirmed information belongs on it.',
              )}
            </p>
            <div style={{ marginTop: 28 }}>
              <Link className="hp-btn hp-btn-primary" to={user ? dashboardPath : '/register'}>
                {t('Learn About Emergency Mode')}
                <Icon name="arrowRight" size={18} />
              </Link>
            </div>
          </div>

          <div className="hp-reveal" style={{ display: 'grid', justifyItems: 'center' }}>
            <div className="hp-emg">
              <div className="hp-emg-head">
                <Icon name="alert" size={24} />
                <div>
                  <h3>{t('Emergency Health Card')}</h3>
                  <p>{t('Example layout — no real patient information')}</p>
                </div>
              </div>
              <div className="hp-emg-rows">
                <EmgRow label="Blood group" value="Sample value" alert />
                <EmgRow label="Allergies" value="Listed here, with reactions" alert />
                <EmgRow label="Critical conditions" value="Active conditions marked critical" />
                <EmgRow label="Critical medications" value="Verified medicines and doses" />
                <EmgRow label="Emergency contact" value="Name, relation and phone" />
                <EmgRow label="Primary doctor" value="Name, specialty and hospital" />
              </div>
              <div className="hp-emg-foot">
                {t(
                  'Generated from verified health memory · shown only to people the patient has granted emergency access',
                )}
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ==================================================== FINAL CTA */}
      <section className="hp-section tight">
        <div className="hp-shell">
          <div className="hp-cta hp-reveal">
            <h2>{t('Make Every Care Decision Start With the Right Health Memory.')}</h2>
            <p>
              {t(
                'Bring the patient’s health story together — securely, intelligently, and with the right people.',
              )}
            </p>
            <div className="hp-cta-buttons">
              {user ? (
                <Link className="hp-btn hp-btn-primary hp-btn-lg" to={dashboardPath}>
                  {t('Open my dashboard')}
                </Link>
              ) : (
                <>
                  <Link className="hp-btn hp-btn-primary hp-btn-lg" to="/register">
                    {t('Get Started')}
                  </Link>
                  <Link className="hp-btn hp-btn-light hp-btn-lg" to="/login">
                    {t('Login')}
                  </Link>
                </>
              )}
            </div>
          </div>
        </div>
      </section>

      <HomeFooter />
    </div>
  );
}

function EmgRow({ label, value, alert }) {
  const t = useT();

  return (
    <div className="hp-emg-row">
      <span className="hp-emg-label">{t(label)}</span>
      <span className={`hp-emg-value${alert ? ' alert' : ''}`}>{t(value)}</span>
    </div>
  );
}

export default Home;
