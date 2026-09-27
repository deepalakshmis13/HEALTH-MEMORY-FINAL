/**
 * Original healthcare illustrations and icons for the public homepage.
 *
 * Everything here is drawn from scratch as inline SVG — no stock photography,
 * no third-party assets, nothing to license. Inline SVG also means the artwork
 * inherits the page palette, scales without artefacts on any display, and adds
 * nothing to the network waterfall.
 */

/* eslint-disable react/no-unknown-property */

const SKIN_WARM = '#e7b492';
const SKIN_DEEP = '#c98f68';
const SILVER = '#dfe4e9';
const CHARCOAL = '#3b4a5a';

/* ==========================================================================
   Hero — an elderly patient and her care companion, connected by her memory
   ========================================================================== */
export function HeroScene() {
  return (
    <svg
      viewBox="0 0 640 544"
      role="img"
      aria-label="An elderly patient seated with a care professional beside her, her health memory connected above them"
      xmlns="http://www.w3.org/2000/svg"
    >
      <defs>
        <linearGradient id="hs-halo" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="#ffffff" stopOpacity="0.92" />
          <stop offset="100%" stopColor="#ffffff" stopOpacity="0.42" />
        </linearGradient>
        <linearGradient id="hs-coat" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#ffffff" />
          <stop offset="100%" stopColor="#eef4f7" />
        </linearGradient>
        <linearGradient id="hs-thread" x1="0" y1="0" x2="1" y2="0">
          <stop offset="0%" stopColor="#0d8f7d" />
          <stop offset="100%" stopColor="#6b60c4" />
        </linearGradient>
        <linearGradient id="hs-chair" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#e8d6c6" />
          <stop offset="100%" stopColor="#d6c0ad" />
        </linearGradient>
      </defs>

      {/* soft halo + ground */}
      <circle cx="352" cy="252" r="196" fill="url(#hs-halo)" />
      <ellipse cx="320" cy="474" rx="252" ry="30" fill="#d5e2ea" opacity="0.6" />

      {/* --- memory thread arcing above the two figures --- */}
      <path
        d="M132 138 C 205 74, 330 70, 404 116"
        fill="none"
        stroke="url(#hs-thread)"
        strokeWidth="2.4"
        strokeLinecap="round"
        strokeDasharray="7 9"
        opacity="0.75"
      />
      <MemoryChip x={96} y={116} tone="#0d8f7d" bg="#e3f4f0" glyph="pulse" />
      <MemoryChip x={252} y={66} tone="#12617c" bg="#e7f1f5" glyph="doc" />
      <MemoryChip x={392} y={108} tone="#6b60c4" bg="#eeecfb" glyph="lock" />

      {/* ================= seated elderly patient ================= */}
      {/* armchair */}
      <path
        d="M126 300 q0-34 34-34 h118 q34 0 34 34 v92 q0 16-16 16 h-154 q-16 0-16-16 z"
        fill="url(#hs-chair)"
      />
      <rect x="112" y="330" width="30" height="86" rx="15" fill="#c9b19c" />
      <rect x="296" y="330" width="30" height="86" rx="15" fill="#c9b19c" />
      <rect x="140" y="416" width="16" height="46" rx="8" fill="#b39a85" />
      <rect x="286" y="416" width="16" height="46" rx="8" fill="#b39a85" />

      {/* legs */}
      <path
        d="M200 396 q-6 42 -14 66"
        stroke="#8fa0b4"
        strokeWidth="26"
        strokeLinecap="round"
        fill="none"
      />
      <path
        d="M244 396 q-2 42 -8 66"
        stroke="#8fa0b4"
        strokeWidth="26"
        strokeLinecap="round"
        fill="none"
      />
      <rect x="166" y="452" width="42" height="17" rx="8.5" fill="#5b6b7f" />
      <rect x="216" y="452" width="42" height="17" rx="8.5" fill="#5b6b7f" />

      {/* body */}
      <path
        d="M180 402 q-8-92 42-104 h22 q50 12 42 104 z"
        fill="#cfc9ee"
      />
      <path d="M198 300 h68 v12 h-68 z" fill="#bdb5e5" opacity="0.7" />

      {/* folded hands */}
      <path
        d="M184 336 q22 30 50 32"
        stroke="#cfc9ee"
        strokeWidth="22"
        strokeLinecap="round"
        fill="none"
      />
      <path
        d="M262 336 q-18 30 -44 32"
        stroke="#cfc9ee"
        strokeWidth="22"
        strokeLinecap="round"
        fill="none"
      />
      <ellipse cx="232" cy="370" rx="24" ry="15" fill={SKIN_WARM} />

      {/* head */}
      <rect x="216" y="272" width="18" height="24" rx="9" fill={SKIN_DEEP} />
      <circle cx="226" cy="250" r="35" fill={SKIN_WARM} />
      <path
        d="M191 246 q4-40 36-40 q34 0 38 40 q-10-16-38-16 q-28 0-36 16 z"
        fill={SILVER}
      />
      <path d="M256 240 q12 10 8 28" stroke={SILVER} strokeWidth="11" strokeLinecap="round" fill="none" />
      {/* glasses */}
      <circle cx="213" cy="252" r="10.5" fill="#ffffff" opacity="0.6" stroke={CHARCOAL} strokeWidth="2.2" />
      <circle cx="243" cy="252" r="10.5" fill="#ffffff" opacity="0.6" stroke={CHARCOAL} strokeWidth="2.2" />
      <path d="M223.5 252 h9" stroke={CHARCOAL} strokeWidth="2.2" />
      <path d="M228 268 q8 5 15 0" stroke={CHARCOAL} strokeWidth="2.4" strokeLinecap="round" fill="none" />

      {/* ================= standing care professional ================= */}
      {/* legs */}
      <rect x="392" y="378" width="26" height="86" rx="13" fill="#37475c" />
      <rect x="428" y="378" width="26" height="86" rx="13" fill="#2f3e50" />
      <rect x="382" y="456" width="44" height="16" rx="8" fill="#22303f" />
      <rect x="424" y="456" width="44" height="16" rx="8" fill="#22303f" />

      {/* coat */}
      <path
        d="M378 392 q-12-104 46-120 h34 q58 16 46 120 z"
        fill="url(#hs-coat)"
      />
      <path d="M424 272 v120" stroke="#dae5eb" strokeWidth="2.4" />
      {/* scrub top under the coat */}
      <path d="M404 274 q20 26 40 0 v34 q-20 16-40 0 z" fill="#2f8f9d" />

      {/* arm resting on the patient's shoulder */}
      <path
        d="M392 300 q-52 14 -84 34"
        stroke="#ffffff"
        strokeWidth="24"
        strokeLinecap="round"
        fill="none"
      />
      <path
        d="M392 300 q-52 14 -84 34"
        stroke="#e5eef3"
        strokeWidth="24"
        strokeLinecap="round"
        fill="none"
        opacity="0.5"
      />
      <ellipse cx="300" cy="338" rx="17" ry="13" transform="rotate(-18 300 338)" fill={SKIN_DEEP} />

      {/* arm holding a tablet */}
      <path
        d="M462 302 q30 24 24 58"
        stroke="#ffffff"
        strokeWidth="24"
        strokeLinecap="round"
        fill="none"
      />
      <g transform="rotate(-8 486 372)">
        <rect x="458" y="344" width="60" height="76" rx="9" fill="#ffffff" stroke="#cfdce4" strokeWidth="2" />
        <rect x="468" y="356" width="40" height="6" rx="3" fill="#12617c" opacity="0.75" />
        <rect x="468" y="370" width="30" height="5" rx="2.5" fill="#c3d3dd" />
        <rect x="468" y="382" width="36" height="5" rx="2.5" fill="#c3d3dd" />
        <rect x="468" y="394" width="24" height="5" rx="2.5" fill="#0d8f7d" opacity="0.6" />
      </g>
      <ellipse cx="486" cy="364" rx="14" ry="11" fill={SKIN_DEEP} />

      {/* head */}
      <rect x="415" y="240" width="18" height="26" rx="9" fill={SKIN_DEEP} />
      <circle cx="424" cy="214" r="33" fill={SKIN_DEEP} />
      <path
        d="M391 212 q2-38 33-38 q31 0 33 38 q-8-18-33-18 q-25 0-33 18 z"
        fill="#3a3038"
      />
      <circle cx="456" cy="200" r="13" fill="#3a3038" />
      <circle cx="414" cy="216" r="2.8" fill={CHARCOAL} />
      <circle cx="436" cy="216" r="2.8" fill={CHARCOAL} />
      <path d="M417 230 q8 6 16 0" stroke={CHARCOAL} strokeWidth="2.4" strokeLinecap="round" fill="none" />

      {/* stethoscope */}
      <path
        d="M406 268 q-14 42 16 52 q30 10 34-24"
        stroke="#2f8f9d"
        strokeWidth="4"
        fill="none"
        strokeLinecap="round"
      />
      <circle cx="456" cy="294" r="8" fill="#ffffff" stroke="#2f8f9d" strokeWidth="4" />
    </svg>
  );
}

