import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { AppLayout } from '@/components/layout/AppLayout';
import { Card } from '@/components/common/Card';
import { StatusBadge } from '@/components/common/StatusBadge';
import { Button } from '@/components/common/Button';
import api, { getErrorMessage } from '@/services/api';
import { Organization } from '@/types';
import { ArrowLeft, Building2, Mail, Phone, MapPin, Calendar, ShieldAlert } from 'lucide-react';

export const OrganizationDetailPage: React.FC = () => {
  const { organizationId } = useParams<{ organizationId: string }>();
  const navigate = useNavigate();
  const [organization, setOrganization] = useState<Organization | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchOrgDetails = async () => {
    setIsLoading(true);
    try {
      // In platform admin endpoints:
      const response = await api.get(`/platform/organizations`);
      const allOrgs: Organization[] = response.data;
      const found = allOrgs.find((o) => o.id === organizationId);
      if (found) {
        setOrganization(found);
      } else {
        setError('Organization not found');
      }
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchOrgDetails();
  }, [organizationId]);

  const handleToggleStatus = async () => {
    if (!organization) return;
    const newStatus = organization.status === 'ACTIVE' ? 'SUSPENDED' : 'ACTIVE';
    if (!window.confirm(`Are you sure you want to change status to ${newStatus}?`)) return;

    try {
      await api.patch(`/platform/organizations/${organization.id}/status`, {
        status: newStatus,
      });
      fetchOrgDetails();
    } catch (err) {
      alert(`Failed to update status: ${getErrorMessage(err)}`);
    }
  };

  if (isLoading) {
    return (
      <AppLayout>
        <div className="p-8 text-center text-sm text-text-2">Loading organization profile...</div>
      </AppLayout>
    );
  }

  if (error || !organization) {
    return (
      <AppLayout>
        <div className="space-y-4">
          <Button variant="outline" size="sm" onClick={() => navigate('/platform/organizations')}>
            <ArrowLeft className="w-4 h-4 mr-1" />
            Back to Organizations
          </Button>
          <div className="p-4 rounded-lg bg-status-rec-bg text-status-err text-sm font-medium">
            {error || 'Organization not found'}
          </div>
        </div>
      </AppLayout>
    );
  }

  return (
    <AppLayout>
      <div className="space-y-6">
        {/* Navigation back */}
        <Button
          variant="outline"
          size="sm"
          onClick={() => navigate('/platform/organizations')}
          leftIcon={<ArrowLeft className="w-4 h-4" />}
        >
          Back to Organizations
        </Button>

        {/* Header Block */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-4 border-b border-line">
          <div>
            <div className="flex items-center gap-3">
              <h1 className="font-serif text-3xl font-bold text-ink">{organization.name}</h1>
              <StatusBadge status={organization.status} />
            </div>
            <div className="text-xs text-text-2 mt-1">
              Organization ID: <span className="font-mono text-ink">{organization.id}</span>
            </div>
          </div>

          <Button
            variant={organization.status === 'ACTIVE' ? 'destructive' : 'primary'}
            onClick={handleToggleStatus}
          >
            {organization.status === 'ACTIVE' ? 'Suspend Organization' : 'Reactivate Organization'}
          </Button>
        </div>

        {/* Metadata Details Grid */}
        <div className="grid md:grid-cols-2 gap-6">
          <Card title="Administrative Information">
            <dl className="space-y-3 text-sm">
              <div className="flex justify-between py-1 border-b border-line/30">
                <dt className="text-text-2 font-medium">Type:</dt>
                <dd className="font-semibold text-ink">{organization.org_type}</dd>
              </div>
              <div className="flex justify-between py-1 border-b border-line/30">
                <dt className="text-text-2 font-medium">Contact Email:</dt>
                <dd className="font-mono text-ink">{organization.contact_email}</dd>
              </div>
              <div className="flex justify-between py-1 border-b border-line/30">
                <dt className="text-text-2 font-medium">Contact Phone:</dt>
                <dd className="font-mono text-ink">{organization.contact_phone || '—'}</dd>
              </div>
              <div className="flex justify-between py-1 border-b border-line/30">
                <dt className="text-text-2 font-medium">Registration Number:</dt>
                <dd className="font-mono text-ink">{organization.registration_number || '—'}</dd>
              </div>
              <div className="flex justify-between py-1">
                <dt className="text-text-2 font-medium">Onboarded Date:</dt>
                <dd className="font-mono text-ink">
                  {new Date(organization.created_at).toLocaleDateString('en-IN', {
                    day: '2-digit',
                    month: 'long',
                    year: 'numeric',
                  })}
                </dd>
              </div>
            </dl>
          </Card>

          <Card title="Clinical Data Privacy Notice">
            <div className="space-y-3 text-xs text-text-2 leading-relaxed">
              <div className="p-3 rounded-lg bg-surface-2 border border-line flex items-start gap-2.5">
                <ShieldAlert className="w-5 h-5 text-accent shrink-0 mt-0.5" />
                <div>
                  <strong className="text-ink font-semibold">Privacy Boundary Enforced</strong>
                  <p className="mt-0.5">
                    Platform Owners have zero default access to clinical transcripts, audio recordings,
                    medications, or doctor notes. Patient records belong strictly to the tenant organization.
                  </p>
                </div>
              </div>
              <p>
                Only operational logs and billing telemetry are visible here. Audit logs record all tenant administrative changes.
              </p>
            </div>
          </Card>
        </div>
      </div>
    </AppLayout>
  );
};

