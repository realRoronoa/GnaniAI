import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { AppLayout } from '@/components/layout/AppLayout';
import { DataTable, Column } from '@/components/common/DataTable';
import { StatusBadge } from '@/components/common/StatusBadge';
import { Button } from '@/components/common/Button';
import { Modal } from '@/components/common/Modal';
import api, { getErrorMessage } from '@/services/api';
import { Organization, SubscriptionPlan } from '@/types';
import { Search, Plus, Building2, CheckCircle2, Ban, Eye, Sparkles, Mail, Key } from 'lucide-react';

export const OrganizationsPage: React.FC = () => {
  const navigate = useNavigate();
  const [organizations, setOrganizations] = useState<Organization[]>([]);
  const [plans, setPlans] = useState<SubscriptionPlan[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Connect & Approve Modal State
  const [isApproveModalOpen, setIsApproveModalOpen] = useState(false);
  const [selectedPendingOrg, setSelectedPendingOrg] = useState<Organization | null>(null);
  const [approvalPlanId, setApprovalPlanId] = useState('');
  const [approvalBillingCycle, setApprovalBillingCycle] = useState<'MONTHLY' | 'ANNUAL'>('MONTHLY');
  const [approvalDurationDays, setApprovalDurationDays] = useState(30);
  const [approvalCouponCode, setApprovalCouponCode] = useState('');
  const [approvalCustomPrice, setApprovalCustomPrice] = useState<string>('');
  const [approvalAdminEmail, setApprovalAdminEmail] = useState('');
  const [approvalAdminName, setApprovalAdminName] = useState('');
  const [approvalTempPassword, setApprovalTempPassword] = useState('');
  const [approvalSuccessResult, setApprovalSuccessResult] = useState<{
    admin_email: string;
    temporary_password: string;
    message: string;
  } | null>(null);

  // New Organization Form
  const [name, setName] = useState('');
  const [orgType, setOrgType] = useState('CLINIC');
  const [contactEmail, setContactEmail] = useState('');
  const [contactPhone, setContactPhone] = useState('');
  const [address, setAddress] = useState('');
  const [adminFullName, setAdminFullName] = useState('');
  const [adminPassword, setAdminPassword] = useState('');

  const fetchOrganizations = async () => {
    setIsLoading(true);
    try {
      const [orgsRes, plansRes] = await Promise.all([
        api.get('/platform/organizations'),
        api.get('/platform/plans').catch(() => ({ data: [] })),
      ]);
      setOrganizations(Array.isArray(orgsRes.data) ? orgsRes.data : []);
      const planList: SubscriptionPlan[] = Array.isArray(plansRes.data) ? plansRes.data : [];
      setPlans(planList);
      if (planList.length > 0 && !approvalPlanId) {
        setApprovalPlanId(planList[0].id);
      }
    } catch (err) {
      console.error('Failed to fetch organizations:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchOrganizations();
  }, []);

  const openApproveModal = (org: Organization) => {
    setSelectedPendingOrg(org);
    const settings = (org as any).settings_json || {};
    setApprovalAdminEmail(org.contact_email || '');
    setApprovalAdminName(settings.admin_full_name || org.name);
    setApprovalCouponCode(settings.coupon_code || '');
    setApprovalCustomPrice('');
    setApprovalTempPassword('');
    setApprovalSuccessResult(null);

    // Default plan to requested plan if found
    const reqCode = (settings.requested_plan || 'PROFESSIONAL').toUpperCase();
    const matchingPlan = plans.find((p) => p.code.toUpperCase() === reqCode);
    if (matchingPlan) {
      setApprovalPlanId(matchingPlan.id);
    } else if (plans.length > 0) {
      setApprovalPlanId(plans[0].id);
    }
    setIsApproveModalOpen(true);
  };

  const handleApproveOnboarding = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedPendingOrg) return;
    setIsSubmitting(true);
    setError(null);

    try {
      const payload: any = {
        plan_id: approvalPlanId,
        billing_cycle: approvalBillingCycle,
        duration_days: Number(approvalDurationDays),
        admin_email: approvalAdminEmail.trim(),
        admin_full_name: approvalAdminName.trim(),
      };
      if (approvalCouponCode.trim()) {
        payload.coupon_code = approvalCouponCode.trim().toUpperCase();
      }
      if (approvalCustomPrice.trim()) {
        payload.custom_final_price_inr = parseFloat(approvalCustomPrice.trim());
      }
      if (approvalTempPassword.trim()) {
        payload.temporary_password = approvalTempPassword.trim();
      }

      const res = await api.post(`/platform/organizations/${selectedPendingOrg.id}/approve-onboarding`, payload);
      setApprovalSuccessResult({
        admin_email: res.data.admin_email,
        temporary_password: res.data.temporary_password,
        message: res.data.message,
      });
      fetchOrganizations();
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleCreateOrg = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setError(null);

    try {
      await api.post('/platform/organizations', {
        name,
        org_type: orgType,
        contact_email: contactEmail,
        contact_phone: contactPhone || '9876543210',
        address: address || 'Clinic Location',
        admin_full_name: adminFullName,
        admin_email: contactEmail,
        admin_password: adminPassword,
      });

      setIsModalOpen(false);
      resetForm();
      fetchOrganizations();
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleToggleStatus = async (org: Organization, e: React.MouseEvent) => {
    e.stopPropagation();
    const newStatus = org.status === 'ACTIVE' ? 'SUSPENDED' : 'ACTIVE';
    if (!window.confirm(`Are you sure you want to mark ${org.name} as ${newStatus}?`)) {
      return;
    }

    try {
      await api.patch(`/platform/organizations/${org.id}/status`, {
        status: newStatus,
      });
      fetchOrganizations();
    } catch (err) {
      alert(`Failed to update status: ${getErrorMessage(err)}`);
    }
  };

  const resetForm = () => {
    setName('');
    setOrgType('CLINIC');
    setContactEmail('');
    setContactPhone('');
    setAddress('');
    setAdminFullName('');
    setAdminPassword('');
    setError(null);
  };

  const filteredOrgs = organizations.filter(
    (o) =>
      o.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      o.contact_email.toLowerCase().includes(searchQuery.toLowerCase())
  );

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
      header: 'Contact Info',
      render: (org) => (
        <div>
          <div className="text-sm font-mono text-ink">{org.contact_email}</div>
          {org.contact_phone && (
            <div className="text-xs text-text-2 font-mono">{org.contact_phone}</div>
          )}
        </div>
      ),
    },
    {
      header: 'Status',
      render: (org) => <StatusBadge status={org.status} />,
    },
    {
      header: 'Registered On',
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
      header: 'Actions',
      render: (org) => (
        <div className="flex items-center gap-2">
          {org.status === 'PENDING' ? (
            <Button
              variant="primary"
              size="sm"
              onClick={(e) => {
                e.stopPropagation();
                openApproveModal(org);
              }}
            >
              <Sparkles className="w-3.5 h-3.5 mr-1 text-accent-2" />
              Connect & Approve
            </Button>
          ) : (
            <>
              <Button
                variant="ghost"
                size="sm"
                onClick={(e) => {
                  e.stopPropagation();
                  navigate(`/platform/organizations/${org.id}`);
                }}
              >
                <Eye className="w-3.5 h-3.5 mr-1" />
                Details
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={(e) => handleToggleStatus(org, e)}
                className={org.status === 'ACTIVE' ? 'text-status-err hover:bg-status-rec-bg' : 'text-status-approved'}
              >
                {org.status === 'ACTIVE' ? 'Suspend' : 'Activate'}
              </Button>
            </>
          )}
        </div>
      ),
    },
  ];

  return (
    <AppLayout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <div className="text-xs font-semibold uppercase tracking-[0.14em] text-accent mb-1">
              PLATFORM CONSOLE
            </div>
            <h1 className="font-serif text-3xl font-bold text-ink">Organizations</h1>
            <p className="text-sm text-text-2 mt-1">
              Manage subscribed clinics, polyclinics, and healthcare provider accounts.
            </p>
          </div>
          <Button
            variant="primary"
            leftIcon={<Plus className="w-4 h-4" />}
            onClick={() => setIsModalOpen(true)}
          >
            Onboard Organization
          </Button>
        </div>

        {/* Pending Onboarding Inquiries (From Public Clinic Registration) */}
        {organizations.filter((o) => o.status === 'PENDING').length > 0 && (
          <div className="bg-amber-50/80 border-2 border-amber-300 rounded-xl p-5 shadow-sm space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <Sparkles className="w-5 h-5 text-amber-700" />
                <h3 className="font-serif text-lg font-bold text-amber-950">
                  Pending Onboarding Inquiries ({organizations.filter((o) => o.status === 'PENDING').length})
                </h3>
              </div>
              <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-amber-200 text-amber-900 border border-amber-300 uppercase tracking-wider">
                Action Required
              </span>
            </div>
            <p className="text-xs text-amber-900/80">
              New clinics have submitted registration inquiries via the website. Connect with their administrator, verify clinical requirements, and approve their account to provision login credentials and plan quotas.
            </p>

            <div className="grid gap-3">
              {organizations
                .filter((o) => o.status === 'PENDING')
                .map((org) => {
                  const settings = (org as any).settings_json || {};
                  return (
                    <div
                      key={org.id}
                      className="bg-surface rounded-lg p-4 border border-amber-200 flex flex-col md:flex-row md:items-center md:justify-between gap-4"
                    >
                      <div className="space-y-1">
                        <div className="flex items-center gap-2">
                          <span className="font-bold text-ink text-base">{org.name}</span>
                          <span className="text-[10px] font-semibold uppercase px-2 py-0.5 rounded bg-surface-2 text-text-2 border border-line">
                            {org.org_type}
                          </span>
                        </div>
                        <div className="text-xs text-text flex items-center gap-3 font-mono">
                          <span>Contact: <strong>{settings.admin_full_name || 'N/A'}</strong></span>
                          <span>•</span>
                          <span>Email: <strong>{org.contact_email}</strong></span>
                          {org.contact_phone && (
                            <>
                              <span>•</span>
                              <span>Phone: <strong>{org.contact_phone}</strong></span>
                            </>
                          )}
                        </div>
                        <div className="text-[11px] text-text-2 flex items-center gap-2">
                          <span>Requested Plan: <strong className="text-accent">{settings.requested_plan || 'PROFESSIONAL'}</strong></span>
                          {settings.coupon_code && (
                            <>
                              <span>•</span>
                              <span className="text-emerald-700 font-semibold font-mono">Coupon: {settings.coupon_code}</span>
                            </>
                          )}
                          <span>•</span>
                          <span>Inquired: {new Date(org.created_at).toLocaleDateString('en-IN')}</span>
                        </div>
                      </div>

                      <Button
                        variant="primary"
                        size="sm"
                        onClick={() => openApproveModal(org)}
                        leftIcon={<Sparkles className="w-3.5 h-3.5 text-accent-2" />}
                      >
                        Connect & Approve Organization
                      </Button>
                    </div>
                  );
                })}
            </div>
          </div>
        )}

        {/* Search Bar */}
        <div className="bg-surface border border-line rounded-lg p-3 flex items-center gap-2 shadow-card">
          <Search className="w-4 h-4 text-text-2" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search by clinic name or admin email..."
            className="flex-1 bg-transparent text-sm text-ink placeholder:text-text-2/60 focus:outline-none"
          />
          {searchQuery && (
            <button
              onClick={() => setSearchQuery('')}
              className="text-xs font-semibold text-text-2 hover:text-ink px-2"
            >
              Clear
            </button>
          )}
        </div>

        {/* Organizations Table */}
        <DataTable
          columns={columns}
          data={filteredOrgs}
          isLoading={isLoading}
          emptyMessage={
            searchQuery ? 'No organizations match your search query.' : 'No organizations onboarded yet.'
          }
          onRowClick={(org) => navigate(`/platform/organizations/${org.id}`)}
        />

        {/* Onboarding Modal */}
        <Modal
          isOpen={isModalOpen}
          onClose={() => {
            setIsModalOpen(false);
            resetForm();
          }}
          title="Onboard New Healthcare Organization"
          subtitle="Provisions the tenant workspace and initializes the Organization Admin account."
          maxWidth="lg"
        >
          <form onSubmit={handleCreateOrg} className="space-y-4">
            {error && (
              <div className="p-3 rounded-md bg-status-rec-bg border border-status-err/30 text-xs text-status-err font-medium">
                {error}
              </div>
            )}

            <div>
              <label className="block text-xs font-semibold text-text uppercase tracking-wider mb-1">
                Organization Name *
              </label>
              <input
                type="text"
                required
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g. Apex Multi-Specialty Clinic"
                className="w-full px-3 py-2 bg-surface-2/60 border border-line rounded text-sm text-ink focus:outline-none focus:ring-1 focus:ring-ink"
              />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-semibold text-text uppercase tracking-wider mb-1">
                  Type
                </label>
                <select
                  value={orgType}
                  onChange={(e) => setOrgType(e.target.value)}
                  className="w-full px-3 py-2 bg-surface-2/60 border border-line rounded text-sm text-ink focus:outline-none focus:ring-1 focus:ring-ink"
                >
                  <option value="CLINIC">Polyclinic / Clinic</option>
                  <option value="HOSPITAL">Hospital</option>
                  <option value="DIAGNOSTIC_CENTER">Diagnostic Center</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-text uppercase tracking-wider mb-1">
                  Contact Phone
                </label>
                <input
                  type="tel"
                  value={contactPhone}
                  onChange={(e) => setContactPhone(e.target.value)}
                  placeholder="+91 9876543210"
                  className="w-full px-3 py-2 bg-surface-2/60 border border-line rounded text-sm text-ink focus:outline-none focus:ring-1 focus:ring-ink"
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-semibold text-text uppercase tracking-wider mb-1">
                  Admin Full Name *
                </label>
                <input
                  type="text"
                  required
                  value={adminFullName}
                  onChange={(e) => setAdminFullName(e.target.value)}
                  placeholder="Dr. Anand Patel"
                  className="w-full px-3 py-2 bg-surface-2/60 border border-line rounded text-sm text-ink focus:outline-none focus:ring-1 focus:ring-ink"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-text uppercase tracking-wider mb-1">
                  Admin Work Email *
                </label>
                <input
                  type="email"
                  required
                  value={contactEmail}
                  onChange={(e) => setContactEmail(e.target.value)}
                  placeholder="admin@apexclinic.in"
                  className="w-full px-3 py-2 bg-surface-2/60 border border-line rounded text-sm text-ink focus:outline-none focus:ring-1 focus:ring-ink"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-text uppercase tracking-wider mb-1">
                Admin Initial Password *
              </label>
              <input
                type="password"
                required
                value={adminPassword}
                onChange={(e) => setAdminPassword(e.target.value)}
                placeholder="At least 8 characters"
                className="w-full px-3 py-2 bg-surface-2/60 border border-line rounded text-sm text-ink focus:outline-none focus:ring-1 focus:ring-ink"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-text uppercase tracking-wider mb-1">
                Address
              </label>
              <textarea
                rows={2}
                value={address}
                onChange={(e) => setAddress(e.target.value)}
                placeholder="Clinic street address and city..."
                className="w-full px-3 py-2 bg-surface-2/60 border border-line rounded text-sm text-ink focus:outline-none focus:ring-1 focus:ring-ink"
              />
            </div>

            <div className="pt-2 flex justify-end gap-2">
              <Button
                type="button"
                variant="outline"
                onClick={() => {
                  setIsModalOpen(false);
                  resetForm();
                }}
              >
                Cancel
              </Button>
              <Button type="submit" variant="primary" isLoading={isSubmitting}>
                Create Organization
              </Button>
            </div>
          </form>
        </Modal>

        {/* Connect & Approve Modal */}
        <Modal
          isOpen={isApproveModalOpen}
          onClose={() => {
            setIsApproveModalOpen(false);
            setSelectedPendingOrg(null);
            setApprovalSuccessResult(null);
            setError(null);
          }}
          title={selectedPendingOrg ? `Connect & Approve: ${selectedPendingOrg.name}` : 'Approve Organization'}
          subtitle="Provision active tenant subscription, primary branch location, and initial Org Admin credentials."
          maxWidth="lg"
        >
          {approvalSuccessResult ? (
            <div className="py-4 space-y-4">
              <div className="p-4 bg-emerald-50 border border-emerald-300 rounded-xl space-y-3">
                <div className="flex items-center gap-2 text-emerald-900 font-bold text-sm">
                  <CheckCircle2 className="w-5 h-5 text-emerald-600" />
                  <span>Organization Successfully Approved & Provisioned!</span>
                </div>
                <p className="text-xs text-emerald-800">
                  A welcome email with login instructions has been dispatched and logged. Provide the temporary credentials below to the clinic administrator:
                </p>

                <div className="p-3 bg-surface rounded-lg border border-emerald-200 font-mono text-xs space-y-1.5 text-ink">
                  <div><strong>Admin Email:</strong> {approvalSuccessResult.admin_email}</div>
                  <div className="flex items-center gap-2">
                    <strong>Temporary Password:</strong>
                    <span className="px-2 py-0.5 rounded bg-emerald-100 text-emerald-900 font-bold">
                      {approvalSuccessResult.temporary_password}
                    </span>
                  </div>
                </div>
              </div>

              <div className="flex justify-end pt-2">
                <Button
                  variant="primary"
                  onClick={() => {
                    setIsApproveModalOpen(false);
                    setSelectedPendingOrg(null);
                    setApprovalSuccessResult(null);
                  }}
                >
                  Done
                </Button>
              </div>
            </div>
          ) : (
            <form onSubmit={handleApproveOnboarding} className="space-y-4">
              {error && (
                <div className="p-3 rounded-md bg-status-rec-bg border border-status-err/30 text-xs text-status-err font-medium">
                  {error}
                </div>
              )}

              <div className="p-3 bg-surface-2 rounded-lg border border-line text-xs space-y-1">
                <div className="font-bold text-ink">{selectedPendingOrg?.name}</div>
                <div className="text-text-2">
                  Contact: {selectedPendingOrg?.contact_email} {selectedPendingOrg?.contact_phone && `• ${selectedPendingOrg.contact_phone}`}
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-text uppercase tracking-wider mb-1">
                    Subscription Plan *
                  </label>
                  <select
                    required
                    value={approvalPlanId}
                    onChange={(e) => setApprovalPlanId(e.target.value)}
                    className="w-full px-3 py-2 bg-surface-2/60 border border-line rounded text-sm text-ink font-medium"
                  >
                    {plans.map((p) => (
                      <option key={p.id} value={p.id}>
                        {p.name} (₹{Number(p.monthly_price).toLocaleString('en-IN')}/mo)
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-text uppercase tracking-wider mb-1">
                    Billing Cycle
                  </label>
                  <select
                    value={approvalBillingCycle}
                    onChange={(e) => setApprovalBillingCycle(e.target.value as any)}
                    className="w-full px-3 py-2 bg-surface-2/60 border border-line rounded text-sm text-ink"
                  >
                    <option value="MONTHLY">Monthly</option>
                    <option value="ANNUAL">Annual</option>
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-text uppercase tracking-wider mb-1">
                    Coupon Code (Optional)
                  </label>
                  <input
                    type="text"
                    value={approvalCouponCode}
                    onChange={(e) => setApprovalCouponCode(e.target.value.toUpperCase())}
                    placeholder="e.g. WELCOME20"
                    className="w-full px-3 py-2 bg-surface-2/60 border border-line rounded text-sm font-mono text-ink uppercase"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-text uppercase tracking-wider mb-1">
                    Custom Price Override (₹, Optional)
                  </label>
                  <input
                    type="number"
                    min={0}
                    value={approvalCustomPrice}
                    onChange={(e) => setApprovalCustomPrice(e.target.value)}
                    placeholder="Leave empty for plan rate"
                    className="w-full px-3 py-2 bg-surface-2/60 border border-line rounded text-sm font-mono text-ink"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-text uppercase tracking-wider mb-1">
                    Admin Full Name *
                  </label>
                  <input
                    type="text"
                    required
                    value={approvalAdminName}
                    onChange={(e) => setApprovalAdminName(e.target.value)}
                    className="w-full px-3 py-2 bg-surface-2/60 border border-line rounded text-sm text-ink"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-text uppercase tracking-wider mb-1">
                    Admin Work Email *
                  </label>
                  <input
                    type="email"
                    required
                    value={approvalAdminEmail}
                    onChange={(e) => setApprovalAdminEmail(e.target.value)}
                    className="w-full px-3 py-2 bg-surface-2/60 border border-line rounded text-sm text-ink"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-text uppercase tracking-wider mb-1">
                  Initial Password (Optional — auto-generated if blank)
                </label>
                <input
                  type="text"
                  value={approvalTempPassword}
                  onChange={(e) => setApprovalTempPassword(e.target.value)}
                  placeholder="Leave empty to auto-generate secure 12-char password"
                  className="w-full px-3 py-2 bg-surface-2/60 border border-line rounded text-sm font-mono text-ink"
                />
              </div>

              <div className="pt-2 flex justify-end gap-2">
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => {
                    setIsApproveModalOpen(false);
                    setSelectedPendingOrg(null);
                  }}
                >
                  Cancel
                </Button>
                <Button type="submit" variant="primary" isLoading={isSubmitting}>
                  Approve & Provision Account
                </Button>
              </div>
            </form>
          )}
        </Modal>
      </div>
    </AppLayout>
  );
};