function MemoryChip({ x, y, tone, bg, glyph }) {
  return (
    <g transform={`translate(${x} ${y})`}>
      <rect
        x="0"
        y="0"
        width="46"
        height="46"
        rx="14"
        fill="#ffffff"
        stroke="#e5ecf2"
        strokeWidth="1.5"
      />
      <rect x="7" y="7" width="32" height="32" rx="10" fill={bg} />
      <g transform="translate(15 15)" stroke={tone} strokeWidth="2" fill="none" strokeLinecap="round" strokeLinejoin="round">
        {glyph === 'pulse' && <path d="M0 8 h4 l2-6 l4 12 l2-6 h4" />}
        {glyph === 'doc' && (
          <>
            <path d="M2 0 h8 l4 4 v12 h-12 z" />
            <path d="M5 8 h6 M5 12 h4" />
          </>
        )}
        {glyph === 'lock' && (
          <>
            <rect x="2" y="7" width="12" height="9" rx="2" />
            <path d="M5 7 V5 a3 3 0 0 1 6 0 v2" />
          </>
        )}
      </g>
    </g>
  );
}

/* ==========================================================================
   Elder care — an older man walking with a family member, at home
   ========================================================================== */
export function ElderCareScene() {
  return (
    <svg
      viewBox="0 0 560 448"
      role="img"
      aria-label="An older man walking with the support of a family member at home"
      xmlns="http://www.w3.org/2000/svg"
    >
      <defs>
        <linearGradient id="ec-wall" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#ffffff" stopOpacity="0.85" />
          <stop offset="100%" stopColor="#ffffff" stopOpacity="0.25" />
        </linearGradient>
      </defs>

      <circle cx="292" cy="196" r="164" fill="url(#ec-wall)" />

      {/* window */}
      <rect x="60" y="66" width="112" height="132" rx="16" fill="#e8f1f6" stroke="#d3e2ea" strokeWidth="2.5" />
      <path d="M116 66 v132 M60 132 h112" stroke="#d3e2ea" strokeWidth="2.5" />
      {/* plant */}
      <path d="M452 322 q-14-52 6-78 q16 26 6 78" fill="#5aa88c" />
      <path d="M462 322 q22-40 44-44 q-8 28-36 46" fill="#79bd9f" />
      <path d="M436 320 h56 l-7 44 h-42 z" fill="#d8ac8a" />

      <ellipse cx="280" cy="392" rx="196" ry="24" fill="#dde8ee" opacity="0.7" />

      {/* ---- family member (left) ---- */}
      <rect x="188" y="300" width="23" height="82" rx="11.5" fill="#4a6076" />
      <rect x="216" y="300" width="23" height="82" rx="11.5" fill="#405468" />
      <rect x="180" y="374" width="40" height="15" rx="7.5" fill="#2b3948" />
      <rect x="212" y="374" width="40" height="15" rx="7.5" fill="#2b3948" />
      <path d="M180 314 q-10-88 40-102 h20 q50 14 40 102 z" fill="#7f74d2" />
      {/* supporting arm */}
      <path d="M258 244 q46 8 66 34" stroke="#7f74d2" strokeWidth="21" strokeLinecap="round" fill="none" />
      <ellipse cx="326" cy="282" rx="15" ry="12" fill={SKIN_WARM} />
      <rect x="212" y="188" width="16" height="24" rx="8" fill={SKIN_DEEP} />
      <circle cx="220" cy="166" r="30" fill={SKIN_WARM} />
      <path d="M190 164 q0-34 30-34 q30 0 30 34 q-6-16-30-16 q-24 0-30 16 z" fill="#4a3b34" />
      <path d="M246 158 q14 14 6 40" stroke="#4a3b34" strokeWidth="14" strokeLinecap="round" fill="none" />
      <circle cx="211" cy="168" r="2.6" fill={CHARCOAL} />
      <circle cx="230" cy="168" r="2.6" fill={CHARCOAL} />
      <path d="M213 180 q7 6 14 0" stroke={CHARCOAL} strokeWidth="2.3" strokeLinecap="round" fill="none" />

      {/* ---- elderly man (right) ---- */}
      <rect x="330" y="308" width="24" height="76" rx="12" fill="#9aa8bb" />
      <rect x="358" y="308" width="24" height="76" rx="12" fill="#8b99ad" />
      <rect x="322" y="376" width="40" height="15" rx="7.5" fill="#5d6b7d" />
      <rect x="354" y="376" width="40" height="15" rx="7.5" fill="#5d6b7d" />
      <path d="M322 322 q-8-86 40-98 h18 q48 12 40 98 z" fill="#a8cfd8" />
      <path d="M338 232 h56 v11 h-56 z" fill="#93c1cc" opacity="0.8" />
      {/* arm on the walking stick */}
      <path d="M404 250 q26 22 22 52" stroke="#a8cfd8" strokeWidth="21" strokeLinecap="round" fill="none" />
      <ellipse cx="426" cy="306" rx="13" ry="11" fill={SKIN_WARM} />
      <path d="M428 306 v78" stroke="#b98c62" strokeWidth="7" strokeLinecap="round" />
      <path d="M428 306 q-16-4-16-16" stroke="#b98c62" strokeWidth="7" strokeLinecap="round" fill="none" />
      {/* head */}
      <rect x="356" y="200" width="16" height="24" rx="8" fill={SKIN_DEEP} />
      <circle cx="364" cy="180" r="31" fill={SKIN_WARM} />
      <path d="M333 176 q2-34 31-34 q29 0 31 34 q-8-16-31-16 q-23 0-31 16 z" fill={SILVER} />
      <circle cx="354" cy="182" r="9.5" fill="#ffffff" opacity="0.55" stroke={CHARCOAL} strokeWidth="2" />
      <circle cx="380" cy="182" r="9.5" fill="#ffffff" opacity="0.55" stroke={CHARCOAL} strokeWidth="2" />
      <path d="M363.5 182 h7" stroke={CHARCOAL} strokeWidth="2" />
      <path d="M357 196 q8 6 16 0" stroke={CHARCOAL} strokeWidth="2.3" strokeLinecap="round" fill="none" />

      {/* warmth motif */}
      <path
        d="M286 112 c 0-9 12-13 16-4 c 4-9 16-5 16 4 c 0 12-16 20-16 20 s-16-8-16-20 z"
        fill="#e08ea0"
        opacity="0.85"
      />
    </svg>
  );
}

