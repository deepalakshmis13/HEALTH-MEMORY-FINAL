import MemoryTimeline from '../health-memory/MemoryTimeline';
import { useT } from '../../i18n/LanguageContext';

export function ClinicalTimeline({ patientId, refreshKey, onOpenDocument }) {
  const t = useT();
  return (
    <MemoryTimeline
      patientId={patientId}
      title={t('Clinical Health Memory Timeline')}
      subtitle={t(
        'Longitudinal record across every source, with provenance and verification status',
      )}
      refreshKey={refreshKey}
      onOpenDocument={onOpenDocument}
    />
  );
}

export default ClinicalTimeline;
