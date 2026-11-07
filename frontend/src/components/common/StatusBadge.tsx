import React from 'react';

export type BadgeVariant =
  | 'active'
  | 'approved'
  | 'completed'
  | 'trial'
  | 'pending'
  | 'awaiting_payment'
  | 'suspended'
  | 'expired'
  | 'failed'
  | 'ai_draft'
  | 'unverified'
  | 'recording'
  | 'coming_soon';

interface StatusBadgeProps {
  status: string | BadgeVariant;
  label?: string;
  className?: string;
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status, label, className = '' }) => {
  const normalized = (status || '').toLowerCase().replace(/[\s-]/g, '_');

  let style = 'bg-surface-2 text-text-2 border-line';
  let showPulse = false;

  switch (normalized) {
    case 'active':
    case 'approved':
    case 'completed':
    case 'confirmed':
      style = 'bg-status-approved-bg text-status-approved border-status-approved/20';
      break;
    case 'trial':
      style = 'bg-ink-2/10 text-ink-2 border-ink-2/20';
      break;
    case 'pending':
    case 'awaiting_payment':
    case 'waiting':
    case 'in_progress':
    case 'arrived':
      style = 'bg-status-warn-bg text-status-warn border-status-warn/25';
      break;
    case 'suspended':
    case 'expired':
    case 'failed':
    case 'cancelled':
    case 'no_show':
      style = 'bg-status-rec-bg text-status-err border-status-err/20';
      break;
    case 'ai_draft':
    case 'ai_generated_draft':
    case 'doctor_edited_draft':
    case 'unverified':
      style = 'bg-status-ai-bg text-status-ai border-status-ai/20';
      break;
    case 'recording':
      style = 'bg-status-rec-bg text-status-rec border-status-rec/30';
      showPulse = true;
      break;
    case 'coming_soon':
      style = 'bg-accent-2 text-ink border-accent-2';
      break;
    default:
      style = 'bg-surface-2 text-text-2 border-line/50';
  }

  const displayText = label || status.replace(/_/g, ' ');

  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold uppercase tracking-wider border ${style} ${className}`}
    >
      {showPulse && <span className="w-2 h-2 rounded-full bg-status-rec animate-ping" />}
      {displayText}
    </span>
  );
};

