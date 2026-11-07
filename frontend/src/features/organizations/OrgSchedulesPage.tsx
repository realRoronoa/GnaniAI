import React, { useEffect, useState } from 'react';
import { AppLayout } from '@/components/layout/AppLayout';
import { DataTable, Column } from '@/components/common/DataTable';
import { StatusBadge } from '@/components/common/StatusBadge';
import { Button } from '@/components/common/Button';
import { Modal } from '@/components/common/Modal';
import api, { getErrorMessage } from '@/services/api';
import { DoctorSchedule, DoctorStaff, Branch } from '@/types';
import { Plus, Calendar, Clock, MapPin } from 'lucide-react';

const DAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];

export const OrgSchedulesPage: React.FC = () => {
  const [schedules, setSchedules] = useState<DoctorSchedule[]>([]);
  const [doctors, setDoctors] = useState<DoctorStaff[]>([]);
  const [branches, setBranches] = useState<Branch[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Form State
  const [selectedDoctorId, setSelectedDoctorId] = useState('');
  const [selectedBranchId, setSelectedBranchId] = useState('');
  const [dayOfWeek, setDayOfWeek] = useState(0); // 0=Mon
  const [startTime, setStartTime] = useState('09:00');
  const [endTime, setEndTime] = useState('13:00');
  const [slotMinutes, setSlotMinutes] = useState(15);

  const fetchScheduleData = async () => {
    setIsLoading(true);
    try {
      const [schedRes, staffRes, branchesRes] = await Promise.all([
        api.get('/org/schedules').catch(() => ({ data: [] })),
        api.get('/org/staff').catch(() => ({ data: { doctors: [] } })),
        api.get('/org/branches').catch(() => ({ data: [] })),
      ]);
      setSchedules(Array.isArray(schedRes.data) ? schedRes.data : []);
      const docList = Array.isArray(staffRes.data?.doctors) ? staffRes.data.doctors : [];
      const branchList = Array.isArray(branchesRes.data) ? branchesRes.data : [];
      setDoctors(docList);
      setBranches(branchList);

      if (docList.length > 0 && !selectedDoctorId) {
        setSelectedDoctorId(docList[0].user_id || docList[0].id);
      }
      if (branchList.length > 0 && !selectedBranchId) {
        setSelectedBranchId(branchList[0].id);
      }
    } catch (err) {
      console.error('Failed to load schedules:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchScheduleData();
  }, []);

  const handleCreateSchedule = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setError(null);

    try {
      await api.post('/org/schedules', {
        doctor_user_id: selectedDoctorId,
        location_id: selectedBranchId,
        day_of_week: Number(dayOfWeek),
        start_time: startTime,
        end_time: endTime,
        slot_duration_minutes: Number(slotMinutes),
      });

      setIsModalOpen(false);
      fetchScheduleData();
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setIsSubmitting(false);
    }
  };

  const columns: Column<DoctorSchedule>[] = [
    {
      header: 'Day of Week',
      render: (s) => (
        <span className="font-semibold text-ink">
          {DAYS[s.day_of_week] || `Day ${s.day_of_week}`}
        </span>
      ),
    },
    {
      header: 'Shift Hours',
      render: (s) => (
        <span className="text-xs font-mono text-text-2">
          {s.start_time} — {s.end_time}
        </span>
      ),
    },
    {
      header: 'Slot Duration',
      render: (s) => (
        <span className="text-xs font-mono text-ink">
          {s.slot_duration_minutes} mins
        </span>
      ),
    },
    {
      header: 'Status',
      render: (s) => <StatusBadge status={s.is_active ? 'ACTIVE' : 'SUSPENDED'} />,
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
            <h1 className="font-serif text-3xl font-bold text-ink">Doctor Shift Schedules</h1>
            <p className="text-sm text-text-2 mt-1">
              Configure OPD weekly consultation slots and branch duty rosters.
            </p>
          </div>
          <Button
            variant="primary"
            leftIcon={<Plus className="w-4 h-4" />}
            onClick={() => setIsModalOpen(true)}
          >
            Add Weekly Shift
          </Button>
        </div>

        {/* Schedules Table */}
        <DataTable
          columns={columns}
          data={schedules}
          isLoading={isLoading}
          emptyMessage="No weekly shifts defined yet."
        />

        {/* Add Schedule Modal */}
        <Modal
          isOpen={isModalOpen}
          onClose={() => setIsModalOpen(false)}
          title="Add Doctor Shift Schedule"
          subtitle="Assign recurring weekly OPD availability for appointments."
        >
          <form onSubmit={handleCreateSchedule} className="space-y-3.5">
            {error && (
              <div className="p-2.5 rounded bg-status-rec-bg border border-status-err/30 text-xs text-status-err">
                {error}
              </div>
            )}

            <div>
              <label className="block text-xs font-semibold text-text uppercase mb-1">
                Doctor *
              </label>
              <select
                required
                value={selectedDoctorId}
                onChange={(e) => setSelectedDoctorId(e.target.value)}
                className="w-full px-3 py-2 bg-surface border border-line rounded text-xs text-ink focus:outline-none focus:ring-1 focus:ring-ink"
              >
                {doctors.map((d) => (
                  <option key={d.id} value={d.user_id || d.id}>
                    {d.full_name} ({d.specialization || 'Doctor'})
                  </option>
                ))}
              </select>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-semibold text-text uppercase mb-1">
                  Branch
                </label>
                <select
                  value={selectedBranchId}
                  onChange={(e) => setSelectedBranchId(e.target.value)}
                  className="w-full px-3 py-2 bg-surface border border-line rounded text-xs text-ink focus:outline-none focus:ring-1 focus:ring-ink"
                >
                  <option value="">Default Branch</option>
                  {branches.map((b) => (
                    <option key={b.id} value={b.id}>
                      {b.name}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-text uppercase mb-1">
                  Day of Week
                </label>
                <select
                  value={dayOfWeek}
                  onChange={(e) => setDayOfWeek(Number(e.target.value))}
                  className="w-full px-3 py-2 bg-surface border border-line rounded text-xs text-ink focus:outline-none focus:ring-1 focus:ring-ink"
                >
                  {DAYS.map((day, idx) => (
                    <option key={idx} value={idx}>
                      {day}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div className="grid grid-cols-3 gap-2">
              <div>
                <label className="block text-xs font-semibold text-text uppercase mb-1">
                  Start Time
                </label>
                <input
                  type="time"
                  required
                  value={startTime}
                  onChange={(e) => setStartTime(e.target.value)}
                  className="w-full px-2 py-2 bg-surface border border-line rounded text-xs text-ink focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-text uppercase mb-1">
                  End Time
                </label>
                <input
                  type="time"
                  required
                  value={endTime}
                  onChange={(e) => setEndTime(e.target.value)}
                  className="w-full px-2 py-2 bg-surface border border-line rounded text-xs text-ink focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-text uppercase mb-1">
                  Slot (Mins)
                </label>
                <input
                  type="number"
                  min={5}
                  max={60}
                  step={5}
                  value={slotMinutes}
                  onChange={(e) => setSlotMinutes(Number(e.target.value))}
                  className="w-full px-2 py-2 bg-surface border border-line rounded text-xs text-ink focus:outline-none"
                />
              </div>
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
                Save Shift
              </Button>
            </div>
          </form>
        </Modal>
      </div>
    </AppLayout>
  );
};

