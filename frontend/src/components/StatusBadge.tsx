import { cn } from '../lib/utils';

interface StatusBadgeProps {
  status: 'connected' | 'error' | 'pending' | 'needs_reauth' | 'disconnected' | string;
  className?: string;
}

const statusConfig: Record<string, { label: string; className: string }> = {
  connected: {
    label: 'Connected',
    className: 'bg-(--color-success-subtle) text-(--color-success)',
  },
  error: {
    label: 'Error',
    className: 'bg-(--color-error-subtle) text-(--color-error)',
  },
  needs_reauth: {
    label: 'Needs Re-auth',
    className: 'bg-(--color-warning-subtle) text-(--color-warning)',
  },
  disconnected: {
    label: 'Disconnected',
    className: 'bg-(--color-bg-elevated) text-(--color-text-muted)',
  },
  pending: {
    label: 'Pending',
    className: 'bg-(--color-info-subtle) text-(--color-info)',
  },
};

export function StatusBadge({ status, className }: StatusBadgeProps) {
  const config = statusConfig[status] || {
    label: status,
    className: 'bg-(--color-bg-elevated) text-(--color-text-muted)',
  };

  return (
    <span
      className={cn(
        'inline-flex items-center px-2.5 py-0.5 rounded-(--radius-full) text-xs font-medium',
        config.className,
        className
      )}
    >
      <span className={cn(
        'w-1.5 h-1.5 rounded-full mr-1.5',
        status === 'connected' ? 'bg-(--color-success)' :
        status === 'error' ? 'bg-(--color-error)' :
        status === 'needs_reauth' ? 'bg-(--color-warning)' :
        'bg-(--color-text-muted)'
      )} />
      {config.label}
    </span>
  );
}