/* ==========================================================================
   Handwritten prescription being read and scored
   ========================================================================== */
export function ScanDocumentScene() {
  return (
    <svg
      viewBox="0 0 520 400"
      role="img"
      aria-label="A handwritten prescription being read, with each field given a confidence score"
      xmlns="http://www.w3.org/2000/svg"
    >
      <defs>
        <linearGradient id="sd-beam" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#0d8f7d" stopOpacity="0" />
          <stop offset="55%" stopColor="#0d8f7d" stopOpacity="0.22" />
          <stop offset="100%" stopColor="#0d8f7d" stopOpacity="0" />
        </linearGradient>
      </defs>

      {/* paper */}
      <g transform="rotate(-3 168 200)">
        <rect x="42" y="40" width="252" height="320" rx="14" fill="#ffffff" stroke="#e0e8ee" strokeWidth="2" />
        <rect x="42" y="40" width="252" height="52" rx="14" fill="#f3f8fa" />
        <rect x="64" y="58" width="112" height="7" rx="3.5" fill="#9db6c3" />
        <rect x="64" y="72" width="74" height="6" rx="3" fill="#c3d3dd" />

        {/* handwriting squiggles */}
        <HandLine y={116} w={168} />
        <HandLine y={140} w={128} />
        <HandLine y={178} w={196} strong />
        <HandLine y={204} w={152} strong />
        <HandLine y={230} w={176} />
        <HandLine y={268} w={140} />
        <HandLine y={292} w={186} />

        {/* signature */}
        <path
          d="M182 324 q14-16 22 0 q8 16 20-6 q10-16 22 4"
          stroke="#5a6b7c"
          strokeWidth="2.6"
          fill="none"
          strokeLinecap="round"
        />
      </g>

      {/* scan beam */}
      <rect x="30" y="156" width="278" height="76" fill="url(#sd-beam)" />
      <rect x="30" y="192" width="278" height="3" rx="1.5" fill="#0d8f7d" opacity="0.85">
        <animate
          attributeName="y"
          values="118;300;118"
          dur="5.2s"
          repeatCount="indefinite"
        />
      </rect>

      {/* extracted fields */}
      <FieldChip y={92} label="Medication" value="Amlodipine" score="54%" tone="#b5762a" bg="#fbf1e2" />
      <FieldChip y={162} label="Dose" value="5 mg" score="62%" tone="#b5762a" bg="#fbf1e2" />
      <FieldChip y={232} label="Frequency" value="Once daily" score="54%" tone="#b5762a" bg="#fbf1e2" />
      <FieldChip y={302} label="Doctor" value="Dr. A. Kumar" score="91%" tone="#0d8f7d" bg="#e3f4f0" />

      {/* connector lines from paper to chips */}
      {[112, 182, 252, 322].map((y, index) => (
        <path
          key={y}
          d={`M296 ${[128, 196, 250, 318][index]} q22 0 22 ${y - [128, 196, 250, 318][index]} h14`}
          stroke="#d5e0e8"
          strokeWidth="1.8"
          fill="none"
          strokeDasharray="4 5"
        />
      ))}
    </svg>
  );
}

