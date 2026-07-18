import { cn } from '../lib/utils';

interface StatusBadgeProps {
  status: 'connected' | 'error' | 'pending' | 'needs_reauth' | 'disconnected' | string;
  className?: string;
}

const statusConfig: Record<string, { label: string; dotClass: string; badgeClass: string }> = {
  connected: {
    label: 'Connected',
    dotClass: 'bg-(--color-success)',
    badgeClass: 'bg-(--color-success-bg) text-(--color-success)',
  },
  error: {
    label: 'Error',
    dotClass: 'bg-(--color-error)',
    badgeClass: 'bg-(--color-error-bg) text-(--color-error)',
  },
  needs_reauth: {
    label: 'Needs Re-auth',
    dotClass: 'bg-(--color-warning)',
    badgeClass: 'bg-(--color-warning-bg) text-(--color-warning)',
  },
  disconnected: {
    label: 'Disconnected',
    dotClass: 'bg-(--color-text-muted)',
    badgeClass: 'bg-(--color-bg-elevated) text-(--color-text-secondary)',
  },
  pending: {
    label: 'Pending',
    dotClass: 'bg-(--color-info)',
    badgeClass: 'bg-(--color-info-bg) text-(--color-info)',
  },
};

export function StatusBadge({ status, className }: StatusBadgeProps) {
  const config = statusConfig[status] || {
    label: status,
    dotClass: 'bg-(--color-text-muted)',
    badgeClass: 'bg-(--color-bg-elevated) text-(--color-text-secondary)',
  };

  return (
    <span
      className={cn(
        'inline-flex items-center px-2.5 py-0.5 rounded-(--radius-full) text-xs font-medium',
        config.badgeClass,
        className
      )}
    >
      <span className={cn('w-1.5 h-1.5 rounded-full mr-1.5', config.dotClass)} />
      {config.label}
    </span>
  );
}
