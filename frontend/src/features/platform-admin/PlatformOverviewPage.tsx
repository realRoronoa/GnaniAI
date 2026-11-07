import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { AppLayout } from '@/components/layout/AppLayout';
import { StatCard } from '@/components/common/StatCard';
import { Card } from '@/components/common/Card';
import { DataTable, Column } from '@/components/common/DataTable';
import { StatusBadge } from '@/components/common/StatusBadge';
import { Button } from '@/components/common/Button';
import api from '@/services/api';
import { Organization, PlatformMetrics } from '@/types';
import { Building2, CreditCard, Stethoscope, FileText, ArrowUpRight, Plus } from 'lucide-react';

export const PlatformOverviewPage: React.FC = () => {
  const navigate = useNavigate();
  const [metrics, setMetrics] = useState<PlatformMetrics | null>(null);
  const [recentOrgs, setRecentOrgs] = useState<Organization[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  const fetchOverview = async () => {
    setIsLoading(true);
    try {
      const [metricsRes, orgsRes] = await Promise.all([
        api.get('/platform/overview').catch(() => ({
          data: {
            total_organizations: 0,
            active_subscriptions: 0,
            total_doctors: 0,
            total_consultations: 0,
            total_consultations_month: 0,
          },
        })),
        api.get('/platform/organizations').catch(() => ({ data: [] })),
      ]);

      const data = metricsRes.data;
      setMetrics({
        ...data,
        total_consultations_month: data.total_consultations_month ?? data.total_consultations ?? 0,
      });
      setRecentOrgs(Array.isArray(orgsRes.data) ? orgsRes.data.slice(0, 5) : []);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchOverview();
  }, []);

  const columns: Column<Organization>[] = [
    {
      header: 'Organization',
      render: (org) => (
        <div>
          <div className="font-semibold text-ink">{org.name}</div>
          <div className="text-xs text-text-2">{org.org_type}</div>
        </div>
      ),
    },
    {
      header: 'Contact Email',
      accessor: 'contact_email',
    },
    {
      header: 'Status',
      render: (org) => <StatusBadge status={org.status} />,
    },
    {
      header: 'Created Date',
      render: (org) => (
        <span className="text-xs font-mono text-text-2">
          {new Date(org.created_at).toLocaleDateString('en-IN', {
            day: '2-digit',
            month: 'short',
            year: 'numeric',
          })}
        </span>
      ),
    },
    {
      header: '',
      render: (org) => (
        <Button
          variant="ghost"
          size="sm"
          onClick={() => navigate(`/platform/organizations/${org.id}`)}
          rightIcon={<ArrowUpRight className="w-3.5 h-3.5" />}
        >
          View
        </Button>
      ),
    },
  ];

  return (
    <AppLayout>
      <div className="space-y-6">
        {/* Header */}
        <div>
          <div className="text-xs font-semibold uppercase tracking-[0.14em] text-accent mb-1">
            PLATFORM CONSOLE
          </div>
          <h1 className="font-serif text-3xl font-bold text-ink">Overview</h1>
          <p className="text-sm text-text-2 mt-1">
            System telemetry and high-level health metrics across all tenant organizations.
          </p>
        </div>

        {/* 4 KPI Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard
            label="Total Organizations"
            value={metrics?.total_organizations ?? '—'}
            subtext="Clinics & Hospitals"
            icon={<Building2 className="w-5 h-5 text-accent" />}
          />
          <StatCard
            label="Active Subscriptions"
            value={metrics?.active_subscriptions ?? '—'}
            subtext="Paying Tenants"
            icon={<CreditCard className="w-5 h-5 text-status-approved" />}
          />
          <StatCard
            label="Registered Doctors"
            value={metrics?.total_doctors ?? '—'}
            subtext="Active Prescribers"
            icon={<Stethoscope className="w-5 h-5 text-status-ai" />}
          />
          <StatCard
            label="Consultations (Month)"
            value={metrics?.total_consultations_month ?? '—'}
            subtext="Generated Transcripts"
            icon={<FileText className="w-5 h-5 text-status-warn" />}
          />
        </div>

        {/* Recent Organizations Section */}
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-base font-semibold text-ink">Recently Onboarded Organizations</h2>
            <Button
              variant="outline"
              size="sm"
              onClick={() => navigate('/platform/organizations')}
            >
              View All Organizations
            </Button>
          </div>

          <DataTable
            columns={columns}
            data={recentOrgs}
            isLoading={isLoading}
            emptyMessage="No organizations registered yet."
            onRowClick={(org) => navigate(`/platform/organizations/${org.id}`)}
          />
        </div>
      </div>
    </AppLayout>
  );
};

