import React, { useEffect, useState } from 'react';
import { AppLayout } from '@/components/layout/AppLayout';
import { DataTable, Column } from '@/components/common/DataTable';
import { StatusBadge } from '@/components/common/StatusBadge';
import { Button } from '@/components/common/Button';
import { Modal } from '@/components/common/Modal';
import api, { getErrorMessage } from '@/services/api';
import { DoctorStaff, ReceptionistStaff, Branch } from '@/types';
import { Plus, Users, Stethoscope, UserCheck } from 'lucide-react';

export const OrgStaffPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'doctors' | 'receptionists'>('doctors');
  const [doctors, setDoctors] = useState<DoctorStaff[]>([]);
  const [receptionists, setReceptionists] = useState<ReceptionistStaff[]>([]);
  const [branches, setBranches] = useState<Branch[]>([]);
  const [subscriptionOverview, setSubscriptionOverview] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Modal State
  const [isDoctorModalOpen, setIsDoctorModalOpen] = useState(false);
  const [isReceptionistModalOpen, setIsReceptionistModalOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Doctor Form
  const [docName, setDocName] = useState('');
  const [docEmail, setDocEmail] = useState('');
  const [docPassword, setDocPassword] = useState('');
  const [docSpecialization, setDocSpecialization] = useState('General Physician');
  const [docRegNum, setDocRegNum] = useState('');

  // Receptionist Form
  const [recName, setRecName] = useState('');
  const [recEmail, setRecEmail] = useState('');
  const [recPassword, setRecPassword] = useState('');

  const fetchStaffData = async () => {
    setIsLoading(true);
    try {
      const [staffRes, branchesRes, subRes] = await Promise.all([
        api.get('/org/staff').catch(() => ({ data: { doctors: [], receptionists: [] } })),
        api.get('/org/branches').catch(() => ({ data: [] })),
        api.get('/org/subscription').catch(() => ({ data: null })),
      ]);
      const staffData = staffRes.data || {};
      setDoctors(Array.isArray(staffData.doctors) ? staffData.doctors : []);
      setReceptionists(Array.isArray(staffData.receptionists) ? staffData.receptionists : []);
      setBranches(Array.isArray(branchesRes.data) ? branchesRes.data : []);
      setSubscriptionOverview(subRes.data || null);
    } catch (err) {
      console.error('Failed to load staff data:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchStaffData();
  }, []);

  const handleCreateDoctor = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setError(null);

    try {
      await api.post('/org/staff/doctors', {
        full_name: docName,
        email: docEmail,
        password: docPassword,
        specialization: docSpecialization || 'General Medicine',
        qualification: 'MBBS, MD',
        registration_number: docRegNum || 'MCI-REG-001',
      });

      setIsDoctorModalOpen(false);
      setDocName('');
      setDocEmail('');
      setDocPassword('');
      setDocRegNum('');
      fetchStaffData();
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleCreateReceptionist = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setError(null);

    try {
      await api.post('/org/staff/receptionists', {
        full_name: recName,
        email: recEmail,
        password: recPassword,
      });

      setIsReceptionistModalOpen(false);
      setRecName('');
      setRecEmail('');
      setRecPassword('');
      fetchStaffData();
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setIsSubmitting(false);
    }
  };

  const doctorColumns: Column<DoctorStaff>[] = [
    {
      header: 'Doctor Name',
      render: (d) => (
        <div>
          <div className="font-semibold text-ink">{d.full_name}</div>
          <div className="text-xs text-text-2">{d.specialization || 'General Practitioner'}</div>
        </div>
      ),
    },
    {
      header: 'Email',
      accessor: 'email',
    },
    {
      header: 'Medical Reg. No.',
      render: (d) => (
        <span className="text-xs font-mono text-text-2">
          {d.registration_number || '—'}
        </span>
      ),
    },
    {
      header: 'Status',
      render: (d) => <StatusBadge status={d.is_active ? 'ACTIVE' : 'SUSPENDED'} />,
    },
  ];

  const receptionistColumns: Column<ReceptionistStaff>[] = [
    {
      header: 'Receptionist Name',
      render: (r) => (
        <div className="font-semibold text-ink">{r.full_name}</div>
      ),
    },
    {
      header: 'Email',
      accessor: 'email',
    },
    {
      header: 'Role',
      render: () => <span className="text-xs font-medium text-text-2">Front Desk & Intake</span>,
    },
    {
      header: 'Status',
      render: (r) => <StatusBadge status={r.is_active ? 'ACTIVE' : 'SUSPENDED'} />,
    },
  ];

  return (
    <AppLayout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <div className="text-xs font-semibold uppercase tracking-[0.14em] text-accent mb-1">
              ORGANIZATION CONSOLE
            </div>
            <h1 className="font-serif text-3xl font-bold text-ink">Staff Roster</h1>
            <p className="text-sm text-text-2 mt-1">
              Invite and manage clinical prescribers and reception desk operators.
            </p>
          </div>
          <div className="flex items-center gap-3">
            {activeTab === 'doctors' ? (
              <div className="flex items-center gap-2">
                {subscriptionOverview?.limits?.max_doctors && (
                  <span className="text-xs font-semibold px-2.5 py-1 rounded bg-surface-2 border border-line text-text-2 font-mono">
                    Doctors: <strong className="text-ink">{doctors.length}</strong> / {subscriptionOverview.limits.max_doctors} used
                  </span>
                )}
                <Button
                  variant="primary"
                  leftIcon={<Plus className="w-4 h-4" />}
                  disabled={subscriptionOverview?.limits?.max_doctors && doctors.length >= subscriptionOverview.limits.max_doctors}
                  onClick={() => setIsDoctorModalOpen(true)}
                >
                  {subscriptionOverview?.limits?.max_doctors && doctors.length >= subscriptionOverview.limits.max_doctors
                    ? 'Doctor Quota Reached'
                    : 'Invite Doctor'}
                </Button>
              </div>
            ) : (
              <div className="flex items-center gap-2">
                {subscriptionOverview?.limits?.max_receptionists && (
                  <span className="text-xs font-semibold px-2.5 py-1 rounded bg-surface-2 border border-line text-text-2 font-mono">
                    Reception: <strong className="text-ink">{receptionists.length}</strong> / {subscriptionOverview.limits.max_receptionists} used
                  </span>
                )}
                <Button
                  variant="primary"
                  leftIcon={<Plus className="w-4 h-4" />}
                  disabled={subscriptionOverview?.limits?.max_receptionists && receptionists.length >= subscriptionOverview.limits.max_receptionists}
                  onClick={() => setIsReceptionistModalOpen(true)}
                >
                  {subscriptionOverview?.limits?.max_receptionists && receptionists.length >= subscriptionOverview.limits.max_receptionists
                    ? 'Reception Quota Reached'
                    : 'Add Receptionist'}
                </Button>
              </div>
            )}
          </div>
        </div>

        {/* Tab Switcher */}
        <div className="flex items-center justify-between border-b border-line pb-2 flex-wrap gap-2">
          <div className="flex gap-2">
            <button
              onClick={() => setActiveTab('doctors')}
              className={`flex items-center gap-2 px-4 py-2 rounded-md text-xs font-semibold tracking-wide transition-colors ${
                activeTab === 'doctors'
                  ? 'bg-ink text-surface shadow-sm'
                  : 'text-text-2 hover:bg-surface-2'
              }`}
            >
              <Stethoscope className="w-3.5 h-3.5" />
              <span>
                Doctors ({doctors.length}
                {subscriptionOverview?.limits?.max_doctors ? ` / ${subscriptionOverview.limits.max_doctors}` : ''})
              </span>
            </button>
            <button
              onClick={() => setActiveTab('receptionists')}
              className={`flex items-center gap-2 px-4 py-2 rounded-md text-xs font-semibold tracking-wide transition-colors ${
                activeTab === 'receptionists'
                  ? 'bg-ink text-surface shadow-sm'
                  : 'text-text-2 hover:bg-surface-2'
              }`}
            >
              <Users className="w-3.5 h-3.5" />
              <span>
                Receptionists ({receptionists.length}
                {subscriptionOverview?.limits?.max_receptionists ? ` / ${subscriptionOverview.limits.max_receptionists}` : ''})
              </span>
            </button>
          </div>

          {subscriptionOverview?.plan_name && (
            <div className="text-xs text-text-2">
              Current Plan: <strong className="text-accent">{subscriptionOverview.plan_name}</strong>
            </div>
          )}
        </div>

        {/* Tables */}
        {activeTab === 'doctors' ? (
          <DataTable
            columns={doctorColumns}
            data={doctors}
            isLoading={isLoading}
            emptyMessage="No doctors enrolled in this organization yet."
          />
        ) : (
          <DataTable
            columns={receptionistColumns}
            data={receptionists}
            isLoading={isLoading}
            emptyMessage="No receptionists enrolled in this organization yet."
          />
        )}

        {/* Add Doctor Modal */}
        <Modal
          isOpen={isDoctorModalOpen}
          onClose={() => setIsDoctorModalOpen(false)}
          title="Invite Doctor to Organization"
          subtitle="Provisions a Doctor account for recording and approving clinical notes."
        >
          <form onSubmit={handleCreateDoctor} className="space-y-3.5">
            {error && (
              <div className="p-2.5 rounded bg-status-rec-bg border border-status-err/30 text-xs text-status-err">
                {error}
              </div>
            )}

            <div>
              <label className="block text-xs font-semibold text-text uppercase mb-1">
                Doctor Full Name *
              </label>
              <input
                type="text"
                required
                value={docName}
                onChange={(e) => setDocName(e.target.value)}
                placeholder="Dr. Priya Rao"
                className="w-full px-3 py-2 bg-surface border border-line rounded text-xs text-ink focus:outline-none focus:ring-1 focus:ring-ink"
              />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-semibold text-text uppercase mb-1">
                  Work Email *
                </label>
                <input
                  type="email"
                  required
                  value={docEmail}
                  onChange={(e) => setDocEmail(e.target.value)}
                  placeholder="dr.priya@clinic.in"
                  className="w-full px-3 py-2 bg-surface border border-line rounded text-xs text-ink focus:outline-none focus:ring-1 focus:ring-ink"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-text uppercase mb-1">
                  Temporary Password *
                </label>
                <input
                  type="password"
                  required
                  value={docPassword}
                  onChange={(e) => setDocPassword(e.target.value)}
                  placeholder="Min 8 characters"
                  className="w-full px-3 py-2 bg-surface border border-line rounded text-xs text-ink focus:outline-none focus:ring-1 focus:ring-ink"
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-semibold text-text uppercase mb-1">
                  Specialization
                </label>
                <input
                  type="text"
                  value={docSpecialization}
                  onChange={(e) => setDocSpecialization(e.target.value)}
                  placeholder="General Medicine / ENT"
                  className="w-full px-3 py-2 bg-surface border border-line rounded text-xs text-ink focus:outline-none focus:ring-1 focus:ring-ink"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-text uppercase mb-1">
                  Registration Number
                </label>
                <input
                  type="text"
                  value={docRegNum}
                  onChange={(e) => setDocRegNum(e.target.value)}
                  placeholder="KMC-12345"
                  className="w-full px-3 py-2 bg-surface border border-line rounded text-xs text-ink font-mono focus:outline-none focus:ring-1 focus:ring-ink"
                />
              </div>
            </div>

            <div className="pt-2 flex justify-end gap-2">
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => setIsDoctorModalOpen(false)}
              >
                Cancel
              </Button>
              <Button type="submit" variant="primary" size="sm" isLoading={isSubmitting}>
                Invite Doctor
              </Button>
            </div>
          </form>
        </Modal>

        {/* Add Receptionist Modal */}
        <Modal
          isOpen={isReceptionistModalOpen}
          onClose={() => setIsReceptionistModalOpen(false)}
          title="Add Receptionist"
          subtitle="Provisions front desk staff for patient check-ins and queue management."
        >
          <form onSubmit={handleCreateReceptionist} className="space-y-3.5">
            {error && (
              <div className="p-2.5 rounded bg-status-rec-bg border border-status-err/30 text-xs text-status-err">
                {error}
              </div>
            )}

            <div>
              <label className="block text-xs font-semibold text-text uppercase mb-1">
                Full Name *
              </label>
              <input
                type="text"
                required
                value={recName}
                onChange={(e) => setRecName(e.target.value)}
                placeholder="Ramesh Kumar"
                className="w-full px-3 py-2 bg-surface border border-line rounded text-xs text-ink focus:outline-none focus:ring-1 focus:ring-ink"
              />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-semibold text-text uppercase mb-1">
                  Work Email *
                </label>
                <input
                  type="email"
                  required
                  value={recEmail}
                  onChange={(e) => setRecEmail(e.target.value)}
                  placeholder="reception@clinic.in"
                  className="w-full px-3 py-2 bg-surface border border-line rounded text-xs text-ink focus:outline-none focus:ring-1 focus:ring-ink"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-text uppercase mb-1">
                  Temporary Password *
                </label>
                <input
                  type="password"
                  required
                  value={recPassword}
                  onChange={(e) => setRecPassword(e.target.value)}
                  placeholder="Min 8 characters"
                  className="w-full px-3 py-2 bg-surface border border-line rounded text-xs text-ink focus:outline-none focus:ring-1 focus:ring-ink"
                />
              </div>
            </div>

            <div className="pt-2 flex justify-end gap-2">
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => setIsReceptionistModalOpen(false)}
              >
                Cancel
              </Button>
              <Button type="submit" variant="primary" size="sm" isLoading={isSubmitting}>
                Add Receptionist
              </Button>
            </div>
          </form>
        </Modal>
      </div>
    </AppLayout>
  );
};

