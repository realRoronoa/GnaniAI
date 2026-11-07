import React, { useEffect, useState } from 'react';
import { AppLayout } from '@/components/layout/AppLayout';
import { DataTable, Column } from '@/components/common/DataTable';
import { StatusBadge } from '@/components/common/StatusBadge';
import { Button } from '@/components/common/Button';
import { Modal } from '@/components/common/Modal';
import api, { getErrorMessage } from '@/services/api';
import { Appointment, DeliveryOptions } from '@/types';
import { Download, Send, CheckCircle2, MessageSquare, Mail, ShieldAlert, FileText } from 'lucide-react';

export const ReportDeliveryPage: React.FC = () => {
  const [completedList, setCompletedList] = useState<Appointment[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  // Delivery Dialog State
  const [selectedApp, setSelectedApp] = useState<Appointment | null>(null);
  const [deliveryOpts, setDeliveryOpts] = useState<DeliveryOptions | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);

  const fetchCompletedEncounters = async () => {
    setIsLoading(true);
    try {
      const response = await api.get('/appointments/queue', {
        params: { status_filter: 'COMPLETED' },
      });
      const list = Array.isArray(response.data?.queue)
        ? response.data.queue
        : Array.isArray(response.data?.doctor_queues)
        ? response.data.doctor_queues.flatMap((dq: any) => dq.appointments || [])
        : Array.isArray(response.data)
        ? response.data
        : [];
      setCompletedList(list);
    } catch (err) {
      console.error('Failed to load completed encounters:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchCompletedEncounters();
  }, []);

  const handleOpenDelivery = async (app: Appointment) => {
    setSelectedApp(app);
    setIsModalOpen(true);
    setStatusMessage(null);
    setDeliveryOpts(null);

    try {
      // In backend, consultations can be mapped or queried
      // We query delivery-options using appointment id or consultation
      const res = await api.get(`/consultations/${app.id}/delivery-options`).catch(() => null);
      if (res && res.data) {
        setDeliveryOpts(res.data);
      } else {
        // Fallback calculation from patient data
        const phone = app.patient?.mobile_number || '';
        const cleanPhone = phone.replace(/\D/g, '');
        const intlPhone = cleanPhone.length === 10 ? `91${cleanPhone}` : cleanPhone;
        const msg = `Namaste ${app.patient?.full_name || 'Patient'}, your consultation summary from Arogya Care Clinic is ready.`;
        setDeliveryOpts({
          patient_name: app.patient?.full_name || 'Patient',
          mobile_number: phone,
          email: null,
          whatsapp_url: `https://wa.me/${intlPhone}?text=${encodeURIComponent(msg)}`,
          email_url: `mailto:?subject=Your Visit Summary&body=${encodeURIComponent(msg)}`,
          message_preview: msg,
        });
      }
    } catch (err) {
      console.error('Failed to fetch delivery options:', err);
    }
  };

  const handleDownloadPDF = async (app: Appointment) => {
    try {
      const response = await api.get(`/consultations/${app.id}/reports/PATIENT_SUMMARY/pdf`, {
        responseType: 'blob',
      });
      const blob = new Blob([response.data], { type: 'application/pdf' });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `Patient_Summary_${app.patient?.patient_identifier || 'Record'}.pdf`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err) {
      alert(`Download unavailable or report not yet approved: ${getErrorMessage(err)}`);
    }
  };

  const handleMarkShared = async (channel: 'MANUAL_WHATSAPP' | 'MANUAL_EMAIL') => {
    if (!selectedApp) return;
    setIsSubmitting(true);
    try {
      await api.post(`/consultations/${selectedApp.id}/mark-shared`, {
        delivery_channel: channel,
        recipient_contact:
          channel === 'MANUAL_WHATSAPP'
            ? selectedApp.patient?.mobile_number || 'WhatsApp'
            : 'Email',
      });
      setStatusMessage('Marked as shared in the patient audit record.');
      setTimeout(() => {
        setIsModalOpen(false);
        setStatusMessage(null);
      }, 1500);
    } catch (err) {
      alert(`Failed to log share event: ${getErrorMessage(err)}`);
    } finally {
      setIsSubmitting(false);
    }
  };

  const columns: Column<Appointment>[] = [
    {
      header: 'Patient Details',
      render: (a) => (
        <div>
          <div className="font-semibold text-ink">{a.patient?.full_name || 'Patient'}</div>
          <div className="text-xs font-mono text-text-2">
            {a.patient?.patient_identifier} • {a.patient?.mobile_number}
          </div>
        </div>
      ),
    },
    {
      header: 'Attending Doctor',
      render: (a) => (
        <span className="text-sm font-medium text-ink">{a.doctor_name || 'Attending Doctor'}</span>
      ),
    },
    {
      header: 'Encounter Status',
      render: () => <StatusBadge status="COMPLETED" />,
    },
    {
      header: 'Delivery Actions',
      render: (a) => (
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            leftIcon={<Download className="w-3.5 h-3.5" />}
            onClick={() => handleDownloadPDF(a)}
          >
            PDF
          </Button>
          <Button
            variant="primary"
            size="sm"
            leftIcon={<Send className="w-3.5 h-3.5" />}
            onClick={() => handleOpenDelivery(a)}
          >
            Share Desk
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
            RECEPTION CONSOLE
          </div>
          <h1 className="font-serif text-3xl font-bold text-ink">Manual Report Delivery</h1>
          <p className="text-sm text-text-2 mt-1">
            Download approved patient summaries or send verified summaries via WhatsApp and Email.
          </p>
        </div>

        {/* Clinical Boundary Notice */}
        <div className="p-3 bg-surface border border-line rounded-lg flex items-center gap-2 text-xs text-text-2 shadow-card">
          <ShieldAlert className="w-4 h-4 text-accent shrink-0" />
          <span>
            <strong>Receptionist Privacy Boundary:</strong> Front desk staff can only access doctor-approved
            Patient Summaries. Internal doctor encounter notes and unapproved AI drafts are restricted.
          </span>
        </div>

        {/* Completed Encounters Table */}
        <DataTable
          columns={columns}
          data={completedList}
          isLoading={isLoading}
          emptyMessage="No completed encounters awaiting report delivery today."
        />

        {/* Share Dialog */}
        {selectedApp && (
          <Modal
            isOpen={isModalOpen}
            onClose={() => setIsModalOpen(false)}
            title="Deliver Patient Summary Handout"
            subtitle={`Patient: ${selectedApp.patient?.full_name} (${selectedApp.patient?.patient_identifier})`}
          >
            <div className="space-y-4">
              {statusMessage ? (
                <div className="py-6 text-center space-y-2">
                  <CheckCircle2 className="w-8 h-8 text-status-approved mx-auto" />
                  <div className="font-semibold text-ink text-sm">{statusMessage}</div>
                </div>
              ) : (
                <>
                  <div className="p-3 bg-surface-2/60 rounded-lg text-xs space-y-1 font-mono">
                    <div className="text-text-2">Recipient Phone:</div>
                    <div className="font-semibold text-ink">{selectedApp.patient?.mobile_number}</div>
                  </div>

                  <div className="space-y-2">
                    <div className="text-xs font-semibold uppercase tracking-wider text-text-2">
                      Dispatch Channel Options:
                    </div>

                    {/* WhatsApp */}
                    <div className="p-3 bg-surface border border-line rounded-lg flex items-center justify-between">
                      <div className="flex items-center gap-2.5">
                        <MessageSquare className="w-4 h-4 text-status-approved" />
                        <div>
                          <div className="text-xs font-semibold text-ink">WhatsApp Direct Web Link</div>
                          <div className="text-[11px] text-text-2">Opens pre-filled wa.me message</div>
                        </div>
                      </div>
                      <div className="flex items-center gap-1.5">
                        {deliveryOpts?.whatsapp_url ? (
                          <a
                            href={deliveryOpts.whatsapp_url}
                            target="_blank"
                            rel="noopener noreferrer"
                          >
                            <Button variant="outline" size="sm">
                              Open Chat
                            </Button>
                          </a>
                        ) : (
                          <Button variant="outline" size="sm" disabled>
                            Invalid Phone
                          </Button>
                        )}
                        <Button
                          variant="primary"
                          size="sm"
                          isLoading={isSubmitting}
                          onClick={() => handleMarkShared('MANUAL_WHATSAPP')}
                        >
                          Mark Sent
                        </Button>
                      </div>
                    </div>

                    {/* Email */}
                    <div className="p-3 bg-surface border border-line rounded-lg flex items-center justify-between">
                      <div className="flex items-center gap-2.5">
                        <Mail className="w-4 h-4 text-status-ai" />
                        <div>
                          <div className="text-xs font-semibold text-ink">Email Client Handout</div>
                          <div className="text-[11px] text-text-2">Opens default email composer</div>
                        </div>
                      </div>
                      <div className="flex items-center gap-1.5">
                        {deliveryOpts?.email_url ? (
                          <a href={deliveryOpts.email_url}>
                            <Button variant="outline" size="sm">
                              Compose
                            </Button>
                          </a>
                        ) : (
                          <Button variant="outline" size="sm" disabled>
                            No Email
                          </Button>
                        )}
                        <Button
                          variant="secondary"
                          size="sm"
                          isLoading={isSubmitting}
                          onClick={() => handleMarkShared('MANUAL_EMAIL')}
                        >
                          Mark Sent
                        </Button>
                      </div>
                    </div>
                  </div>

                  <div className="pt-2 flex justify-end">
                    <Button variant="outline" size="sm" onClick={() => setIsModalOpen(false)}>
                      Close
                    </Button>
                  </div>
                </>
              )}
            </div>
          </Modal>
        )}
      </div>
    </AppLayout>
  );
};