function HandLine({ y, w, strong }) {
  const stroke = strong ? '#46596b' : '#7e93a4';
  return (
    <path
      d={`M64 ${y} q10-7 20 0 t20 0 t20 0 t20 0 t20 0 t${w - 120} 0`}
      stroke={stroke}
      strokeWidth={strong ? 3 : 2.4}
      fill="none"
      strokeLinecap="round"
      opacity={strong ? 0.9 : 0.6}
    />
  );
}

function FieldChip({ y, label, value, score, tone, bg }) {
  return (
    <g transform={`translate(332 ${y})`}>
      <rect x="0" y="0" width="176" height="58" rx="14" fill="#ffffff" stroke="#e5ecf2" strokeWidth="1.6" />
      <text x="16" y="23" fontSize="10" fontWeight="700" letterSpacing="1.1" fill="#8a9aab">
        {label.toUpperCase()}
      </text>
      <text x="16" y="43" fontSize="14" fontWeight="600" fill="#0f1f2b">
        {value}
      </text>
      <rect x="118" y="18" width="44" height="22" rx="11" fill={bg} />
      <text x="140" y="33" fontSize="11" fontWeight="700" fill={tone} textAnchor="middle">
        {score}
      </text>
    </g>
  );
}

/* ==========================================================================
   Small artwork for the three input methods
   ========================================================================== */
