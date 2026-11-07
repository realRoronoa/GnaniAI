import React, { useEffect, useState } from 'react';
import { AppLayout } from '@/components/layout/AppLayout';
import { DataTable, Column } from '@/components/common/DataTable';
import { StatusBadge } from '@/components/common/StatusBadge';
import { Button } from '@/components/common/Button';
import { Modal } from '@/components/common/Modal';
import api, { getErrorMessage } from '@/services/api';
import { Patient, DuplicatePatientMatch } from '@/types';
import { Search, Plus, UserPlus, AlertTriangle, ShieldCheck, Edit, Phone, Mail, FileText } from 'lucide-react';

export const PatientsDirectoryPage: React.FC = () => {
  const [patients, setPatients] = useState<Patient[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [isLoading, setIsLoading] = useState(true);

  // Registration Modal State
  const [isRegModalOpen, setIsRegModalOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [regError, setRegError] = useState<string | null>(null);

  // Form Fields
  const [fullName, setFullName] = useState('');
  const [ageYears, setAgeYears] = useState<number | ''>('');
  const [gender, setGender] = useState('MALE');
  const [mobileNumber, setMobileNumber] = useState('');
  const [email, setEmail] = useState('');
  const [preferredLang, setPreferredLang] = useState('hi');
  const [allergies, setAllergies] = useState('');
  const [adminNotes, setAdminNotes] = useState('');

  // Duplicate Check State
  const [dupMatches, setDupMatches] = useState<DuplicatePatientMatch[]>([]);
  const [isCheckingDups, setIsCheckingDups] = useState(false);
  const [acknowledgedDuplicate, setAcknowledgedDuplicate] = useState(false);

  // Edit Patient State
  const [editingPatient, setEditingPatient] = useState<Patient | null>(null);
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);

  const fetchPatients = async (query = '') => {
    setIsLoading(true);
    try {
      const response = await api.get('/patients', {
        params: query ? { q: query } : {},
      });
      setPatients(Array.isArray(response.data) ? response.data : []);
    } catch (err) {
      console.error('Failed to load patients:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchPatients(searchQuery);
  }, []);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    fetchPatients(searchQuery);
  };

  // Real-time duplicate check when phone or name changes
  useEffect(() => {
    if (!isRegModalOpen) return;
    const cleanPhone = mobileNumber.trim();
    if (cleanPhone.length >= 10 || fullName.trim().length >= 3) {
      const timer = setTimeout(async () => {
        setIsCheckingDups(true);
        try {
          const res = await api.get('/patients/check-duplicates', {
            params: {
              mobile_number: cleanPhone.length >= 10 ? cleanPhone : undefined,
              full_name: fullName.trim().length >= 3 ? fullName.trim() : undefined,
            },
          });
          setDupMatches(res.data.potential_matches || res.data.matches || []);
        } catch {
          setDupMatches([]);
        } finally {
          setIsCheckingDups(false);
        }
      }, 400);
      return () => clearTimeout(timer);
    } else {
      setDupMatches([]);
    }
  }, [mobileNumber, fullName, isRegModalOpen]);

  const handleRegisterPatient = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setRegError(null);

    try {
      await api.post('/patients', {
        full_name: fullName,
        age_years: ageYears !== '' ? Number(ageYears) : null,
        gender,
        mobile_number: mobileNumber,
        email: email || null,
        preferred_language: preferredLang,
        allergies_summary: allergies || null,
        administrative_notes: adminNotes || null,
      });

      setIsRegModalOpen(false);
      resetRegForm();
      fetchPatients(searchQuery);
    } catch (err) {
      setRegError(getErrorMessage(err));
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleUpdatePatient = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingPatient) return;
    setIsSubmitting(true);

    try {
      await api.patch(`/patients/${editingPatient.id}`, {
        full_name: editingPatient.full_name,
        mobile_number: editingPatient.mobile_number,
        email: editingPatient.email || null,
        preferred_language: editingPatient.preferred_language,
        allergies_summary: editingPatient.allergies_summary || null,
        administrative_notes: editingPatient.administrative_notes || null,
      });

      setIsEditModalOpen(false);
      setEditingPatient(null);
      fetchPatients(searchQuery);
    } catch (err) {
      alert(`Update failed: ${getErrorMessage(err)}`);
    } finally {
      setIsSubmitting(false);
    }
  };

  const resetRegForm = () => {
    setFullName('');
    setAgeYears('');
    setGender('MALE');
    setMobileNumber('');
    setEmail('');
    setPreferredLang('hi');
    setAllergies('');
    setAdminNotes('');
    setDupMatches([]);
    setAcknowledgedDuplicate(false);
    setRegError(null);
  };

  const columns: Column<Patient>[] = [
    {
      header: 'Patient Identifier',
      render: (p) => (
        <div>
          <span className="font-mono font-bold text-ink text-sm">
            {p.patient_identifier}
          </span>
          <div className="text-xs text-text-2">
            Reg: {new Date(p.created_at).toLocaleDateString('en-IN', { month: 'short', day: 'numeric', year: 'numeric' })}
          </div>
        </div>
      ),
    },
    {
      header: 'Full Name & Demographics',
      render: (p) => (
        <div>
          <div className="font-semibold text-ink text-sm">{p.full_name}</div>
          <div className="text-xs text-text-2">
            {p.gender} • {p.age_years ? `${p.age_years} yrs` : 'Age N/A'} • Lang:{' '}
            <span className="uppercase font-semibold text-ink">{p.preferred_language}</span>
          </div>
        </div>
      ),
    },
    {
      header: 'Contact Info',
      render: (p) => (
        <div className="text-xs font-mono space-y-0.5">
          <div className="flex items-center gap-1.5 text-ink">
            <Phone className="w-3.5 h-3.5 text-text-2" />
            <span>{p.mobile_number}</span>
          </div>
          {p.email && (
            <div className="flex items-center gap-1.5 text-text-2">
              <Mail className="w-3.5 h-3.5 text-text-2" />
              <span>{p.email}</span>
            </div>
          )}
        </div>
      ),
    },
    {
      header: 'Allergies & Alerts',
      render: (p) => (
        <div>
          {p.allergies_summary ? (
            <span className="inline-block text-xs font-semibold px-2 py-0.5 rounded bg-status-rec-bg text-status-err border border-status-err/20">
              {p.allergies_summary}
            </span>
          ) : (
            <span className="text-xs text-text-2 font-medium">No Known Allergies</span>
          )}
          <div className="text-[10px] text-text-2 uppercase mt-0.5">
            Status: {p.allergy_verification_status}
          </div>
        </div>
      ),
    },
    {
      header: 'Actions',
      render: (p) => (
        <div className="flex items-center gap-2">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => {
              setEditingPatient(p);
              setIsEditModalOpen(true);
            }}
          >
            <Edit className="w-3.5 h-3.5 mr-1" />
            Edit
          </Button>
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
              RECEPTION CONSOLE
            </div>
            <h1 className="font-serif text-3xl font-bold text-ink">Patient Directory</h1>
            <p className="text-sm text-text-2 mt-1">
              Search existing clinic patient records, view visit histories, or register new UHIDs.
            </p>
          </div>
          <Button
            variant="primary"
            leftIcon={<UserPlus className="w-4 h-4" />}
            onClick={() => setIsRegModalOpen(true)}
          >
            Register New Patient
          </Button>
        </div>

        {/* Search Bar */}
        <form onSubmit={handleSearchSubmit} className="bg-surface border border-line rounded-lg p-3 flex items-center gap-2 shadow-card">
          <Search className="w-4 h-4 text-text-2" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search by Name, UHID (e.g. ARC-2026-0001), or 10-digit mobile number..."
            className="flex-1 bg-transparent text-sm text-ink placeholder:text-text-2/60 focus:outline-none"
          />
          <Button type="submit" variant="outline" size="sm">
            Search
          </Button>
          {searchQuery && (
            <button
              type="button"
              onClick={() => {
                setSearchQuery('');
                fetchPatients('');
              }}
              className="text-xs text-text-2 hover:text-ink px-2 font-medium"
            >
              Clear
            </button>
          )}
        </form>

        {/* Patients Table */}
        <DataTable
          columns={columns}
          data={patients}
          isLoading={isLoading}
          emptyMessage="No patient records found matching your search."
        />

        {/* Registration Modal */}
        <Modal
          isOpen={isRegModalOpen}
          onClose={() => {
            setIsRegModalOpen(false);
            resetRegForm();
          }}
          title="Register New Patient"
          subtitle="Generates an official clinic UHID record. Patients are records and do not log in."
          maxWidth="lg"
        >
          <form onSubmit={handleRegisterPatient} className="space-y-4">
            {regError && (
              <div className="p-3 rounded-md bg-status-rec-bg border border-status-err/30 text-xs text-status-err font-medium">
                {regError}
              </div>
            )}

            {/* Non-Blocking Duplicate Warning Card */}
            {dupMatches.length > 0 && (
              <div className="p-3.5 rounded-lg bg-status-warn-bg border border-status-warn/30 space-y-2">
                <div className="flex items-center gap-2 text-xs font-bold text-status-warn uppercase tracking-wider">
                  <AlertTriangle className="w-4 h-4 shrink-0" />
                  <span>Existing Patient(s) Found ({dupMatches.length})</span>
                </div>
                <p className="text-xs text-text-2">
                  Patients often share family mobile numbers in India. Verify whether this is an existing
                  patient or a new family member before creating a new record.
                </p>
                <div className="divide-y divide-line/40 max-h-36 overflow-y-auto bg-surface/80 rounded p-2 text-xs">
                  {dupMatches.map((m) => (
                    <div key={m.id} className="py-1.5 flex justify-between items-center">
                      <div>
                        <strong className="text-ink">{m.full_name}</strong> ({m.gender}, {m.age_years || 'N/A'}y)
                        <div className="font-mono text-[11px] text-text-2">{m.patient_identifier} • {m.mobile_number}</div>
                      </div>
                      <span className="text-[10px] font-semibold text-status-warn bg-status-warn-bg px-2 py-0.5 rounded">
                        {m.match_reason || (m.match_reasons && m.match_reasons.join(', ')) || 'Potential match'}
                      </span>
                    </div>
                  ))}
                </div>
                <label className="flex items-center gap-2 pt-1 text-xs font-semibold text-ink cursor-pointer">
                  <input
                    type="checkbox"
                    checked={acknowledgedDuplicate}
                    onChange={(e) => setAcknowledgedDuplicate(e.target.checked)}
                    className="rounded border-line text-accent"
                  />
                  <span>Confirm: This is a distinct individual / family member needing a new UHID</span>
                </label>
              </div>
            )}

            <div>
              <label className="block text-xs font-semibold text-text uppercase tracking-wider mb-1">
                Patient Full Name *
              </label>
              <input
                type="text"
                required
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                placeholder="e.g. Ramesh Verma"
                className="w-full px-3 py-2 bg-surface-2/60 border border-line rounded text-sm text-ink focus:outline-none focus:ring-1 focus:ring-ink"
              />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-semibold text-text uppercase tracking-wider mb-1">
                  Age (Years)
                </label>
                <input
                  type="number"
                  min={0}
                  max={125}
                  value={ageYears}
                  onChange={(e) => setAgeYears(e.target.value ? Number(e.target.value) : '')}
                  placeholder="e.g. 45"
                  className="w-full px-3 py-2 bg-surface-2/60 border border-line rounded text-sm text-ink focus:outline-none focus:ring-1 focus:ring-ink"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-text uppercase tracking-wider mb-1">
                  Gender *
                </label>
                <select
                  value={gender}
                  onChange={(e) => setGender(e.target.value)}
                  className="w-full px-3 py-2 bg-surface-2/60 border border-line rounded text-sm text-ink focus:outline-none focus:ring-1 focus:ring-ink"
                >
                  <option value="MALE">Male</option>
                  <option value="FEMALE">Female</option>
                  <option value="OTHER">Other</option>
                </select>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-semibold text-text uppercase tracking-wider mb-1">
                  Mobile Number *
                </label>
                <input
                  type="tel"
                  required
                  value={mobileNumber}
                  onChange={(e) => setMobileNumber(e.target.value)}
                  placeholder="9876543210"
                  className="w-full px-3 py-2 bg-surface-2/60 border border-line rounded text-sm text-ink font-mono focus:outline-none focus:ring-1 focus:ring-ink"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-text uppercase tracking-wider mb-1">
                  Preferred Language *
                </label>
                <select
                  value={preferredLang}
                  onChange={(e) => setPreferredLang(e.target.value)}
                  className="w-full px-3 py-2 bg-surface-2/60 border border-line rounded text-sm text-ink focus:outline-none focus:ring-1 focus:ring-ink"
                >
                  <option value="en">English</option>
                  <option value="hi">Hindi (हिंदी)</option>
                  <option value="ta">Tamil (தமிழ்)</option>
                  <option value="te">Telugu (తెలుగు)</option>
                  <option value="kn">Kannada (ಕನ್ನಡ)</option>
                  <option value="ml">Malayalam (മലയാളം)</option>
                  <option value="mr">Marathi (मराठी)</option>
                  <option value="bn">Bengali (বাংলা)</option>
                  <option value="gu">Gujarati (ગુજરાતી)</option>
                </select>
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-text uppercase tracking-wider mb-1">
                Email Address (Optional)
              </label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="patient@example.in"
                className="w-full px-3 py-2 bg-surface-2/60 border border-line rounded text-sm text-ink focus:outline-none focus:ring-1 focus:ring-ink"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-text uppercase tracking-wider mb-1">
                Known Drug / Food Allergies
              </label>
              <input
                type="text"
                value={allergies}
                onChange={(e) => setAllergies(e.target.value)}
                placeholder="e.g. Penicillin, Sulfa drugs, Peanuts (or leave empty)"
                className="w-full px-3 py-2 bg-surface-2/60 border border-line rounded text-sm text-ink focus:outline-none focus:ring-1 focus:ring-ink"
              />
            </div>

            <div className="pt-2 flex justify-end gap-2">
              <Button
                type="button"
                variant="outline"
                onClick={() => {
                  setIsRegModalOpen(false);
                  resetRegForm();
                }}
              >
                Cancel
              </Button>
              <Button
                type="submit"
                variant="primary"
                isLoading={isSubmitting}
                disabled={dupMatches.length > 0 && !acknowledgedDuplicate}
              >
                Register Patient & Generate UHID
              </Button>
            </div>
          </form>
        </Modal>

        {/* Edit Modal */}
        {editingPatient && (
          <Modal
            isOpen={isEditModalOpen}
            onClose={() => {
              setIsEditModalOpen(false);
              setEditingPatient(null);
            }}
            title="Edit Patient Details"
            subtitle={`UHID: ${editingPatient.patient_identifier}`}
          >
            <form onSubmit={handleUpdatePatient} className="space-y-3.5">
              <div>
                <label className="block text-xs font-semibold text-text uppercase mb-1">
                  Full Name
                </label>
                <input
                  type="text"
                  required
                  value={editingPatient.full_name}
                  onChange={(e) =>
                    setEditingPatient({ ...editingPatient, full_name: e.target.value })
                  }
                  className="w-full px-3 py-2 bg-surface border border-line rounded text-sm text-ink focus:outline-none"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-text uppercase mb-1">
                    Mobile Number
                  </label>
                  <input
                    type="tel"
                    required
                    value={editingPatient.mobile_number}
                    onChange={(e) =>
                      setEditingPatient({ ...editingPatient, mobile_number: e.target.value })
                    }
                    className="w-full px-3 py-2 bg-surface border border-line rounded text-sm text-ink font-mono focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-text uppercase mb-1">
                    Language
                  </label>
                  <select
                    value={editingPatient.preferred_language}
                    onChange={(e) =>
                      setEditingPatient({ ...editingPatient, preferred_language: e.target.value })
                    }
                    className="w-full px-3 py-2 bg-surface border border-line rounded text-sm text-ink focus:outline-none"
                  >
                    <option value="en">English</option>
                    <option value="hi">Hindi (हिंदी)</option>
                    <option value="ta">Tamil (தமிழ்)</option>
                    <option value="te">Telugu (తెలుగు)</option>
                    <option value="kn">Kannada (ಕನ್ನಡ)</option>
                    <option value="ml">Malayalam (മലയാളം)</option>
                    <option value="mr">Marathi (मराठी)</option>
                    <option value="bn">Bengali (বাংলা)</option>
                    <option value="gu">Gujarati (ગુજરાતી)</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-text uppercase mb-1">
                  Allergies
                </label>
                <input
                  type="text"
                  value={editingPatient.allergies_summary || ''}
                  onChange={(e) =>
                    setEditingPatient({ ...editingPatient, allergies_summary: e.target.value })
                  }
                  placeholder="e.g. Penicillin"
                  className="w-full px-3 py-2 bg-surface border border-line rounded text-sm text-ink focus:outline-none"
                />
              </div>

              <div className="pt-2 flex justify-end gap-2">
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => setIsEditModalOpen(false)}
                >
                  Cancel
                </Button>
                <Button type="submit" variant="primary" isLoading={isSubmitting}>
                  Save Changes
                </Button>
              </div>
            </form>
          </Modal>
        )}
      </div>
    </AppLayout>
  );
};

