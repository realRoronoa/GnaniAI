import React from 'react';
import { AppLayout } from '@/components/layout/AppLayout';
import { Card } from '@/components/common/Card';
import {
  CalendarDays,
  GitBranch,
  MessageSquare,
  Mail,
  Bell,
  Sparkles,
  Volume2,
  BarChart3,
  ShieldCheck,
  CheckCircle2,
  Clock,
} from 'lucide-react';

export const UpcomingRoadmapPage: React.FC = () => {
  const ROADMAP_ITEMS = [
    {
      id: 1,
      title: 'Patient Online Appointment Booking',
      category: 'Patient Intake',
      icon: <CalendarDays className="w-5 h-5 text-accent" />,
      description:
        'Self-service online booking via verified OTP contact verification and booking reference IDs. Enforces strict zero-patient-login architecture with no patient accounts or passwords.',
      mvpStatus: 'Staff-entered reception booking only',
      v2Status: 'Public web booking link with SMS OTP confirmation',
    },
    {
      id: 2,
      title: 'Advanced Online Appointment & Reception Integration',
      category: 'Clinic Workflow',
      icon: <GitBranch className="w-5 h-5 text-status-ai" />,
      description:
        'Automated real-time bidirectional queue synchronization between online bookings, walk-ins, and doctor OPD consultation room desk queues.',
      mvpStatus: 'Single reception desk manual queueing',
      v2Status: 'Multi-desk automated arrival token kiosks',
    },
    {
      id: 3,
      title: 'Automated WhatsApp Delivery (Meta Cloud API)',
      category: 'Patient Delivery',
      icon: <MessageSquare className="w-5 h-5 text-status-approved" />,
      description:
        'Official Meta WhatsApp Business API integration delivering approved PDF handouts and medication reminders directly to verified patient phone numbers.',
      mvpStatus: 'Manual 1-click wa.me chat link via clinic staff',
      v2Status: 'Automated templated WhatsApp messages upon doctor sign-off',
    },
    {
      id: 4,
      title: 'Automated Email Delivery (SendGrid / AWS SES)',
      category: 'Patient Delivery',
      icon: <Mail className="w-5 h-5 text-status-warn" />,
      description:
        'Automated branded email delivery of bilingual clinical summary PDFs with password-protected PDF attachments matching hospital security guidelines.',
      mvpStatus: 'Manual mailto composer link',
      v2Status: 'Server-side direct automated dispatch with open tracking',
    },
    {
      id: 5,
      title: 'Appointment Automation & Reminders',
      category: 'Operational Retention',
      icon: <Bell className="w-5 h-5 text-accent" />,
      description:
        'Automated scheduled appointment reminders at 24h and 2h before consultation times, automatic no-show tracking, and 1-click patient rescheduling.',
      mvpStatus: 'Manual phone follow-ups',
      v2Status: 'Scheduled background Celery cron reminder jobs',
    },
    {
      id: 6,
      title: 'Advanced AI Clinical Documentation (Live Gnani Engine)',
      category: 'AI Pipeline',
      icon: <Sparkles className="w-5 h-5 text-status-ai" />,
      description:
        'Live production integration with Gnani Prisma v2.5 multi-speaker acoustic models and Evon v3.3 medical LLM for real-time streaming audio transcription.',
      mvpStatus: 'Mock & batch upload speech recognition',
      v2Status: 'Real-time WebSocket streaming audio transcription',
    },
    {
      id: 7,
      title: 'Voice-Based Patient Summary (Gnani Timbre TTS)',
      category: 'Vernacular Accessibility',
      icon: <Volume2 className="w-5 h-5 text-status-approved" />,
      description:
        'High-quality Indian English and Hindi audio narration of approved patient summaries so elderly or non-literate patients can listen to prescription instructions.',
      mvpStatus: 'Written bilingual patient handout PDF',
      v2Status: 'Synthesized voice audio note sent with PDF handout',
    },
    {
      id: 8,
      title: 'Advanced Healthcare Analytics & Insights',
      category: 'Executive Intelligence',
      icon: <BarChart3 className="w-5 h-5 text-status-warn" />,
      description:
        'Clinic-wide epidemiological trends, top diagnosed conditions, medication adherence rates, doctor documentation turnaround times, and OPD queue wait-time metrics.',
      mvpStatus: 'Basic consultation counters and usage limits',
      v2Status: 'Full visual analytical dashboard with CSV/PDF exports',
    },
  ];

  return (
    <AppLayout>
      <div className="space-y-6">
        {/* Header */}
        <div>
          <div className="text-xs font-semibold uppercase tracking-[0.14em] text-accent mb-1">
            PRODUCT EVOLUTION
          </div>
          <h1 className="font-serif text-3xl font-bold text-ink">
            Upcoming Features & V2 Roadmap
          </h1>
          <p className="text-sm text-text-2 mt-1">
            Planned future enhancements for ArogyaScribe outpatient clinical documentation.
          </p>
        </div>

        {/* Human-in-the-Loop Guarantee Banner */}
        <div className="p-4 bg-surface border border-line rounded-xl shadow-card flex items-start gap-3">
          <ShieldCheck className="w-5 h-5 text-status-approved shrink-0 mt-0.5" />
          <div className="text-xs text-text-2 leading-relaxed">
            <strong className="text-ink font-semibold">Core Non-Negotiable Architecture Principle:</strong>
            <p className="mt-0.5">
              Even with future automation (automated reminders, automated delivery, live speech streaming),
              <strong> Doctor Approval is ALWAYS Human-Controlled</strong>. No clinical note or prescription
              will ever be delivered to a patient or stored as an official health record without explicit licensed physician sign-off.
            </p>
          </div>
        </div>

        {/* 8 Feature Cards Grid */}
        <div className="grid md:grid-cols-2 gap-4">
          {ROADMAP_ITEMS.map((item) => (
            <div
              key={item.id}
              className="bg-surface rounded-xl border border-line p-5 shadow-card flex flex-col justify-between space-y-4"
            >
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="p-2 rounded-lg bg-surface-2">{item.icon}</span>
                    <span className="text-[11px] font-bold uppercase tracking-wider text-text-2">
                      {item.category}
                    </span>
                  </div>
                  <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-accent-2 text-ink">
                    COMING SOON — PLANNED FOR FUTURE RELEASE
                  </span>
                </div>

                <h3 className="font-serif text-lg font-bold text-ink">{item.title}</h3>
                <p className="text-xs text-text-2 leading-relaxed">{item.description}</p>
              </div>

              <div className="pt-3 border-t border-line/40 grid grid-cols-2 gap-2 text-[11px]">
                <div>
                  <span className="text-text-2 font-medium block">Current MVP:</span>
                  <span className="text-ink font-semibold">{item.mvpStatus}</span>
                </div>
                <div>
                  <span className="text-accent font-medium block">Planned V2:</span>
                  <span className="text-ink font-semibold">{item.v2Status}</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </AppLayout>
  );
};

