import React, { useEffect, useState } from 'react';
import { AppLayout } from '@/components/layout/AppLayout';
import { StatCard } from '@/components/common/StatCard';
import { Card } from '@/components/common/Card';
import { StatusBadge } from '@/components/common/StatusBadge';
import api from '@/services/api';
import { OrgEntitlements } from '@/types';
import { Users, Building2, Stethoscope, FileText, CheckCircle2 } from 'lucide-react';

export const OrgOverviewPage: React.FC = () => {
  const [entitlements, setEntitlements] = useState<OrgEntitlements | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const fetchEntitlements = async () => {
    setIsLoading(true);
    try {
      const [dashRes, subRes] = await Promise.all([
        api.get('/org/dashboard').catch(() => ({ data: null })),
        api.get('/org/subscription').catch(() => ({ data: null })),
      ]);

      const dash = dashRes.data;
      const sub = subRes.data;

      setEntitlements({
        plan_name: sub?.plan_name || dash?.plan_name || 'Professional',
        status: sub?.status || dash?.subscription_status || 'ACTIVE',
        max_doctors: sub?.limits?.max_doctors ?? 10,
        used_doctors: sub?.current_usage?.doctors ?? dash?.doctors_count ?? 0,
        max_receptionists: sub?.limits?.max_receptionists ?? 5,
        used_receptionists: sub?.current_usage?.receptionists ?? dash?.receptionists_count ?? 0,
        max_branches: sub?.limits?.max_branches ?? 3,
        used_branches: sub?.current_usage?.branches ?? dash?.branches_count ?? 0,
        max_consultations: sub?.limits?.monthly_consultation_limit ?? dash?.quota_consultations ?? 2000,
        used_consultations: sub?.current_usage?.consultations_this_month ?? dash?.consultations_month_count ?? 0,
      });
    } catch (err) {
      console.error('Failed to fetch entitlements:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchEntitlements();
  }, []);

  const calculatePercent = (used: number, max: number) => {
    if (!max || max <= 0) return 0;
    return Math.min(100, Math.round((used / max) * 100));
  };

  return (
    <AppLayout>
      <div className="space-y-6">
        {/* Header */}
        <div>
          <div className="text-xs font-semibold uppercase tracking-[0.14em] text-accent mb-1">
            ORGANIZATION CONSOLE
          </div>
          <h1 className="font-serif text-3xl font-bold text-ink">Clinic Overview</h1>
          <p className="text-sm text-text-2 mt-1">
            Operational status, subscription entitlements, and staff utilization.
          </p>
        </div>

        {/* Subscription Plan Banner */}
        <div className="bg-surface rounded-xl border border-line p-5 shadow-card flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-ink-2 text-white flex items-center justify-center font-bold">
              AS
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-serif font-bold text-lg text-ink">
                  {entitlements?.plan_name || 'Professional'} Plan
                </span>
                <StatusBadge status={entitlements?.status || 'ACTIVE'} />
              </div>
              <p className="text-xs text-text-2">
                Monthly active entitlement • Multi-branch clinical operations
              </p>
            </div>
          </div>
        </div>

        {/* Entitlements Gauge Cards Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {/* Doctors */}
          <div className="bg-surface border border-line rounded-lg p-5 shadow-card space-y-3">
            <div className="flex items-center justify-between text-xs font-semibold uppercase tracking-wider text-text-2">
              <span>Doctors Allocated</span>
              <Stethoscope className="w-4 h-4 text-status-ai" />
            </div>
            <div className="text-2xl font-bold text-ink font-mono">
              {entitlements?.used_doctors ?? 0} / {entitlements?.max_doctors ?? 10}
            </div>
            <div className="w-full bg-surface-2 h-2 rounded-full overflow-hidden">
              <div
                className="bg-status-ai h-full rounded-full transition-all duration-300"
                style={{
                  width: `${calculatePercent(
                    entitlements?.used_doctors || 0,
                    entitlements?.max_doctors || 10
                  )}%`,
                }}
              />
            </div>
          </div>

          {/* Receptionists */}
          <div className="bg-surface border border-line rounded-lg p-5 shadow-card space-y-3">
            <div className="flex items-center justify-between text-xs font-semibold uppercase tracking-wider text-text-2">
              <span>Receptionists</span>
              <Users className="w-4 h-4 text-status-approved" />
            </div>
            <div className="text-2xl font-bold text-ink font-mono">
              {entitlements?.used_receptionists ?? 0} / {entitlements?.max_receptionists ?? 5}
            </div>
            <div className="w-full bg-surface-2 h-2 rounded-full overflow-hidden">
              <div
                className="bg-status-approved h-full rounded-full transition-all duration-300"
                style={{
                  width: `${calculatePercent(
                    entitlements?.used_receptionists || 0,
                    entitlements?.max_receptionists || 5
                  )}%`,
                }}
              />
            </div>
          </div>

          {/* Branches */}
          <div className="bg-surface border border-line rounded-lg p-5 shadow-card space-y-3">
            <div className="flex items-center justify-between text-xs font-semibold uppercase tracking-wider text-text-2">
              <span>Clinic Branches</span>
              <Building2 className="w-4 h-4 text-accent" />
            </div>
            <div className="text-2xl font-bold text-ink font-mono">
              {entitlements?.used_branches ?? 0} / {entitlements?.max_branches ?? 3}
            </div>
            <div className="w-full bg-surface-2 h-2 rounded-full overflow-hidden">
              <div
                className="bg-accent h-full rounded-full transition-all duration-300"
                style={{
                  width: `${calculatePercent(
                    entitlements?.used_branches || 0,
                    entitlements?.max_branches || 3
                  )}%`,
                }}
              />
            </div>
          </div>

          {/* Consultations */}
          <div className="bg-surface border border-line rounded-lg p-5 shadow-card space-y-3">
            <div className="flex items-center justify-between text-xs font-semibold uppercase tracking-wider text-text-2">
              <span>Monthly Consultations</span>
              <FileText className="w-4 h-4 text-status-warn" />
            </div>
            <div className="text-2xl font-bold text-ink font-mono">
              {entitlements?.used_consultations ?? 0} / {entitlements?.max_consultations ?? 2500}
            </div>
            <div className="w-full bg-surface-2 h-2 rounded-full overflow-hidden">
              <div
                className="bg-status-warn h-full rounded-full transition-all duration-300"
                style={{
                  width: `${calculatePercent(
                    entitlements?.used_consultations || 0,
                    entitlements?.max_consultations || 2500
                  )}%`,
                }}
              />
            </div>
          </div>
        </div>
      </div>
    </AppLayout>
  );
};

