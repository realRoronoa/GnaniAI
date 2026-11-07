import React, { useEffect, useState } from 'react';
import { AppLayout } from '@/components/layout/AppLayout';
import { DataTable, Column } from '@/components/common/DataTable';
import { StatusBadge } from '@/components/common/StatusBadge';
import { Button } from '@/components/common/Button';
import { Modal } from '@/components/common/Modal';
import api, { getErrorMessage } from '@/services/api';
import { Branch } from '@/types';
import { Plus, GitBranch, MapPin, Phone } from 'lucide-react';

export const OrgBranchesPage: React.FC = () => {
  const [branches, setBranches] = useState<Branch[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Form State
  const [name, setName] = useState('');
  const [branchCode, setBranchCode] = useState('');
  const [city, setCity] = useState('');
  const [state, setState] = useState('');
  const [address, setAddress] = useState('');
  const [phone, setPhone] = useState('');

  const fetchBranches = async () => {
    setIsLoading(true);
    try {
      const response = await api.get('/org/branches');
      setBranches(Array.isArray(response.data) ? response.data : []);
    } catch (err) {
      console.error('Failed to fetch branches:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchBranches();
  }, []);

  const handleCreateBranch = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setError(null);

    try {
      await api.post('/org/branches', {
        name,
        branch_code: branchCode,
        city: city || null,
        state: state || null,
        address: address || null,
        phone: phone || null,
      });

      setIsModalOpen(false);
      resetForm();
      fetchBranches();
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setIsSubmitting(false);
    }
  };

  const resetForm = () => {
    setName('');
    setBranchCode('');
    setCity('');
    setState('');
    setAddress('');
    setPhone('');
    setError(null);
  };

  const columns: Column<Branch>[] = [
    {
      header: 'Branch Name',
      render: (b) => (
        <div>
          <div className="font-semibold text-ink">{b.name}</div>
          <div className="text-xs font-mono text-text-2">Code: {b.branch_code}</div>
        </div>
      ),
    },
    {
      header: 'Location',
      render: (b) => (
        <div className="text-xs text-text-2">
          {b.city && b.state ? `${b.city}, ${b.state}` : b.city || b.address || '—'}
        </div>
      ),
    },
    {
      header: 'Contact Phone',
      render: (b) => (
        <span className="text-xs font-mono text-ink">{b.phone || '—'}</span>
      ),
    },
    {
      header: 'Status',
      render: (b) => <StatusBadge status={b.is_active ? 'ACTIVE' : 'SUSPENDED'} />,
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
            <h1 className="font-serif text-3xl font-bold text-ink">Clinic Branches</h1>
            <p className="text-sm text-text-2 mt-1">
              Manage physical clinic locations, OPD desks, and consultation facilities.
            </p>
          </div>
          <Button
            variant="primary"
            leftIcon={<Plus className="w-4 h-4" />}
            onClick={() => setIsModalOpen(true)}
          >
            Add Branch Location
          </Button>
        </div>

        {/* Branches Table */}
        <DataTable
          columns={columns}
          data={branches}
          isLoading={isLoading}
          emptyMessage="No branches configured yet."
        />

        {/* Add Branch Modal */}
        <Modal
          isOpen={isModalOpen}
          onClose={() => {
            setIsModalOpen(false);
            resetForm();
          }}
          title="Add New Clinic Branch"
          subtitle="Configure a physical location for patient queueing and doctor scheduling."
        >
          <form onSubmit={handleCreateBranch} className="space-y-3.5">
            {error && (
              <div className="p-2.5 rounded bg-status-rec-bg border border-status-err/30 text-xs text-status-err">
                {error}
              </div>
            )}

            <div>
              <label className="block text-xs font-semibold text-text uppercase mb-1">
                Branch Name *
              </label>
              <input
                type="text"
                required
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g. Indiranagar Main Clinic"
                className="w-full px-3 py-2 bg-surface border border-line rounded text-xs text-ink focus:outline-none focus:ring-1 focus:ring-ink"
              />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-semibold text-text uppercase mb-1">
                  Branch Code *
                </label>
                <input
                  type="text"
                  required
                  value={branchCode}
                  onChange={(e) => setBranchCode(e.target.value)}
                  placeholder="e.g. BLR-IND-01"
                  className="w-full px-3 py-2 bg-surface border border-line rounded text-xs text-ink font-mono focus:outline-none focus:ring-1 focus:ring-ink"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-text uppercase mb-1">
                  Phone
                </label>
                <input
                  type="tel"
                  value={phone}
                  onChange={(e) => setPhone(e.target.value)}
                  placeholder="+91 80 12345678"
                  className="w-full px-3 py-2 bg-surface border border-line rounded text-xs text-ink focus:outline-none focus:ring-1 focus:ring-ink"
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-semibold text-text uppercase mb-1">
                  City
                </label>
                <input
                  type="text"
                  value={city}
                  onChange={(e) => setCity(e.target.value)}
                  placeholder="Bengaluru"
                  className="w-full px-3 py-2 bg-surface border border-line rounded text-xs text-ink focus:outline-none focus:ring-1 focus:ring-ink"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-text uppercase mb-1">
                  State
                </label>
                <input
                  type="text"
                  value={state}
                  onChange={(e) => setState(e.target.value)}
                  placeholder="Karnataka"
                  className="w-full px-3 py-2 bg-surface border border-line rounded text-xs text-ink focus:outline-none focus:ring-1 focus:ring-ink"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-text uppercase mb-1">
                Full Street Address
              </label>
              <textarea
                rows={2}
                value={address}
                onChange={(e) => setAddress(e.target.value)}
                placeholder="100 Feet Road, HAL 2nd Stage..."
                className="w-full px-3 py-2 bg-surface border border-line rounded text-xs text-ink focus:outline-none focus:ring-1 focus:ring-ink"
              />
            </div>

            <div className="pt-2 flex justify-end gap-2">
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => setIsModalOpen(false)}
              >
                Cancel
              </Button>
              <Button type="submit" variant="primary" size="sm" isLoading={isSubmitting}>
                Save Branch
              </Button>
            </div>
          </form>
        </Modal>
      </div>
    </AppLayout>
  );
};

