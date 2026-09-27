import { useState } from 'react';
import { Badge } from '../common/StatusBadge';
import EmptyState from '../common/EmptyState';
import { useToast } from '../common/Toast';
import { caregiverService } from '../../services/roleServices';
import { useT } from '../../i18n/LanguageContext';

export function CareTasks({ tasks = [], onDone }) {
  const t = useT();
  const toast = useToast();
  const [busyId, setBusyId] = useState(null);

  const update = async (task, status) => {
    setBusyId(task.id);
    try {
      await caregiverService.updateTask(task.id, status);
      onDone?.();
    } catch (error) {
      toast.error(error.message);
    } finally {
      setBusyId(null);
    }
  };

  if (!tasks.length) {
    return (
      <EmptyState
        icon="✅"
        title="No care tasks in this shift"
        message="Routine care tasks are generated for the hours covered by the shift."
      />
    );
  }

  return (
    <div className="stack">
      {tasks.map((task) => (
        <div className="row between" key={task.id}>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div className="row tight">
              <span className="strong">{task.title}</span>
              <Badge tone="outline">{t(task.category)}</Badge>
            </div>
            <div className="small muted">
              {t('Due {time}', { time: task.due_time || '—' })}
            </div>
          </div>
          <div className="row tight">
            <Badge
              tone={
                task.status === 'Done'
                  ? 'ok'
                  : task.status === 'Skipped'
                    ? 'warn'
                    : 'outline'
              }
            >
              {t(task.status)}
            </Badge>
            {task.status === 'Pending' && (
              <>
                <button
                  type="button"
                  className="btn btn-success btn-sm"
                  onClick={() => update(task, 'Done')}
                  disabled={busyId === task.id}
                >
                  {t('Done')}
                </button>
                <button
                  type="button"
                  className="btn btn-outline btn-sm"
                  onClick={() => update(task, 'Skipped')}
                  disabled={busyId === task.id}
                >
                  {t('Skip')}
                </button>
              </>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}

export default CareTasks;
