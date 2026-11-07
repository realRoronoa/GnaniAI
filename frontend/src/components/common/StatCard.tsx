import React from 'react';

interface StatCardProps {
  label: string;
  value: string | number;
  subtext?: string;
  trend?: {
    value: string;
    isPositive?: boolean;
  };
  icon?: React.ReactNode;
  className?: string;
}

export const StatCard: React.FC<StatCardProps> = ({
  label,
  value,
  subtext,
  trend,
  icon,
  className = '',
}) => {
  return (
    <div className={`bg-surface border border-line rounded-lg p-5 shadow-card ${className}`}>
      <div className="flex items-center justify-between">
        <span className="text-[11px] font-semibold uppercase tracking-[0.12em] text-text-2">
          {label}
        </span>
        {icon && <span className="text-text-2">{icon}</span>}
      </div>
      <div className="mt-2 text-[30px] font-semibold text-ink font-mono tracking-tight">
        {value}
      </div>
      {(subtext || trend) && (
        <div className="mt-1 flex items-center gap-2 text-xs text-text-2">
          {trend && (
            <span
              className={`font-medium ${
                trend.isPositive ? 'text-status-approved' : 'text-status-err'
              }`}
            >
              {trend.value}
            </span>
          )}
          {subtext && <span>{subtext}</span>}
        </div>
      )}
    </div>
  );
};

