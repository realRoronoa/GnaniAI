import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { AppLayout } from '@/components/layout/AppLayout';
import { StatCard } from '@/components/common/StatCard';
import { DataTable, Column } from '@/components/common/DataTable';
import { StatusBadge } from '@/components/common/StatusBadge';
import { Button } from '@/components/common/Button';
import api, { getErrorMessage } from '@/services/api';
import { Appointment, AppointmentStatus, ReceptionOverview, DoctorStaff } from '@/types';
import {
  Users,
  Clock,
  CheckCircle2,
  AlertCircle,
  XCircle,
  UserCheck,
  RefreshCw,
  Plus,
  ArrowRight,
  Filter,
} from 'lucide-react';

export const ReceptionOverviewPage: React.FC = () => {
  const navigate = useNavigate();
  const [overview, setOverview] = useState<ReceptionOverview | null>(null);
  const [appointments, setAppointments] = useState<Appointment[]>([]);
  const [doctors, setDoctors] = useState<DoctorStaff[]>([]);
  const [selectedDoctorId, setSelectedDoctorId] = useState<string>('all');
  const [selectedStatus, setSelectedStatus] = useState<string>('all');
  const [isLoading, setIsLoading] = useState(true);
  const [autoPoll, setAutoPoll] = useState(true);

  const fetchQueueData = async () => {
    setIsLoading(true);
    try {
      const [overviewRes, queueRes, staffRes] = await Promise.all([
        api.get('/reception/overview').catch(() => ({ data: null })),
        api.get('/appointments/queue').catch(() => ({ data: { queue: [] } })),
        api.get('/org/staff').catch(() => ({ data: { doctors: [] } })),
      ]);

      setOverview(overviewRes.data);
      const queueList = Array.isArray(queueRes.data?.queue)
        ? queueRes.data.queue
        : Array.isArray(queueRes.data?.doctor_queues)
        ? queueRes.data.doctor_queues.flatMap((dq: any) => dq.appointments || [])
        : Array.isArray(queueRes.data)
        ? queueRes.data
        : [];
      setAppointments(queueList);
      setDoctors(Array.isArray(staffRes.data?.doctors) ? staffRes.data.doctors : []);
    } catch (err) {
      console.error('Failed to load reception overview:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchQueueData();
    let interval: NodeJS.Timeout | null = null;
    if (autoPoll) {
      interval = setInterval(() => {
        fetchQueueData();
      }, 15000);
    }
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [autoPoll]);

  const handleUpdateStatus = async (appointmentId: string, newStatus: AppointmentStatus) => {
    try {
      await api.patch(`/appointments/${appointmentId}/status`, {
        status: newStatus,
      });
      fetchQueueData();
    } catch (err) {
      alert(`Status update failed: ${getErrorMessage(err)}`);
    }
  };

  // Filter appointments
  const filteredQueue = appointments.filter((app) => {
    if (selectedDoctorId !== 'all' && app.doctor_user_id !== selectedDoctorId) return false;
    if (selectedStatus !== 'all' && app.status !== selectedStatus) return false;
    return true;
  });

  const columns: Column<Appointment>[] = [
    {
      header: 'Queue #',
      render: (app) => (
        <span className="font-mono font-bold text-ink text-sm">
          #{app.queue_position}
        </span>
      ),
      className: 'w-20',
    },
    {
      header: 'Patient Details',
      render: (app) => (
        <div>
          <div className="font-semibold text-ink">
            {app.patient?.full_name || 'Patient'}
          </div>
          <div className="text-xs text-text-2 font-mono flex items-center gap-2">
            <span>{app.patient?.patient_identifier || 'UHID Pending'}</span>
            <span>•</span>
            <span>{app.patient?.mobile_number}</span>
            {app.patient?.has_previous_visits && (
              <span className="text-[10px] bg-status-ai-bg text-status-ai px-1.5 py-0.2 rounded font-sans font-semibold">
                Returning
              </span>
            )}
          </div>
        </div>
      ),
    },
    {
      header: 'Assigned Doctor',
      render: (app) => (
        <span className="text-sm font-medium text-ink">
          {app.doctor_name || 'Unassigned'}
        </span>
      ),
    },
    {
      header: 'Type & Scheduled',
      render: (app) => (
        <div>
          <span
            className={`inline-block text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded ${
              app.appointment_type === 'WALK_IN'
                ? 'bg-status-warn-bg text-status-warn'
                : 'bg-surface-2 text-text-2'
            }`}
          >
            {app.appointment_type}
          </span>
          <div className="text-xs font-mono text-text-2 mt-0.5">
            {app.scheduled_time || 'Walk-in'}
          </div>
        </div>
      ),
    },
    {
      header: 'Status',
      render: (app) => <StatusBadge status={app.status} />,
    },
    {
      header: 'Actions',
      render: (app) => (
        <div className="flex items-center gap-1.5 flex-wrap">
          {app.status === 'SCHEDULED' && (
            <Button
              variant="outline"
              size="sm"
              onClick={() => handleUpdateStatus(app.id, 'CONFIRMED')}
            >
              Confirm
            </Button>
          )}
          {app.status === 'CONFIRMED' && (
            <Button
              variant="primary"
              size="sm"
              onClick={() => handleUpdateStatus(app.id, 'ARRIVED')}
            >
              Mark Arrived
            </Button>
          )}
          {app.status === 'ARRIVED' && (
            <Button
              variant="primary"
              size="sm"
              onClick={() => handleUpdateStatus(app.id, 'WAITING')}
            >
              To Waiting Queue
            </Button>
          )}
          {['SCHEDULED', 'CONFIRMED', 'ARRIVED', 'WAITING'].includes(app.status) && (
            <Button
              variant="ghost"
              size="sm"
              className="text-status-err hover:bg-status-rec-bg/30 text-xs"
              onClick={() => {
                if (window.confirm('Cancel this appointment?')) {
                  handleUpdateStatus(app.id, 'CANCELLED');
                }
              }}
            >
              Cancel
            </Button>
          )}
          {app.status === 'WAITING' && (
            <span className="text-xs font-medium text-status-warn flex items-center gap-1">
              <Clock className="w-3.5 h-3.5 animate-spin" />
              Waiting for Doctor
            </span>
          )}
          {app.status === 'IN_PROGRESS' && (
            <span className="text-xs font-semibold text-status-rec flex items-center gap-1">
              <span className="w-2 h-2 rounded-full bg-status-rec animate-pulse" />
              In Consultation
            </span>
          )}
          {app.status === 'COMPLETED' && (
            <span className="text-xs font-medium text-status-approved flex items-center gap-1">
              <CheckCircle2 className="w-3.5 h-3.5" />
              Encounter Finished
            </span>
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
              RECEPTION CONSOLE
            </div>
            <h1 className="font-serif text-3xl font-bold text-ink">Live OPD Queue</h1>
            <p className="text-sm text-text-2 mt-1">
              Today's patient flow, waiting room queueing, and desk arrival check-ins.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <label className="flex items-center gap-2 text-xs font-medium text-text-2 cursor-pointer">
              <input
                type="checkbox"
                checked={autoPoll}
                onChange={(e) => setAutoPoll(e.target.checked)}
                className="rounded border-line text-ink focus:ring-ink"
              />
              <span>Live 15s Auto-sync</span>
            </label>
            <Button
              variant="outline"
              size="sm"
              leftIcon={<RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />}
              onClick={fetchQueueData}
            >
              Refresh
            </Button>
            <Button
              variant="primary"
              size="sm"
              leftIcon={<Plus className="w-4 h-4" />}
              onClick={() => navigate('/reception/appointments')}
            >
              Book Appointment
            </Button>
          </div>
        </div>

        {/* Status Counters KPI Grid */}
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
          <StatCard
            label="Total Today"
            value={overview?.total_appointments ?? appointments.length}
            icon={<Users className="w-4 h-4 text-ink" />}
          />
          <StatCard
            label="In Waiting Room"
            value={overview?.waiting_count ?? appointments.filter((a) => a.status === 'WAITING').length}
            icon={<Clock className="w-4 h-4 text-status-warn" />}
          />
          <StatCard
            label="Arrived at Desk"
            value={overview?.arrived_count ?? appointments.filter((a) => a.status === 'ARRIVED').length}
            icon={<UserCheck className="w-4 h-4 text-status-ai" />}
          />
          <StatCard
            label="In Consultation"
            value={overview?.in_progress_count ?? appointments.filter((a) => a.status === 'IN_PROGRESS').length}
            icon={<span className="w-2.5 h-2.5 rounded-full bg-status-rec animate-pulse" />}
          />
          <StatCard
            label="Completed"
            value={overview?.completed_count ?? appointments.filter((a) => a.status === 'COMPLETED').length}
            icon={<CheckCircle2 className="w-4 h-4 text-status-approved" />}
          />
          <StatCard
            label="Cancelled / No-Show"
            value={
              (overview?.cancelled_count ?? 0) + (overview?.no_show_count ?? 0) ||
              appointments.filter((a) => ['CANCELLED', 'NO_SHOW'].includes(a.status)).length
            }
            icon={<XCircle className="w-4 h-4 text-status-err" />}
          />
        </div>

        {/* Doctor & Status Filters */}
        <div className="bg-surface border border-line rounded-lg p-3 flex flex-wrap items-center justify-between gap-3 shadow-card">
          <div className="flex items-center gap-2 flex-wrap">
            <Filter className="w-4 h-4 text-text-2" />
            <span className="text-xs font-semibold uppercase tracking-wider text-text-2">
              Filter By:
            </span>

            {/* Doctor Filter */}
            <select
              value={selectedDoctorId}
              onChange={(e) => setSelectedDoctorId(e.target.value)}
              className="px-2.5 py-1.5 bg-surface-2 border border-line rounded text-xs text-ink font-medium focus:outline-none"
            >
              <option value="all">All Doctors</option>
              {doctors.map((d) => (
                <option key={d.id} value={d.user_id || d.id}>
                  {d.full_name} ({d.specialization || 'General'})
                </option>
              ))}
            </select>

            {/* Status Filter */}
            <select
              value={selectedStatus}
              onChange={(e) => setSelectedStatus(e.target.value)}
              className="px-2.5 py-1.5 bg-surface-2 border border-line rounded text-xs text-ink font-medium focus:outline-none"
            >
              <option value="all">All Statuses</option>
              <option value="WAITING">Waiting Room</option>
              <option value="ARRIVED">Arrived</option>
              <option value="IN_PROGRESS">In Progress</option>
              <option value="CONFIRMED">Confirmed</option>
              <option value="SCHEDULED">Scheduled</option>
              <option value="COMPLETED">Completed</option>
              <option value="CANCELLED">Cancelled</option>
            </select>
          </div>

          <div className="text-xs text-text-2 font-mono">
            Showing {filteredQueue.length} of {appointments.length} patients
          </div>
        </div>

        {/* Queue Table */}
        <DataTable
          columns={columns}
          data={filteredQueue}
          isLoading={isLoading}
          emptyMessage="No patients currently in queue for this selection."
        />
      </div>
    </AppLayout>
  );
};

