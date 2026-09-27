/**
 * Client-side view of the memory layer.
 *
 * The reasoning lives in the backend (consent and authorization must be
 * enforced there). These modules describe how each agent presents itself and
 * how its evidence should be read in the interface.
 */

export const PIPELINE_STEPS = [
  { key: 'consent', label: 'Checking consent' },
  { key: 'authorization', label: 'Verifying role authorization' },
  { key: 'retrieval', label: 'Finding relevant records' },
  { key: 'context', label: 'Building context' },
  { key: 'answer', label: 'Composing an evidence-backed answer' },
];

export function describeEvidence(source) {
  const bits = [];
  if (source.trust_level) bits.push(source.trust_level);
  if (source.verification_status === 'PENDING_VERIFICATION') {
    bits.push('unverified');
  }
  if (source.confidence !== null && source.confidence !== undefined) {
    bits.push(`${Math.round(source.confidence * 100)}% confidence`);
  }
  return bits.join(' · ');
}

export function groupSources(sources = []) {
  return sources.reduce((groups, source) => {
    const key = source.source_type || 'OTHER';
    groups[key] = groups[key] || [];
    groups[key].push(source);
    return groups;
  }, {});
}

export default { PIPELINE_STEPS, describeEvidence, groupSources };