export function TextArt() {
  return (
    <svg viewBox="0 0 132 118" aria-hidden="true" xmlns="http://www.w3.org/2000/svg">
      <rect x="18" y="14" width="96" height="86" rx="14" fill="#fff" stroke="#cfe0e6" strokeWidth="2" />
      <rect x="32" y="34" width="58" height="7" rx="3.5" fill="#12617c" opacity="0.7" />
      <rect x="32" y="50" width="68" height="6" rx="3" fill="#c9dce3" />
      <rect x="32" y="64" width="46" height="6" rx="3" fill="#c9dce3" />
      <rect x="32" y="78" width="34" height="6" rx="3" fill="#0d8f7d" opacity="0.55" />
      <g transform="rotate(38 96 86)">
        <rect x="88" y="58" width="12" height="44" rx="6" fill="#0d8f7d" />
        <path d="M88 102 h12 l-6 12 z" fill="#0b6f61" />
      </g>
    </svg>
  );
}

export function VoiceArt() {
  return (
    <svg viewBox="0 0 132 118" aria-hidden="true" xmlns="http://www.w3.org/2000/svg">
      <circle cx="66" cy="58" r="42" fill="#fff" stroke="#d8d4f0" strokeWidth="2" />
      <rect x="56" y="34" width="20" height="34" rx="10" fill="#6b60c4" />
      <path d="M46 62 a20 20 0 0 0 40 0" stroke="#6b60c4" strokeWidth="4" fill="none" strokeLinecap="round" />
      <path d="M66 82 v10" stroke="#6b60c4" strokeWidth="4" strokeLinecap="round" />
      {[[18, 14], [30, 22], [102, 22], [114, 14]].map(([x, h], index) => (
        <rect key={index} x={x} y={58 - h / 2} width="5" height={h} rx="2.5" fill="#a49cdd" />
      ))}
      <path d="M40 104 h52" stroke="#e2def5" strokeWidth="5" strokeLinecap="round" />
    </svg>
  );
}

