import { cn } from '../lib/utils';

export function ScoreBadge({ score }: { score: number | null | undefined }) {
  if (score == null) {
    return (
      <span className="inline-flex items-center px-2.5 py-0.5 rounded-(--radius-full) text-xs font-medium bg-(--color-bg-elevated) text-(--color-text-muted)">
        Pending
      </span>
    );
  }

  const getColor = () => {
    if (score >= 80) return 'bg-(--color-success-bg) text-(--color-success)';
    if (score >= 60) return 'bg-(--color-info-bg) text-(--color-info)';
    if (score >= 40) return 'bg-(--color-warning-bg) text-(--color-warning)';
    return 'bg-(--color-error-bg) text-(--color-error)';
  };

  return (
    <span className={cn(
      'inline-flex items-center px-2.5 py-0.5 rounded-(--radius-full) text-xs font-bold tabular-nums',
      getColor()
    )}>
      {Math.round(score)}%
    </span>
  );
}
