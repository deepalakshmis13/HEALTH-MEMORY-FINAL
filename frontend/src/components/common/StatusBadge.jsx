import {
  SOURCE_ICONS,
  SOURCE_LABELS,
  TRUST_TONE,
  VERIFICATION_LABELS,
} from '../../utils/constants';
import { percent } from '../../utils/formatters';
import { useT } from '../../i18n/LanguageContext';

export function Badge({ tone = '', children, title, large = false }) {
  const t = useT();
  return (
    <span
      className={`badge ${tone ? `badge-${tone}` : ''} ${large ? 'badge-lg' : ''}`}
      title={t(title)}
    >
      {children}
    </span>
  );
}

/** Where a record came from — never hidden, never implied (§34, §35). */
export function SourceBadge({ sourceType, trustLevel }) {
  const t = useT();
  const label = SOURCE_LABELS[sourceType] || sourceType;
  const tone = TRUST_TONE[trustLevel] || 'outline';
  return (
    <Badge
      tone={tone}
      title={
        trustLevel ? t('Trust level: {level}', { level: t(trustLevel) }) : t(label)
      }
    >
      <span aria-hidden="true">{SOURCE_ICONS[sourceType] || '•'}</span>
      {t(trustLevel || label)}
    </Badge>
  );
}

export function VerificationBadge({ status, confidence }) {
  const t = useT();
  if (!status || status === 'NOT_REQUIRED') {
    return (
      <Badge tone="outline" title={t('Accepted directly into health memory')}>
        {t(VERIFICATION_LABELS.NOT_REQUIRED)}
      </Badge>
    );
  }
  const tone =
    status === 'PENDING_VERIFICATION'
      ? 'warn'
      : status === 'REJECTED'
        ? 'danger'
        : 'ok';
  return (
    <Badge
      tone={tone}
      title={
        confidence !== undefined && confidence !== null
          ? t('Confidence {value}', { value: percent(confidence) })
          : undefined
      }
    >
      {t(VERIFICATION_LABELS[status] || status)}
    </Badge>
  );
}

export function PriorityBadge({ priority }) {
  const t = useT();
  if (priority === 'HIGH') {
    return <Badge tone="danger">{t('High priority')}</Badge>;
  }
  return <Badge tone="warn">{t('Needs verification')}</Badge>;
}

export function SeverityDot({ severity }) {
  const t = useT();
  const map = { normal: 'ok', attention: 'warn', critical: 'danger' };
  return <Badge tone={map[severity] || 'outline'}>{t(severity)}</Badge>;
}

export default Badge;
