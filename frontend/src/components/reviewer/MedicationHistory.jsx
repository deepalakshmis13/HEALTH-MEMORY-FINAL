import MemoryCard from '../health-memory/MemoryCard';
import EmptyState from '../common/EmptyState';
import { SectionCard } from '../common/PageHeader';
import { useT } from '../../i18n/LanguageContext';

export function MedicationHistory({ events = [] }) {
  const t = useT();
  return (
    <SectionCard
      title={t('Medication History')}
      subtitle={t(
        "Every medication event in this patient's health memory, newest first",
      )}
    >
      {events.length === 0 ? (
        <EmptyState
          icon="🕒"
          title={t('No medication history')}
          message={t(
            'Prescriptions, changes and administrations appear here as they are recorded.',
          )}
        />
      ) : (
        <div className="stack">
          {events.map((event) => (
            <MemoryCard key={event.id} event={event} />
          ))}
        </div>
      )}
    </SectionCard>
  );
}

export default MedicationHistory;
