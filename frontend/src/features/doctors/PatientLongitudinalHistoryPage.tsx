import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { AppLayout } from '@/components/layout/AppLayout';
import { Card } from '@/components/common/Card';
import { StatusBadge } from '@/components/common/StatusBadge';
import { Button } from '@/components/common/Button';
import api, { getErrorMessage } from '@/services/api';
import {
  ArrowLeft,
  Calendar,
  AlertTriangle,
  Pill,
  FileText,
  Clock,
  Download,
  ShieldCheck,
  User,
} from 'lucide-react';

export const PatientLongitudinalHistoryPage: React.FC = () => {
  const { patientId } = useParams<{ patientId: string }>();
  const navigate = useNavigate();

  const [historyData, setHistoryData] = useState<any | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchHistory = async () => {
    setIsLoading(true);
    try {
      const response = await api.get(`/patients/${patientId}/longitudinal-history`);
      setHistoryData(response.data);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchHistory();
  }, [patientId]);

  if (isLoading) {
    return (
      <AppLayout>
        <div className="p-8 text-center text-sm text-text-2">Loading longitudinal history...</div>
      </AppLayout>
    );
  }

  if (error || !historyData) {
    return (
      <AppLayout>
        <div className="space-y-4">
          <Button variant="outline" size="sm" onClick={() => navigate('/doctor/dashboard')}>
            <ArrowLeft className="w-4 h-4 mr-1" />
            Back to Dashboard
          </Button>
          <div className="p-4 rounded-lg bg-status-rec-bg text-status-err text-sm font-medium">
            {error || 'Patient history not found'}
          </div>
        </div>
      </AppLayout>
    );
  }

  const patient = historyData.patient;

  return (
    <AppLayout>
      <div className="space-y-6">
        {/* Navigation back */}
        <Button
          variant="outline"
          size="sm"
          onClick={() => navigate('/doctor/dashboard')}
          leftIcon={<ArrowLeft className="w-4 h-4" />}
        >
          Back to Doctor Dashboard
        </Button>

        {/* Patient Header Block */}
        <div className="bg-surface rounded-xl border border-line p-6 shadow-card flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div>
            <div className="flex items-center gap-3">
              <h1 className="font-serif text-3xl font-bold text-ink">{patient.full_name}</h1>
              <span className="font-mono text-xs px-2.5 py-1 rounded bg-surface-2 text-ink border border-line">
                {patient.patient_identifier}
              </span>
            </div>
            <div className="text-xs text-text-2 mt-1.5 flex items-center gap-2">
              <span>{patient.gender}</span>
              <span>•</span>
              <span>{patient.age_years ? `${patient.age_years} years` : 'Age N/A'}</span>
              <span>•</span>
              <span>Mobile: {patient.mobile_number}</span>
              <span>•</span>
              <span className="uppercase font-semibold text-ink">
                Preferred Lang: {patient.preferred_language}
              </span>
            </div>
          </div>

          <div>
            {patient.allergies_summary ? (
              <div className="p-3 bg-status-rec-bg border border-status-err/30 rounded-lg text-xs">
                <div className="font-bold text-status-err flex items-center gap-1.5 uppercase tracking-wider">
                  <AlertTriangle className="w-3.5 h-3.5" />
                  Known Allergies
                </div>
                <div className="font-semibold text-ink mt-0.5">{patient.allergies_summary}</div>
                <div className="text-[10px] text-text-2 mt-0.5">
                  Verification: {patient.allergy_verification_status}
                </div>
              </div>
            ) : (
              <div className="p-3 bg-status-approved-bg border border-status-approved/30 rounded-lg text-xs">
                <div className="font-bold text-status-approved flex items-center gap-1.5 uppercase tracking-wider">
                  <ShieldCheck className="w-3.5 h-3.5" />
                  No Documented Allergies
                </div>
                <div className="text-[10px] text-text-2 mt-0.5">
                  Verification: {patient.allergy_verification_status}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Longitudinal Grid: Historical Medications + Chronological Visits */}
        <div className="grid lg:grid-cols-12 gap-6">
          {/* Historical Medications (Part 5.4 - Explicitly Labeled) */}
          <div className="lg:col-span-5 space-y-4">
            <Card
              title="Historical Prescriptions & Medications"
              subtitle="Past therapies recorded in previous clinical encounters"
            >
              <div className="p-2.5 bg-status-warn-bg/50 border border-status-warn/25 rounded-md text-xs text-status-warn mb-3 font-medium">
                ⚠️ HISTORICAL — Verify current adherence before re-prescribing.
              </div>

              {historyData.historical_medications?.length === 0 ? (
                <div className="text-xs text-text-2 py-4 text-center">
                  No historical medications recorded.
                </div>
              ) : (
                <div className="divide-y divide-line/40 space-y-2">
                  {historyData.historical_medications?.map((m: any, idx: number) => (
                    <div key={idx} className="pt-2 text-xs">
                      <div className="font-semibold text-ink flex items-center justify-between">
                        <span>{m.medication_name} {m.strength && `(${m.strength})`}</span>
                        <span className="text-[10px] px-2 py-0.5 rounded bg-surface-2 text-text-2">
                          {m.doctor_verified ? 'Verified' : 'Unverified'}
                        </span>
                      </div>
                      <div className="text-text-2 mt-0.5 font-mono">
                        {m.dosage} • {m.frequency} • {m.duration}
                      </div>
                      {m.special_instructions && (
                        <div className="text-[11px] text-text-2 italic mt-0.5">
                          "{m.special_instructions}"
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </Card>
          </div>

          {/* Chronological Visit Timeline */}
          <div className="lg:col-span-7 space-y-4">
            <Card
              title="Encounter History & Approved Notes"
              subtitle="Chronological list of all outpatient visits and signed clinical records"
            >
              {historyData.consultations?.length === 0 ? (
                <div className="text-xs text-text-2 py-4 text-center">
                  No previous consultations recorded for this patient.
                </div>
              ) : (
                <div className="space-y-4">
                  {historyData.consultations?.map((cons: any) => (
                    <div
                      key={cons.id}
                      className="p-4 bg-surface-2/40 border border-line rounded-lg space-y-2"
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <Calendar className="w-4 h-4 text-accent" />
                          <span className="font-semibold text-ink text-sm">
                            Visit on{' '}
                            {new Date(cons.started_at).toLocaleDateString('en-IN', {
                              day: '2-digit',
                              month: 'short',
                              year: 'numeric',
                            })}
                          </span>
                        </div>
                        <StatusBadge status={cons.status} />
                      </div>

                      {cons.chief_complaint_summary && (
                        <div className="text-xs text-text">
                          <strong className="text-ink">Chief Complaint:</strong>{' '}
                          {cons.chief_complaint_summary}
                        </div>
                      )}

                      {/* Approved Reports list */}
                      {cons.reports && cons.reports.length > 0 && (
                        <div className="pt-2 border-t border-line/30 flex items-center gap-3">
                          <span className="text-xs font-semibold text-text-2">Approved Notes:</span>
                          {cons.reports.map((rep: any) => (
                            <Button
                              key={rep.id}
                              variant="outline"
                              size="sm"
                              className="text-xs h-7"
                              leftIcon={<FileText className="w-3 h-3 text-accent" />}
                              onClick={() =>
                                window.open(
                                  `/api/v1/consultations/${cons.id}/reports/${rep.report_type}/pdf`,
                                  '_blank'
                                )
                              }
                            >
                              {rep.report_type === 'DOCTOR_CLINICAL'
                                ? 'Doctor Note PDF'
                                : 'Patient Handout PDF'}
                            </Button>
                          ))}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </Card>
          </div>
        </div>
      </div>
    </AppLayout>
  );
};

