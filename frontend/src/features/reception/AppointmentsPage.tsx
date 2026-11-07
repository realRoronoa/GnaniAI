import React, { useEffect, useState } from 'react';
import { AppLayout } from '@/components/layout/AppLayout';
import { DataTable, Column } from '@/components/common/DataTable';
import { StatusBadge } from '@/components/common/StatusBadge';
import { Button } from '@/components/common/Button';
import { Modal } from '@/components/common/Modal';
import api, { getErrorMessage } from '@/services/api';
import { Appointment, DoctorStaff, Branch, Patient, AppointmentType } from '@/types';
import { Plus, Calendar, Clock, UserCheck, Stethoscope, AlertCircle } from 'lucide-react';

export const AppointmentsPage: React.FC = () => {
  const [appointments, setAppointments] = useState<Appointment[]>([]);
  const [doctors, setDoctors] = useState<DoctorStaff[]>([]);
  const [branches, setBranches] = useState<Branch[]>([]);
  const [patients, setPatients] = useState<Patient[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  // Book Modal
  const [isBookModalOpen, setIsBookModalOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Form Fields
  const [selectedPatientId, setSelectedPatientId] = useState('');
  const [selectedDoctorId, setSelectedDoctorId] = useState('');
  const [selectedBranchId, setSelectedBranchId] = useState('');
  const [appType, setAppType] = useState<AppointmentType>('WALK_IN');
  const [appDate, setAppDate] = useState(() => new Date().toISOString().split('T')[0]);
  const [scheduledTime, setScheduledTime] = useState('10:00');
  const [reason, setReason] = useState('');
  const [adminNotes, setAdminNotes] = useState('');

  // Reassign Modal
  const [reassignApp, setReassignApp] = useState<Appointment | null>(null);
  const [newDoctorId, setNewDoctorId] = useState('');

  const fetchData = async () => {
    setIsLoading(true);
    try {
      const [queueRes, staffRes, branchesRes, patientsRes] = await Promise.all([
        api.get('/appointments/queue').catch(() => ({ data: { queue: [] } })),
        api.get('/org/staff').catch(() => ({ data: { doctors: [] } })),
        api.get('/org/branches').catch(() => ({ data: [] })),
        api.get('/patients').catch(() => ({ data: [] })),
      ]);

      const queueList = queueRes.data?.queue || queueRes.data || [];
      setAppointments(Array.isArray(queueList) ? queueList : []);
      const docList = Array.isArray(staffRes.data?.doctors) ? staffRes.data.doctors : [];
      const branchList = Array.isArray(branchesRes.data) ? branchesRes.data : [];
      const patList = Array.isArray(patientsRes.data) ? patientsRes.data : [];

      setDoctors(docList);
      setBranches(branchList);
      setPatients(patList);

      if (patList.length > 0 && !selectedPatientId) setSelectedPatientId(patList[0].id);
      if (docList.length > 0 && !selectedDoctorId) setSelectedDoctorId(docList[0].user_id || docList[0].id);
      if (branchList.length > 0 && !selectedBranchId) setSelectedBranchId(branchList[0].id);
    } catch (err) {
      console.error('Failed to load appointments data:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  useEffect(() => {
    if (isBookModalOpen) {
      if (patients.length > 0 && !selectedPatientId) setSelectedPatientId(patients[0].id);
      if (doctors.length > 0 && !selectedDoctorId) setSelectedDoctorId(doctors[0].user_id || doctors[0].id);
      if (branches.length > 0 && !selectedBranchId) setSelectedBranchId(branches[0].id);
    }
  }, [isBookModalOpen, patients, doctors, branches]);

  const handleBookAppointment = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedPatientId) {
      setError('Please select a registered patient.');
      return;
    }

    setIsSubmitting(true);
    setError(null);

    try {
      let scheduledIso: string = new Date().toISOString();
      if (appType === 'SCHEDULED' && scheduledTime) {
        try {
          scheduledIso = new Date(`${appDate}T${scheduledTime}:00`).toISOString();
        } catch {
          scheduledIso = new Date().toISOString();
        }
      }

      await api.post('/appointments', {
        patient_id: selectedPatientId,
        doctor_user_id: selectedDoctorId || null,
        location_id: selectedBranchId || null,
        appointment_date: appDate,
        scheduled_time: scheduledIso,
        appointment_type: appType,
        reason_for_visit: reason || null,
        administrative_notes: adminNotes || null,
      });

      setIsBookModalOpen(false);
      setReason('');
      setAdminNotes('');
      fetchData();
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleReassignDoctor = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!reassignApp || !newDoctorId) return;
    setIsSubmitting(true);

    try {
      await api.patch(`/appointments/${reassignApp.id}/assign-doctor`, {
        doctor_user_id: newDoctorId,
      });

      setReassignApp(null);
      fetchData();
    } catch (err) {
      alert(`Doctor reassignment failed: ${getErrorMessage(err)}`);
    } finally {
      setIsSubmitting(false);
    }
  };

  const columns: Column<Appointment>[] = [
    {
      header: 'Queue #',
      render: (a) => (
        <span className="font-mono font-bold text-ink">#{a.queue_position}</span>
      ),
    },
    {
      header: 'Patient',
      render: (a) => (
        <div>
          <div className="font-semibold text-ink">{a.patient?.full_name || 'Patient'}</div>
          <div className="text-xs font-mono text-text-2">
            {a.patient?.patient_identifier || '—'}
          </div>
        </div>
      ),
    },
    {
      header: 'Assigned Doctor',
      render: (a) => (
        <div className="flex items-center gap-2">
          <span className="font-medium text-ink text-sm">{a.doctor_name || 'Unassigned'}</span>
          <Button
            variant="ghost"
            size="sm"
            className="text-[11px] h-6 px-1.5"
            onClick={() => {
              setReassignApp(a);
              setNewDoctorId(a.doctor_user_id || (doctors[0]?.user_id || ''));
            }}
          >
            Reassign
          </Button>
        </div>
      ),
    },
    {
      header: 'Type & Reason',
      render: (a) => (
        <div>
          <span className="text-xs font-semibold text-text uppercase">{a.appointment_type}</span>
          <div className="text-xs text-text-2 truncate max-w-xs">
            {a.reason_for_visit || 'General OPD Consultation'}
          </div>
        </div>
      ),
    },
    {
      header: 'Status',
      render: (a) => <StatusBadge status={a.status} />,
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
            <h1 className="font-serif text-3xl font-bold text-ink">Outpatient Bookings</h1>
            <p className="text-sm text-text-2 mt-1">
              Create outpatient bookings, assign consulting doctors, and manage desk arrivals.
            </p>
          </div>
          <Button
            variant="primary"
            leftIcon={<Plus className="w-4 h-4" />}
            onClick={() => setIsBookModalOpen(true)}
          >
            New Consultation Booking
          </Button>
        </div>

        {/* Appointments Table */}
        <DataTable
          columns={columns}
          data={appointments}
          isLoading={isLoading}
          emptyMessage="No appointments scheduled for today."
        />

        {/* Book Appointment Modal */}
        <Modal
          isOpen={isBookModalOpen}
          onClose={() => setIsBookModalOpen(false)}
          title="Book Consultation Appointment"
          subtitle="Assigns a queue number and schedules patient intake."
          maxWidth="lg"
        >
          <form onSubmit={handleBookAppointment} className="space-y-3.5">
            {error && (
              <div className="p-2.5 rounded bg-status-rec-bg border border-status-err/30 text-xs text-status-err font-medium">
                {error}
              </div>
            )}

            <div>
              <label className="block text-xs font-semibold text-text uppercase mb-1">
                Select Registered Patient *
              </label>
              <select
                required
                value={selectedPatientId}
                onChange={(e) => setSelectedPatientId(e.target.value)}
                className="w-full px-3 py-2 bg-surface-2/60 border border-line rounded text-sm text-ink focus:outline-none"
              >
                {patients.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.full_name} ({p.patient_identifier}) — {p.mobile_number}
                  </option>
                ))}
              </select>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-semibold text-text uppercase mb-1">
                  Assigned Doctor *
                </label>
                <select
                  required
                  value={selectedDoctorId}
                  onChange={(e) => setSelectedDoctorId(e.target.value)}
                  className="w-full px-3 py-2 bg-surface-2/60 border border-line rounded text-sm text-ink focus:outline-none"
                >
                  {doctors.length === 0 ? (
                    <option value="" disabled>No doctors found in clinic</option>
                  ) : (
                    doctors.map((d) => (
                      <option key={d.id} value={d.user_id || d.id}>
                        {d.full_name} ({d.specialization || 'Doctor'})
                      </option>
                    ))
                  )}
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-text uppercase mb-1">
                  Clinic Branch
                </label>
                <select
                  value={selectedBranchId}
                  onChange={(e) => setSelectedBranchId(e.target.value)}
                  className="w-full px-3 py-2 bg-surface-2/60 border border-line rounded text-sm text-ink focus:outline-none"
                >
                  <option value="">Default Branch</option>
                  {branches.map((b) => (
                    <option key={b.id} value={b.id}>
                      {b.name} ({b.branch_code})
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div className="grid grid-cols-3 gap-3">
              <div>
                <label className="block text-xs font-semibold text-text uppercase mb-1">
                  Type *
                </label>
                <select
                  value={appType}
                  onChange={(e) => setAppType(e.target.value as AppointmentType)}
                  className="w-full px-3 py-2 bg-surface-2/60 border border-line rounded text-sm text-ink focus:outline-none"
                >
                  <option value="WALK_IN">Walk-In</option>
                  <option value="SCHEDULED">Scheduled</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-text uppercase mb-1">
                  Date
                </label>
                <input
                  type="date"
                  value={appDate}
                  onChange={(e) => setAppDate(e.target.value)}
                  className="w-full px-3 py-2 bg-surface-2/60 border border-line rounded text-sm text-ink focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-text uppercase mb-1">
                  Time Slot
                </label>
                <input
                  type="time"
                  disabled={appType === 'WALK_IN'}
                  value={scheduledTime}
                  onChange={(e) => setScheduledTime(e.target.value)}
                  className="w-full px-3 py-2 bg-surface-2/60 border border-line rounded text-sm text-ink focus:outline-none disabled:opacity-40"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-text uppercase mb-1">
                Reason for Visit / Chief Complaint
              </label>
              <input
                type="text"
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                placeholder="e.g. Acute fever, persistent cough for 4 days"
                className="w-full px-3 py-2 bg-surface-2/60 border border-line rounded text-sm text-ink focus:outline-none"
              />
            </div>

            <div className="pt-2 flex justify-end gap-2">
              <Button type="button" variant="outline" onClick={() => setIsBookModalOpen(false)}>
                Cancel
              </Button>
              <Button type="submit" variant="primary" isLoading={isSubmitting}>
                Book Consultation
              </Button>
            </div>
          </form>
        </Modal>

        {/* Reassign Doctor Modal */}
        {reassignApp && (
          <Modal
            isOpen={!!reassignApp}
            onClose={() => setReassignApp(null)}
            title="Reassign Consulting Doctor"
            subtitle={`Patient: ${reassignApp.patient?.full_name || 'Patient'}`}
          >
            <form onSubmit={handleReassignDoctor} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-text uppercase mb-1">
                  Select New Attending Doctor
                </label>
                <select
                  required
                  value={newDoctorId}
                  onChange={(e) => setNewDoctorId(e.target.value)}
                  className="w-full px-3 py-2 bg-surface-2/60 border border-line rounded text-sm text-ink focus:outline-none"
                >
                  {doctors.map((d) => (
                    <option key={d.id} value={d.user_id || d.id}>
                      {d.full_name} ({d.specialization || 'Doctor'})
                    </option>
                  ))}
                </select>
              </div>

              <div className="pt-2 flex justify-end gap-2">
                <Button type="button" variant="outline" onClick={() => setReassignApp(null)}>
                  Cancel
                </Button>
                <Button type="submit" variant="primary" isLoading={isSubmitting}>
                  Confirm Reassignment
                </Button>
              </div>
            </form>
          </Modal>
        )}
      </div>
    </AppLayout>
  );
};