export function ScanArt() {
  return (
    <svg viewBox="0 0 132 118" aria-hidden="true" xmlns="http://www.w3.org/2000/svg">
      <rect x="24" y="10" width="70" height="90" rx="10" fill="#fff" stroke="#e6d2cc" strokeWidth="2" transform="rotate(-6 59 55)" />
      <rect x="38" y="22" width="70" height="90" rx="10" fill="#fff" stroke="#e6d2cc" strokeWidth="2" />
      <path d="M50 44 q8-6 16 0 t16 0 t10 0" stroke="#b5762a" strokeWidth="3" fill="none" strokeLinecap="round" opacity="0.75" />
      <path d="M50 62 q8-6 16 0 t16 0" stroke="#b5762a" strokeWidth="3" fill="none" strokeLinecap="round" opacity="0.55" />
      <path d="M50 80 q8-6 16 0 t16 0 t8 0" stroke="#b5762a" strokeWidth="3" fill="none" strokeLinecap="round" opacity="0.55" />
      <g stroke="#12617c" strokeWidth="3" fill="none" strokeLinecap="round">
        <path d="M32 32 v-8 h8" />
        <path d="M114 32 v-8 h-8" />
        <path d="M32 100 v8 h8" />
        <path d="M114 100 v8 h-8" />
      </g>
    </svg>
  );
}

/* ==========================================================================
   Icons
   ========================================================================== */
const iconBase = {
  fill: 'none',
  stroke: 'currentColor',
  strokeWidth: 1.85,
  strokeLinecap: 'round',
  strokeLinejoin: 'round',
};

