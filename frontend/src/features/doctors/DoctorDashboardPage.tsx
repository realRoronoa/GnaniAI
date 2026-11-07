import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { AppLayout } from '@/components/layout/AppLayout';
import { StatCard } from '@/components/common/StatCard';
import { Card } from '@/components/common/Card';
import { DataTable, Column } from '@/components/common/DataTable';
import { StatusBadge } from '@/components/common/StatusBadge';
import { Button } from '@/components/common/Button';
import api, { getErrorMessage } from '@/services/api';
import { DoctorDashboard, Appointment } from '@/types';
import {
  Stethoscope,
  Clock,
  CheckCircle2,
  AlertCircle,
  FileText,
  Play,
  ArrowRight,
  History,
  User,
  Calendar,
} from 'lucide-react';

export const DoctorDashboardPage: React.FC = () => {
  const navigate = useNavigate();
  const [dashboard, setDashboard] = useState<DoctorDashboard | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [startingAppointmentId, setStartingAppointmentId] = useState<string | null>(null);

  const fetchDashboard = async () => {
    setIsLoading(true);
    try {
      const response = await api.get('/doctor/dashboard');
      const data = response.data;
      if (data) {
        if (!data.waiting_queue && Array.isArray(data.waiting_patients)) {
          data.waiting_queue = data.waiting_patients.map((item: any) => item.appointment || item);
        }
        if (!data.upcoming_appointments && Array.isArray(data.upcoming_patients)) {
          data.upcoming_appointments = data.upcoming_patients.map((item: any) => item.appointment || item);
        }
        if (data.completed_today_count === undefined && Array.isArray(data.completed_patients)) {
          data.completed_today_count = data.completed_patients.length;
        }
      }
      setDashboard(data);
    } catch (err) {
      console.error('Failed to load doctor dashboard:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboard();
  }, []);

  const handleStartConsultation = async (appointmentId: string) => {
    setStartingAppointmentId(appointmentId);
    try {
      const response = await api.post('/consultations', {
        appointment_id: appointmentId,
      });
      const consultation = response.data;
      navigate(`/doctor/consultations/${consultation.id}`);
    } catch (err) {
      alert(`Could not start consultation: ${getErrorMessage(err)}`);
    } finally {
      setStartingAppointmentId(null);
    }
  };

  const queueColumns: Column<Appointment>[] = [
    {
      header: 'Queue #',
      render: (a) => (
        <span className="font-mono font-bold text-ink text-sm">
          #{a.queue_position}
        </span>
      ),
      className: 'w-20',
    },
    {
      header: 'Patient Details',
      render: (a) => (
        <div>
          <div className="font-semibold text-ink flex items-center gap-2">
            <span>{a.patient?.full_name || 'Patient'}</span>
            {a.patient?.has_previous_visits && (
              <span className="inline-flex items-center gap-1 text-[10px] font-semibold bg-surface-2 text-text px-1.5 py-0.5 rounded border border-line">
                <History className="w-3 h-3 text-accent" />
                Returning
              </span>
            )}
          </div>
          <div className="text-xs text-text-2 font-mono">
            {a.patient?.patient_identifier} • {a.patient?.gender}, {a.patient?.age_years || 'N/A'}y • {a.patient?.preferred_language?.toUpperCase()}
          </div>
        </div>
      ),
    },
    {
      header: 'Reason for Visit',
      render: (a) => (
        <span className="text-xs text-text-2">
          {a.reason_for_visit || 'General Consultation'}
        </span>
      ),
    },
    {
      header: 'Waiting Status',
      render: (a) => <StatusBadge status={a.status} />,
    },
    {
      header: 'Clinical Action',
      render: (a) => (
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => navigate(`/doctor/patients/${a.patient_id}`)}
          >
            History
          </Button>
          <Button
            variant="primary"
            size="sm"
            isLoading={startingAppointmentId === a.id}
            leftIcon={<Play className="w-3.5 h-3.5" />}
            onClick={() => handleStartConsultation(a.id)}
          >
            Start Visit
          </Button>
        </div>
      ),
    },
  ];

  return (
    <AppLayout>
      <div className="space-y-6">
        {/* Header */}
        <div>
          <div className="text-xs font-semibold uppercase tracking-[0.14em] text-accent mb-1">
            DOCTOR WORKSPACE
          </div>
          <h1 className="font-serif text-3xl font-bold text-ink">
            Consultations Overview
          </h1>
          <p className="text-sm text-text-2 mt-1">
            Welcome, Dr. {dashboard?.doctor_name || 'Physician'} • {dashboard?.today_date || new Date().toLocaleDateString('en-IN', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' })}
          </p>
        </div>

        {/* Active Consultation Spotlight Banner */}
        {dashboard?.active_consultation && (
          <div className="bg-surface rounded-xl border-2 border-accent p-6 shadow-card flex flex-col md:flex-row md:items-center md:justify-between gap-4">
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full bg-status-rec animate-pulse" />
                <span className="text-xs font-bold uppercase tracking-wider text-status-rec">
                  Active Consultation In Progress
                </span>
              </div>
              <h2 className="font-serif text-2xl font-bold text-ink">
                {dashboard.active_consultation.patient_name}
              </h2>
              <div className="text-xs font-mono text-text-2">
                UHID: {dashboard.active_consultation.patient_identifier} • Started at {new Date(dashboard.active_consultation.started_at).toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' })}
              </div>
            </div>

            <Button
              variant="accent"
              size="lg"
              rightIcon={<ArrowRight className="w-4 h-4" />}
              onClick={() => navigate(`/doctor/consultations/${dashboard.active_consultation?.id}`)}
            >
              Resume Consultation Studio
            </Button>
          </div>
        )}

        {/* 3 Metric Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <StatCard
            label="Patients in Waiting Queue"
            value={dashboard?.waiting_queue?.length ?? 0}
            subtext="Ready for examination"
            icon={<Clock className="w-5 h-5 text-status-warn" />}
          />
          <StatCard
            label="Pending Report Approvals"
            value={dashboard?.reports_pending_approval?.length ?? 0}
            subtext="Requires doctor sign-off"
            icon={<FileText className="w-5 h-5 text-accent" />}
          />
          <StatCard
            label="Completed Today"
            value={dashboard?.completed_today_count ?? 0}
            subtext="Consultations closed"
            icon={<CheckCircle2 className="w-5 h-5 text-status-approved" />}
          />
        </div>

        {/* Waiting Queue Table */}
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-base font-semibold text-ink">
              Today's Waiting Room Queue ({dashboard?.waiting_queue?.length || 0})
            </h2>
            <Button variant="outline" size="sm" onClick={fetchDashboard}>
              Refresh Queue
            </Button>
          </div>

          <DataTable
            columns={queueColumns}
            data={dashboard?.waiting_queue || []}
            isLoading={isLoading}
            emptyMessage="No patients currently waiting in your queue."
          />
        </div>

        {/* Reports Pending Approval Section */}
        {dashboard?.reports_pending_approval && dashboard.reports_pending_approval.length > 0 && (
          <div className="space-y-3 pt-2">
            <h2 className="text-base font-semibold text-ink">
              Clinical Reports Awaiting Your Sign-Off ({dashboard.reports_pending_approval.length})
            </h2>

            <div className="grid md:grid-cols-2 gap-3">
              {dashboard.reports_pending_approval.map((item) => (
                <div
                  key={item.consultation_id}
                  className="bg-surface border border-line rounded-lg p-4 shadow-card flex items-center justify-between"
                >
                  <div>
                    <div className="font-semibold text-ink text-sm">{item.patient_name}</div>
                    <div className="text-xs font-mono text-text-2">
                      {item.patient_identifier} • Encountered {new Date(item.encounter_time).toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' })}
                    </div>
                  </div>

                  <Button
                    variant="primary"
                    size="sm"
                    onClick={() => navigate(`/doctor/consultations/${item.consultation_id}`)}
                  >
                    Review & Sign
                  </Button>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </AppLayout>
  );
};