export function Icon({ name, size = 22 }) {
  const paths = {
    memory: (
      <>
        <path d="M12 4a4 4 0 0 0-4 4v1a3 3 0 0 0 0 6v1a4 4 0 0 0 8 0v-1a3 3 0 0 0 0-6V8a4 4 0 0 0-4-4z" />
        <path d="M12 4v16M8.5 9h7" />
      </>
    ),
    shield: (
      <>
        <path d="M12 3l7 3v6c0 4.2-2.9 7.6-7 9-4.1-1.4-7-4.8-7-9V6z" />
        <path d="M9.2 12.2l2 2 3.6-3.8" />
      </>
    ),
    spark: (
      <>
        <path d="M12 3l1.9 4.9L19 9.8l-5.1 1.9L12 16.6l-1.9-4.9L5 9.8l5.1-1.9z" />
        <path d="M18.5 15.5l.8 2 2 .8-2 .8-.8 2-.8-2-2-.8 2-.8z" />
      </>
    ),
    users: (
      <>
        <circle cx="9" cy="8" r="3.2" />
        <path d="M3.5 19.5c0-3 2.5-5 5.5-5s5.5 2 5.5 5" />
        <path d="M16 5.6a3.2 3.2 0 0 1 0 6.3M17.5 14.9c2.1.5 3.5 2.3 3.5 4.6" />
      </>
    ),
    text: (
      <>
        <path d="M4 5h16M4 10h11M4 15h13M4 20h7" />
      </>
    ),
    mic: (
      <>
        <rect x="9" y="3" width="6" height="11" rx="3" />
        <path d="M5.5 11.5a6.5 6.5 0 0 0 13 0M12 18v3" />
      </>
    ),
    scan: (
      <>
        <path d="M4 8V5.5A1.5 1.5 0 0 1 5.5 4H8M16 4h2.5A1.5 1.5 0 0 1 20 5.5V8M20 16v2.5a1.5 1.5 0 0 1-1.5 1.5H16M8 20H5.5A1.5 1.5 0 0 1 4 18.5V16" />
        <path d="M7 12h10" />
      </>
    ),
    lock: (
      <>
        <rect x="4.5" y="10" width="15" height="10" rx="2.5" />
        <path d="M8 10V7a4 4 0 0 1 8 0v3M12 14v2.5" />
      </>
    ),
    stethoscope: (
      <>
        <path d="M6 3v5a4.5 4.5 0 0 0 9 0V3" />
        <path d="M6 3H4.5M15 3h1.5" />
        <path d="M10.5 12.4v2.1a4.5 4.5 0 0 0 9 0V13" />
        <circle cx="19.5" cy="11" r="2" />
      </>
    ),
    heart: (
      <path d="M12 20s-7-4.4-7-9.3A4.2 4.2 0 0 1 12 8a4.2 4.2 0 0 1 7 2.7C19 15.6 12 20 12 20z" />
    ),
    pill: (
      <>
        <rect x="3.2" y="9" width="17.6" height="6" rx="3" transform="rotate(-45 12 12)" />
        <path d="M8.5 8.5l7 7" />
      </>
    ),
    clipboard: (
      <>
        <rect x="5" y="4.5" width="14" height="16" rx="2.5" />
        <path d="M9 4.5V3.2h6v1.3" />
        <path d="M8.5 11h7M8.5 15h5" />
      </>
    ),
    alert: (
      <>
        <path d="M12 4l8.5 15h-17z" />
        <path d="M12 10v4M12 17h.01" />
      </>
    ),
    check: <path d="M5 12.5l4.5 4.5L19 7.5" />,
    arrowRight: (
      <>
        <path d="M4.5 12h15" />
        <path d="M13.5 6l6 6-6 6" />
      </>
    ),
    arrowDown: (
      <>
        <path d="M12 4.5v15" />
        <path d="M6 13.5l6 6 6-6" />
      </>
    ),
    home: (
      <>
        <path d="M4 10.5L12 4l8 6.5V20a1 1 0 0 1-1 1h-4v-6H9v6H5a1 1 0 0 1-1-1z" />
      </>
    ),
    link: (
      <>
        <path d="M10 13.5a3.5 3.5 0 0 0 5 0l3-3a3.5 3.5 0 0 0-5-5l-1.2 1.2" />
        <path d="M14 10.5a3.5 3.5 0 0 0-5 0l-3 3a3.5 3.5 0 0 0 5 5l1.2-1.2" />
      </>
    ),
  };

  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      aria-hidden="true"
      xmlns="http://www.w3.org/2000/svg"
      {...iconBase}
    >
      {paths[name] || paths.check}
    </svg>
  );
}

export function BrandMark({ size = 22 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" aria-hidden="true" xmlns="http://www.w3.org/2000/svg">
      <path
        d="M12 3.8a4.1 4.1 0 0 0-4.1 4.1v.5A3.2 3.2 0 0 0 6.4 14v1.3a4.1 4.1 0 0 0 8.2.3"
        fill="none"
        stroke="#ffffff"
        strokeWidth="1.9"
        strokeLinecap="round"
      />
      <path
        d="M12 3.8a4.1 4.1 0 0 1 4.1 4.1v.5A3.2 3.2 0 0 1 17.6 14"
        fill="none"
        stroke="#ffffff"
        strokeWidth="1.9"
        strokeLinecap="round"
        opacity="0.65"
      />
      <path
        d="M8.6 12.2h2l1.1-2.6 1.6 5 1.1-2.4h2"
        fill="none"
        stroke="#ffffff"
        strokeWidth="1.9"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

export default HeroScene;
