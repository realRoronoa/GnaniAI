import React, { useEffect, useState, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { AppLayout } from '@/components/layout/AppLayout';
import { Card } from '@/components/common/Card';
import { StatusBadge } from '@/components/common/StatusBadge';
import { Button } from '@/components/common/Button';
import { Modal } from '@/components/common/Modal';
import api, { getErrorMessage } from '@/services/api';
import {
  Consultation,
  ConsentRecord,
  TranscriptData,
  ClinicalFact,
  MedicationInstruction,
  ReportItem,
  DeliveryOptions,
} from '@/types';
import {
  Mic,
  MicOff,
  Pause,
  Play,
  Square,
  ShieldCheck,
  ShieldAlert,
  Sparkles,
  FileText,
  Pill,
  CheckCircle2,
  AlertTriangle,
  Upload,
  RefreshCw,
  Download,
  Share2,
  Edit,
  ArrowRight,
  ArrowLeft,
  MessageSquare,
  Mail,
  Printer,
} from 'lucide-react';

const FactValueRenderer: React.FC<{ value: any }> = ({ value }) => {
  let parsed = value;
  if (typeof value === 'string') {
    try {
      parsed = JSON.parse(value);
    } catch {
      parsed = value;
    }
  }

  if (typeof parsed !== 'object' || parsed === null) {
    return <span className="font-semibold text-ink text-sm">{String(parsed)}</span>;
  }

  const title = parsed.name || parsed.finding || parsed.condition || parsed.diagnosis || parsed.key || 'Clinical Observation';
  const entries = Object.entries(parsed).filter(
    ([k]) => !['name', 'finding', 'condition', 'diagnosis', 'key'].includes(k)
  );

  return (
    <div className="space-y-1.5">
      <div className="font-semibold text-ink text-sm">
        {title}
      </div>
      {entries.length > 0 && (
        <div className="flex flex-wrap items-center gap-1.5 pt-0.5">
          {entries.map(([k, v]) => {
            const formattedKey = k.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
            const displayVal = typeof v === 'boolean' ? (v ? 'Yes' : 'No') : String(v);
            const isNegative = v === false || displayVal.toLowerCase() === 'denied / absent' || displayVal.toLowerCase() === 'absent';
            return (
              <span
                key={k}
                className={`text-[11px] font-medium px-2 py-0.5 rounded border ${isNegative
                    ? 'bg-status-rec-bg/30 text-status-err border-status-err/20'
                    : 'bg-surface border-line text-text'
                  }`}
              >
                <strong className="text-ink">{formattedKey}:</strong> {displayVal}
              </span>
            );
          })}
        </div>
      )}
    </div>
  );
};

export const ConsultationStudioPage: React.FC = () => {
  const { consultationId } = useParams<{ consultationId: string }>();
  const navigate = useNavigate();

  // Active Stage Tab: 0=Consent & Audio, 1=Transcript & Facts, 2=Medications Guard, 3=Dual Reports & Sign-Off
  const [activeStage, setActiveStage] = useState<number>(0);

  // Core Data States
  const [consultation, setConsultation] = useState<Consultation | null>(null);
  const [consent, setConsent] = useState<ConsentRecord | null>(null);
  const [transcriptData, setTranscriptData] = useState<TranscriptData | null>(null);
  const [facts, setFacts] = useState<ClinicalFact[]>([]);
  const [medications, setMedications] = useState<MedicationInstruction[]>([]);
  const [reports, setReports] = useState<ReportItem[]>([]);
  const [deliveryOpts, setDeliveryOpts] = useState<DeliveryOptions | null>(null);

  const [isLoading, setIsLoading] = useState(true);
  const [isProcessingAI, setIsProcessingAI] = useState(false);
  const [statusBanner, setStatusBanner] = useState<{ text: string; type: 'ok' | 'warn' | 'err' } | null>(null);

  // ----------------------------------------------------
  // Stage 1: Recording & MediaRecorder State
  // ----------------------------------------------------
  const [recState, setRecState] = useState<'IDLE' | 'RECORDING' | 'PAUSED' | 'UPLOADING'>('IDLE');
  const [timerSeconds, setTimerSeconds] = useState(0);
  const [liveTranscript, setLiveTranscript] = useState('');
  const liveTranscriptRef = useRef<string>('');
  const finalTranscriptRef = useRef<string>('');
  const interimTranscriptRef = useRef<string>('');
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const timerIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const recognitionRef = useRef<any>(null);

  const updateLiveTranscript = (text: string) => {
    liveTranscriptRef.current = text;
    setLiveTranscript(text);
    if (textareaRef.current && textareaRef.current.value !== text) {
      textareaRef.current.value = text;
    }
  };

  // Consent Form State
  const [consentLang, setConsentLang] = useState('hi');
  const [consentSubmitting, setConsentSubmitting] = useState(false);

  // ----------------------------------------------------
  // Stage 2: Transcript Editing State
  // ----------------------------------------------------
  const [editingSegmentId, setEditingSegmentId] = useState<string | null>(null);
  const [editedSegmentText, setEditedSegmentText] = useState('');

  // ----------------------------------------------------
  // Stage 3: Medication Verification State
  // ----------------------------------------------------
  const [verifyingMedId, setVerifyingMedId] = useState<string | null>(null);

  // ----------------------------------------------------
  // Stage 4: Reports & Approval State
  // ----------------------------------------------------
  const [selectedReportType, setSelectedReportType] = useState<'DOCTOR_CLINICAL' | 'PATIENT_SUMMARY'>('DOCTOR_CLINICAL');
  const [editedMarkdown, setEditedMarkdown] = useState('');
  const [isSavingDraft, setIsSavingDraft] = useState(false);
  const [isApproving, setIsApproving] = useState(false);

  // Master Data Loader
  const loadConsultationData = async () => {
    if (!consultationId) return;
    setIsLoading(true);
    try {
      const [consRes, transRes, factsRes, medsRes, reportsRes] = await Promise.all([
        api.get(`/consultations/${consultationId}`).catch(() => ({ data: null })),
        api.get(`/consultations/${consultationId}/transcript`).catch(() => ({ data: null })),
        api.get(`/consultations/${consultationId}/clinical-facts`).catch(() => ({ data: [] })),
        api.get(`/consultations/${consultationId}/medications`).catch(() => ({ data: [] })),
        api.get(`/consultations/${consultationId}/reports`).catch(() => ({ data: [] })),
      ]);

      const consData = consRes.data;
      setConsultation(consData);
      setConsent(consData?.consent || null);
      setTranscriptData(transRes.data);
      setFacts(Array.isArray(factsRes.data) ? factsRes.data : []);
      setMedications(Array.isArray(medsRes.data) ? medsRes.data : []);

      const reps = Array.isArray(reportsRes.data) ? reportsRes.data : [];
      setReports(reps);

      const currentRep = reps.find((r) => r.report_type === selectedReportType);
      if (currentRep) {
        setEditedMarkdown(currentRep.content_markdown || '');
      }

      // If approved, also fetch delivery options
      const isAnyApproved = reps.some((r) => r.current_status === 'APPROVED');
      if (isAnyApproved) {
        api.get(`/consultations/${consultationId}/delivery-options`)
          .then((res) => setDeliveryOpts(res.data))
          .catch(() => { });
      }
    } catch (err) {
      console.error('Failed to load consultation studio data:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadConsultationData();
  }, [consultationId]);

  // Update editor markdown when switching reports
  useEffect(() => {
    const cur = reports.find((r) => r.report_type === selectedReportType);
    if (cur) {
      setEditedMarkdown(cur.content_markdown || '');
    }
  }, [selectedReportType, reports]);

  // Timer interval effect
  useEffect(() => {
    if (recState === 'RECORDING') {
      timerIntervalRef.current = setInterval(() => {
        setTimerSeconds((prev) => prev + 1);
      }, 1000);
    } else {
      if (timerIntervalRef.current) clearInterval(timerIntervalRef.current);
    }
    return () => {
      if (timerIntervalRef.current) clearInterval(timerIntervalRef.current);
    };
  }, [recState]);

  // -----------------------------------------------------------------
  // 1. Consent Actions
  // -----------------------------------------------------------------
  const handleGrantConsent = async () => {
    setConsentSubmitting(true);
    setStatusBanner(null);
    try {
      const response = await api.post(`/consultations/${consultationId}/consent`, {
        language: consentLang,
        consent_wording_version: '1.0',
        consent_text_snapshot:
          'Patient explicitly granted informed verbal consent for clinical documentation and AI scribing assistance.',
        is_granted: true,
      });
      setConsent(response.data);
      setStatusBanner({ text: 'Informed consent captured. Microphone unlocked.', type: 'ok' });
      loadConsultationData();
    } catch (err) {
      setStatusBanner({ text: `Consent error: ${getErrorMessage(err)}`, type: 'err' });
    } finally {
      setConsentSubmitting(false);
    }
  };

  const handleWithdrawConsent = async () => {
    if (!window.confirm('Withdraw consent? Recording will be stopped and deleted.')) return;
    setConsentSubmitting(true);
    try {
      await api.post(`/consultations/${consultationId}/consent/withdraw`, {
        withdrawal_reason: 'Patient verbally requested recording withdrawal.',
      });
      setConsent(null);
      if (recState === 'RECORDING' || recState === 'PAUSED') {
        stopRecordingCleanup();
      }
      setStatusBanner({ text: 'Consent withdrawn. Recording halted.', type: 'warn' });
      loadConsultationData();
    } catch (err) {
      alert(`Withdrawal failed: ${getErrorMessage(err)}`);
    } finally {
      setConsentSubmitting(false);
    }
  };

  // -----------------------------------------------------------------
  // 2. Real Browser MediaRecorder Audio Capture
  // -----------------------------------------------------------------
  const startRecording = async () => {
    if (!consent?.is_granted) {
      alert('Patient consent must be captured before starting audio recording.');
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      audioChunksRef.current = [];
      finalTranscriptRef.current = '';
      interimTranscriptRef.current = '';
      updateLiveTranscript('');
      // Clear pre-existing consultation stage data so stale mock data never bleeds in
      setTranscriptData(null);
      setFacts([]);
      setMedications([]);
      setReports([]);

      const mediaRecorder = new MediaRecorder(stream, {
        mimeType: MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
          ? 'audio/webm;codecs=opus'
          : 'audio/webm',
      });

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      mediaRecorder.onstop = async () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
        stream.getTracks().forEach((track) => track.stop());
        const domVal = textareaRef.current?.value?.trim() || '';
        const currentRef = (liveTranscriptRef.current || '').trim();
        const finalCaptured = domVal || currentRef;
        await uploadAudioBlob(audioBlob, finalCaptured);
      };

      // Native browser speech recognition in background for live spoken capture
      const SpeechRec = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
      if (SpeechRec) {
        try {
          const rec = new SpeechRec();
          rec.continuous = true;
          rec.interimResults = true;
          rec.lang = consentLang === 'hi' ? 'hi-IN' : 'en-IN';
          rec.onresult = (evt: any) => {
            let final = '';
            let interim = '';
            for (let i = 0; i < evt.results.length; i++) {
              if (evt.results[i].isFinal) {
                final += evt.results[i][0].transcript + ' ';
              } else {
                interim += evt.results[i][0].transcript + ' ';
              }
            }
            finalTranscriptRef.current = (finalTranscriptRef.current + ' ' + final).trim();
            interimTranscriptRef.current = interim.trim();
            const fullCombined = (finalTranscriptRef.current + ' ' + interimTranscriptRef.current).trim();
            updateLiveTranscript(fullCombined);
          };
          rec.onerror = () => { };
          rec.start();
          recognitionRef.current = rec;
        } catch { }
      }

      mediaRecorderRef.current = mediaRecorder;
      mediaRecorder.start(1000); // 1-second chunks
      setRecState('RECORDING');
      setTimerSeconds(0);
    } catch (err) {
      alert(`Microphone access error: ${getErrorMessage(err)}. You can use the 1-Click Sample Audio fallback below.`);
    }
  };

  const pauseRecording = () => {
    if (mediaRecorderRef.current && recState === 'RECORDING') {
      mediaRecorderRef.current.pause();
      setRecState('PAUSED');
    }
  };

  const resumeRecording = () => {
    if (mediaRecorderRef.current && recState === 'PAUSED') {
      mediaRecorderRef.current.resume();
      setRecState('RECORDING');
    }
  };

  const stopRecording = async () => {
    // 1. First stop SpeechRecognition and wait 400ms for browser to flush final recognition event
    if (recognitionRef.current) {
      try { recognitionRef.current.stop(); } catch { }
    }
    await new Promise((r) => setTimeout(r, 400));

    // 2. Read live DOM value or refs to guarantee real spoken words are preserved
    const domVal = textareaRef.current?.value?.trim() || '';
    const currentRef = (liveTranscriptRef.current || '').trim();
    const resolvedText = domVal || currentRef;
    if (resolvedText) {
      updateLiveTranscript(resolvedText);
    }

    if (mediaRecorderRef.current && (recState === 'RECORDING' || recState === 'PAUSED')) {
      setRecState('UPLOADING');
      mediaRecorderRef.current.stop();
    }
  };

  const stopRecordingCleanup = () => {
    if (recognitionRef.current) {
      try { recognitionRef.current.stop(); } catch { }
    }
    if (mediaRecorderRef.current) {
      try {
        mediaRecorderRef.current.stop();
      } catch { }
    }
    setRecState('IDLE');
    setTimerSeconds(0);
  };

  const uploadAudioBlob = async (blob: Blob, transcriptText?: string) => {
    setRecState('UPLOADING');
    setStatusBanner({ text: 'Uploading encounter audio to secure storage...', type: 'ok' });

    try {
      const domVal = textareaRef.current?.value?.trim() || '';
      const textToSend = (transcriptText || domVal || liveTranscriptRef.current).trim();
      const formData = new FormData();
      formData.append('audio_file', blob, 'consultation_audio.webm');
      if (textToSend) {
        formData.append('transcript_text', textToSend);
      }

      await api.post(`/consultations/${consultationId}/audio`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });

      setStatusBanner({ text: 'Audio uploaded successfully! Running clinical AI pipeline...', type: 'ok' });

      // Automatically trigger AI Pipeline with the actual spoken transcript and is_sample_demo: false
      await runAIPipeline(textToSend, false);
    } catch (err) {
      setStatusBanner({ text: `Audio upload failed: ${getErrorMessage(err)}`, type: 'err' });
      setRecState('IDLE');
    }
  };

  // 1-Click Sample Synthetic Audio Fallback
  const handleUploadSampleAudioAndRun = async () => {
    if (!consent?.is_granted) {
      await handleGrantConsent();
    }

    setRecState('UPLOADING');
    setStatusBanner({ text: 'Generating synthetic consultation audio file...', type: 'ok' });

    try {
      // 1-second PCM silence WAV header
      const wavBytes = new Uint8Array([
        82, 73, 70, 70, 36, 0, 0, 0, 87, 65, 86, 69, 102, 109, 116, 32,
        16, 0, 0, 0, 1, 0, 1, 0, 68, 172, 0, 0, 136, 88, 1, 0, 2, 0, 16, 0,
        100, 97, 116, 97, 0, 0, 0, 0
      ]);
      const blob = new Blob([wavBytes], { type: 'audio/wav' });

      const formData = new FormData();
      formData.append('audio_file', blob, 'sample_consultation.wav');

      await api.post(`/consultations/${consultationId}/audio`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });

      setStatusBanner({ text: 'Sample audio uploaded. Triggering sample AI demo pipeline...', type: 'ok' });
      // Explicitly pass is_sample_demo = true ONLY for this button!
      await runAIPipeline('', true);
    } catch (err) {
      setStatusBanner({ text: `Synthetic pipeline run failed: ${getErrorMessage(err)}`, type: 'err' });
      setRecState('IDLE');
    }
  };

  const runAIPipeline = async (transcriptText?: string, isSampleDemo: boolean = false) => {
    setIsProcessingAI(true);
    try {
      const domVal = textareaRef.current?.value?.trim() || '';
      const textToSend = (transcriptText !== undefined ? transcriptText : (domVal || liveTranscriptRef.current)).trim();
      await api.post(`/consultations/${consultationId}/process`, {
        transcript_text: textToSend || null,
        is_sample_demo: isSampleDemo,
      });
      setStatusBanner({ text: 'AI processing completed! Transcript, Clinical Facts, and Draft Reports generated.', type: 'ok' });
      setRecState('IDLE');
      await loadConsultationData();
      setActiveStage(1); // Advance to Transcript review
    } catch (err) {
      setStatusBanner({ text: `AI pipeline error: ${getErrorMessage(err)}`, type: 'err' });
    } finally {
      setIsProcessingAI(false);
    }
  };

  const handleResetConsultation = async () => {
    if (!window.confirm('Are you sure you want to completely clear and reset this consultation? All recordings, transcripts, facts, medications, and reports will be wiped.')) {
      return;
    }
    try {
      await api.delete(`/consultations/${consultationId}/reset`);
      updateLiveTranscript('');
      finalTranscriptRef.current = '';
      interimTranscriptRef.current = '';
      setTranscriptData(null);
      setFacts([]);
      setMedications([]);
      setReports([]);
      setStatusBanner({ text: 'Consultation wiped clean. Ready for new encounter.', type: 'ok' });
      await loadConsultationData();
    } catch (err) {
      alert(`Reset failed: ${getErrorMessage(err)}`);
    }
  };

  // -----------------------------------------------------------------
  // 3. Transcript Inline Editing
  // -----------------------------------------------------------------
  const handleSaveSegmentEdit = async (segmentId: string) => {
    try {
      await api.put(`/consultations/${consultationId}/transcript`, {
        segments: [{ segment_id: segmentId, corrected_text: editedSegmentText }],
      });
      setEditingSegmentId(null);
      loadConsultationData();
    } catch (err) {
      alert(`Failed to save edit: ${getErrorMessage(err)}`);
    }
  };

  // -----------------------------------------------------------------
  // 4. Clinical Fact Review
  // -----------------------------------------------------------------
  const handleReviewFact = async (factId: string, status: 'ACCEPTED' | 'REJECTED') => {
    try {
      await api.patch(`/consultations/${consultationId}/clinical-facts/${factId}`, {
        doctor_review_status: status,
      });
      loadConsultationData();
    } catch (err) {
      alert(`Fact review failed: ${getErrorMessage(err)}`);
    }
  };

  // -----------------------------------------------------------------
  // 5. Medication Verification
  // -----------------------------------------------------------------
  const handleVerifyMedication = async (med: MedicationInstruction) => {
    setVerifyingMedId(med.id);
    try {
      await api.put(`/consultations/${consultationId}/medications/${med.id}`, {
        medication_name: med.medication_name,
        dosage: med.dosage || '1 tablet',
        frequency: med.frequency || 'Once daily',
        duration: med.duration || '5 days',
        doctor_verified: true,
      });
      loadConsultationData();
    } catch (err) {
      alert(`Medication verification failed: ${getErrorMessage(err)}`);
    } finally {
      setVerifyingMedId(null);
    }
  };

  // -----------------------------------------------------------------
  // 6. Report Draft Editing & Approval
  // -----------------------------------------------------------------
  const handleSaveReportDraft = async () => {
    setIsSavingDraft(true);
    try {
      await api.put(`/consultations/${consultationId}/reports/${selectedReportType}`, {
        rendered_markdown: editedMarkdown,
      });
      setStatusBanner({
        text: 'Report draft saved. If previously approved, a new DOCTOR_EDITED_DRAFT version was created.',
        type: 'ok',
      });
      loadConsultationData();
    } catch (err) {
      setStatusBanner({ text: `Failed to save draft: ${getErrorMessage(err)}`, type: 'err' });
    } finally {
      setIsSavingDraft(false);
    }
  };

  const handleApproveReports = async () => {
    const unverifiedMeds = medications.filter((m) => !m.is_historical && (!m.doctor_verified || (m.uncertainty_flags && m.uncertainty_flags.length > 0)));
    if (unverifiedMeds.length > 0) {
      alert(`Safety Gate Active: You have ${unverifiedMeds.length} unverified medication instruction(s). Please verify all prescriptions in Stage 3 before approving.`);
      setActiveStage(2);
      return;
    }

    if (!window.confirm('Digitally approve clinical encounter? This will lock the version with a SHA-256 digital signature and generate official PDFs.')) {
      return;
    }

    setIsApproving(true);
    try {
      await api.post(`/consultations/${consultationId}/approve`);
      setStatusBanner({
        text: 'Encounter successfully APPROVED! PDFs generated and digitally signed.',
        type: 'ok',
      });
      loadConsultationData();
    } catch (err) {
      alert(`Approval blocked: ${getErrorMessage(err)}`);
    } finally {
      setIsApproving(false);
    }
  };

  const handleDownloadPdf = async (reportType: 'DOCTOR_CLINICAL' | 'PATIENT_SUMMARY') => {
    try {
      setStatusBanner({
        text: `Downloading ${reportType === 'DOCTOR_CLINICAL' ? 'Doctor Clinical Note' : 'Patient Handout'} PDF...`,
        type: 'ok',
      });
      const response = await api.get(`/consultations/${consultationId}/reports/${reportType}/pdf`, {
        responseType: 'blob',
      });
      const blob = new Blob([response.data], { type: 'application/pdf' });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${reportType === 'DOCTOR_CLINICAL' ? 'doctor_clinical_note' : 'patient_summary'}_${consultationId}.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
      setStatusBanner({ text: 'PDF downloaded successfully!', type: 'ok' });
    } catch (err) {
      alert(`PDF download failed: ${getErrorMessage(err)}`);
    }
  };

  const formatTimer = (sec: number) => {
    const m = Math.floor(sec / 60);
    const s = sec % 60;
    return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
  };

  const unverifiedCount = medications.filter((m) => !m.is_historical && !m.doctor_verified).length;
  const currentReport = reports.find((r) => r.report_type === selectedReportType);
  const isApproved = currentReport?.current_status === 'APPROVED';

  return (
    <AppLayout>
      <div className="space-y-6">
        {/* Top Header Bar */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-4 border-b border-line">
          <div>
            <Button
              variant="outline"
              size="sm"
              onClick={() => navigate('/doctor/dashboard')}
              leftIcon={<ArrowLeft className="w-3.5 h-3.5" />}
              className="mb-2"
            >
              Back to Dashboard
            </Button>
            <div className="flex items-center gap-3">
              <h1 className="font-serif text-3xl font-bold text-ink">
                Consultation Studio
              </h1>
              <StatusBadge status={consultation?.status || 'SETUP'} />
            </div>
            <div className="text-xs text-text-2 mt-1 font-mono">
              Encounter ID: {consultationId}
            </div>
          </div>

          <div className="flex items-center gap-3">
            <div className="hidden md:flex items-center gap-1.5 px-3 py-1 bg-surface-2 border border-line rounded-full text-[11px] font-medium text-text-2">
              <span className="w-2 h-2 rounded-full bg-status-approved"></span>
              <span>Gnani Indic Engine: <strong className="text-ink">Credit-Protected Cache Active</strong></span>
            </div>
            <Button
              variant="outline"
              size="sm"
              leftIcon={<RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />}
              onClick={loadConsultationData}
            >
              Refresh Studio
            </Button>
          </div>
        </div>

        {/* Global Notification Banner */}
        {statusBanner && (
          <div
            className={`p-3 rounded-lg text-xs font-semibold flex items-center justify-between border ${statusBanner.type === 'ok'
                ? 'bg-status-approved-bg text-status-approved border-status-approved/30'
                : statusBanner.type === 'warn'
                  ? 'bg-status-warn-bg text-status-warn border-status-warn/30'
                  : 'bg-status-rec-bg text-status-err border-status-err/30'
              }`}
          >
            <span>{statusBanner.text}</span>
            <button
              onClick={() => setStatusBanner(null)}
              className="text-xs underline hover:opacity-80"
            >
              Dismiss
            </button>
          </div>
        )}

        {/* 4-Stage Navigation Bar */}
        <div className="flex gap-2 border-b border-line pb-2 overflow-x-auto">
          {[
            { id: 0, label: '1. Consent & Recording', icon: <Mic className="w-3.5 h-3.5" /> },
            { id: 1, label: '2. Transcript & Provenance', icon: <FileText className="w-3.5 h-3.5" /> },
            {
              id: 2,
              label: `3. Medication Guard (${unverifiedCount} unverified)`,
              icon: <Pill className="w-3.5 h-3.5" />,
              badge: unverifiedCount > 0 ? 'warn' : 'ok',
            },
            { id: 3, label: '4. Dual Reports & Sign-Off', icon: <CheckCircle2 className="w-3.5 h-3.5" /> },
          ].map((stage) => (
            <button
              key={stage.id}
              onClick={() => setActiveStage(stage.id)}
              className={`flex items-center gap-2 px-4 py-2 rounded-md text-xs font-semibold tracking-wide transition-all ${activeStage === stage.id
                  ? 'bg-ink text-surface shadow-sm'
                  : 'bg-surface text-text-2 hover:bg-surface-2 hover:text-ink border border-line/60'
                }`}
            >
              <span>{stage.icon}</span>
              <span>{stage.label}</span>
              {stage.badge === 'warn' && (
                <span className="w-2 h-2 rounded-full bg-status-warn" />
              )}
            </button>
          ))}
        </div>

        {/* ========================================================== */}
        {/* STAGE 1: Consent Gate & Recording Studio                   */}
        {/* ========================================================== */}
        {activeStage === 0 && (
          <div className="space-y-6">
            {/* Informed Consent Card */}
            <Card
              title="Mandatory Informed Patient Consent"
              subtitle="Explicit patient consent is required before recording audio."
            >
              {consent?.is_granted ? (
                <div className="p-4 bg-status-approved-bg/60 border border-status-approved/30 rounded-lg flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
                  <div className="space-y-1 text-xs">
                    <div className="font-bold text-status-approved flex items-center gap-1.5 uppercase tracking-wider">
                      <ShieldCheck className="w-4 h-4" />
                      Consent Recorded & Active
                    </div>
                    <div className="text-text">
                      Language: <span className="uppercase font-semibold">{consent.consent_language}</span> • Wording Version: {consent.wording_version}
                    </div>
                    <div className="text-text-2 italic">
                      "{consent.consent_text_snapshot || 'Verbal consent granted by patient for documentation.'}"
                    </div>
                  </div>

                  <Button
                    variant="destructive"
                    size="sm"
                    isLoading={consentSubmitting}
                    onClick={handleWithdrawConsent}
                  >
                    Withdraw Consent
                  </Button>
                </div>
              ) : (
                <div className="space-y-4">
                  <div className="p-3.5 bg-status-warn-bg border border-status-warn/30 rounded-lg text-xs text-status-warn space-y-1">
                    <div className="font-bold flex items-center gap-1.5 uppercase tracking-wider">
                      <AlertTriangle className="w-4 h-4" />
                      Consent Required Before Audio Recording
                    </div>
                    <p>
                      Explain to the patient that audio will be captured to assist the doctor with documentation.
                      The doctor checks every draft and the audio is stored in private encrypted storage in India.
                    </p>
                  </div>

                  <div className="flex items-center gap-4 flex-wrap">
                    <div>
                      <label className="block text-xs font-semibold text-text uppercase mb-1">
                        Vernacular Language
                      </label>
                      <select
                        value={consentLang}
                        onChange={(e) => setConsentLang(e.target.value)}
                        className="px-3 py-1.5 bg-surface-2 border border-line rounded text-xs text-ink font-medium"
                      >
                        <option value="en">English</option>
                        <option value="hi">Hindi (हिन्दी)</option>
                        <option value="ta">Tamil (தமிழ்)</option>
                        <option value="te">Telugu (తెలుగు)</option>
                        <option value="kn">Kannada (ಕನ್ನಡ)</option>
                        <option value="ml">Malayalam (മലയാളം)</option>
                        <option value="mr">Marathi (मराठी)</option>
                        <option value="bn">Bengali (বাংলা)</option>
                        <option value="gu">Gujarati (ગુજરાતી)</option>
                      </select>
                    </div>

                    <div className="pt-5">
                      <Button
                        variant="primary"
                        isLoading={consentSubmitting}
                        onClick={handleGrantConsent}
                      >
                        Capture & Confirm Patient Consent
                      </Button>
                    </div>
                  </div>
                </div>
              )}
            </Card>

            {/* Audio Recording Controls */}
            <Card
              title="Acoustic Ambient Recording Studio"
              subtitle="Web MediaRecorder audio capture with 16kHz speech recognition"
            >
              <div className="space-y-6">
                {/* Explicit Text Recording Badge & Timer */}
                <div className="flex items-center justify-between p-4 bg-surface-2 rounded-lg border border-line">
                  <div className="flex items-center gap-3">
                    <div
                      className={`w-3.5 h-3.5 rounded-full ${recState === 'RECORDING'
                          ? 'bg-status-rec animate-pulse'
                          : recState === 'PAUSED'
                            ? 'bg-status-warn'
                            : 'bg-line'
                        }`}
                    />
                    <div>
                      <div className="text-xs font-bold uppercase tracking-wider text-ink">
                        {recState === 'RECORDING'
                          ? 'RECORDING ACTIVE — MIC LIVE'
                          : recState === 'PAUSED'
                            ? 'RECORDING PAUSED'
                            : recState === 'UPLOADING'
                              ? 'UPLOADING AUDIO ASSET'
                              : 'STUDIO READY'}
                      </div>
                      <div className="text-[11px] text-text-2">
                        Microphone status: {consent?.is_granted ? 'Authorized' : 'Locked by Consent Gate'}
                      </div>
                    </div>
                  </div>

                  <div className="text-3xl font-mono font-bold text-ink">
                    {formatTimer(timerSeconds)}
                  </div>
                </div>

                {/* Primary Recording Buttons */}
                <div className="flex items-center gap-3 flex-wrap">
                  {recState === 'IDLE' && (
                    <div className="flex items-center gap-3 flex-wrap">
                      <Button
                        variant="primary"
                        disabled={!consent?.is_granted || isProcessingAI}
                        leftIcon={<Mic className="w-4 h-4 text-status-rec" />}
                        onClick={startRecording}
                      >
                        Start Microphone Recording
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        disabled={isProcessingAI}
                        leftIcon={<RefreshCw className="w-3.5 h-3.5 text-text-2" />}
                        onClick={handleResetConsultation}
                      >
                        Clear & Reset Consultation Data
                      </Button>
                    </div>
                  )}

                  {recState === 'RECORDING' && (
                    <>
                      <Button
                        variant="outline"
                        leftIcon={<Pause className="w-4 h-4 text-status-warn" />}
                        onClick={pauseRecording}
                      >
                        Pause
                      </Button>
                      <Button
                        variant="primary"
                        leftIcon={<Square className="w-4 h-4 text-status-err" />}
                        onClick={stopRecording}
                      >
                        Stop & Upload Audio
                      </Button>
                    </>
                  )}

                  {recState === 'PAUSED' && (
                    <>
                      <Button
                        variant="primary"
                        leftIcon={<Play className="w-4 h-4" />}
                        onClick={resumeRecording}
                      >
                        Resume Recording
                      </Button>
                      <Button
                        variant="outline"
                        leftIcon={<Square className="w-4 h-4" />}
                        onClick={stopRecording}
                      >
                        Stop & Upload Audio
                      </Button>
                    </>
                  )}

                  {recState === 'UPLOADING' && (
                    <Button variant="primary" disabled isLoading>
                      Uploading & Processing...
                    </Button>
                  )}
                </div>

                {/* Live Spoken Dictation / Doctor Notes Area */}
                <div className="pt-3 border-t border-line/40 space-y-2">
                  <div className="flex items-center justify-between">
                    <label className="text-xs font-semibold text-text uppercase tracking-wider flex items-center gap-1.5">
                      <span className={`w-2 h-2 rounded-full ${recState === 'RECORDING' ? 'bg-status-rec animate-pulse' : 'bg-line'}`} />
                      Live Spoken Words & Doctor Clinical Notes
                    </label>
                    <span className="text-[11px] text-text-2">Transcribed live from your voice / editable</span>
                  </div>
                  <textarea
                    ref={textareaRef}
                    rows={3}
                    value={liveTranscript}
                    onChange={(e) => updateLiveTranscript(e.target.value)}
                    placeholder="Speak into your microphone or type consultation findings directly here... Your actual spoken words will be saved and official clinical reports generated from them."
                    className="w-full p-3 bg-surface-2/60 border border-line rounded-lg text-sm text-ink focus:outline-none focus:ring-1 focus:ring-ink"
                  />
                  {liveTranscript.trim() && recState === 'IDLE' && (
                    <div className="flex justify-end pt-1">
                      <Button
                        variant="secondary"
                        size="sm"
                        isLoading={isProcessingAI}
                        leftIcon={<Sparkles className="w-3.5 h-3.5" />}
                        onClick={() => runAIPipeline(liveTranscriptRef.current)}
                      >
                        Process Dictated Spoken Notes with AI
                      </Button>
                    </div>
                  )}
                </div>

                {/* 1-Click Fallback Button for Testers Without Physical Mic */}
                <div className="pt-4 border-t border-line/40 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
                  <div className="text-xs text-text-2">
                    <strong className="text-ink">No physical microphone on this machine?</strong>
                    <p>Trigger the full end-to-end pipeline using synthetic test audio in 1 click.</p>
                  </div>

                  <Button
                    variant="accent"
                    size="sm"
                    isLoading={isProcessingAI || recState === 'UPLOADING'}
                    leftIcon={<Sparkles className="w-3.5 h-3.5" />}
                    onClick={handleUploadSampleAudioAndRun}
                  >
                    Upload Sample Audio & Run AI Pipeline
                  </Button>
                </div>
              </div>
            </Card>
          </div>
        )}

        {/* ========================================================== */}
        {/* STAGE 2: Transcript & Clinical Provenance Viewer          */}
        {/* ========================================================== */}
        {activeStage === 1 && (
          <div className="grid lg:grid-cols-12 gap-6">
            {/* Transcript Editor (Left 6 cols) */}
            <div className="lg:col-span-6 space-y-4">
              <Card
                title="Diarized Audio Transcript"
                subtitle="Speaker-labeled segments with inline doctor corrections"
              >
                {transcriptData?.segments?.length === 0 ? (
                  <div className="text-xs text-text-2 py-6 text-center">
                    No transcript available. Run recording in Stage 1 first.
                  </div>
                ) : (
                  <div className="space-y-3 max-h-[600px] overflow-y-auto pr-1">
                    {transcriptData?.segments?.map((seg) => {
                      const isEditing = editingSegmentId === seg.id;
                      return (
                        <div
                          key={seg.id}
                          className="p-3 bg-surface-2/50 border border-line rounded-lg text-xs space-y-1.5"
                        >
                          <div className="flex items-center justify-between text-[11px]">
                            <span
                              className={`font-bold uppercase tracking-wider ${seg.speaker_label === 'DOCTOR' ? 'text-accent' : 'text-status-ai'
                                }`}
                            >
                              {seg.speaker_label}
                            </span>
                            <span className="font-mono text-text-2">
                              {Math.floor(seg.start_time_ms / 1000)}s — {Math.floor(seg.end_time_ms / 1000)}s
                            </span>
                          </div>

                          {isEditing ? (
                            <div className="space-y-2 pt-1">
                              <textarea
                                rows={2}
                                value={editedSegmentText}
                                onChange={(e) => setEditedSegmentText(e.target.value)}
                                className="w-full p-2 bg-surface border border-line rounded text-xs text-ink focus:outline-none"
                              />
                              <div className="flex justify-end gap-1.5">
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  onClick={() => setEditingSegmentId(null)}
                                >
                                  Cancel
                                </Button>
                                <Button
                                  variant="primary"
                                  size="sm"
                                  onClick={() => handleSaveSegmentEdit(seg.id)}
                                >
                                  Save Correction
                                </Button>
                              </div>
                            </div>
                          ) : (
                            <div className="flex items-start justify-between gap-2">
                              <div>
                                <p className="text-ink leading-relaxed">
                                  {seg.corrected_text || seg.original_text}
                                </p>
                                {seg.corrected_text && (
                                  <div className="text-[10px] text-text-2 italic mt-1">
                                    Original AI text: "{seg.original_text}"
                                  </div>
                                )}
                              </div>
                              <Button
                                variant="ghost"
                                size="sm"
                                className="h-6 w-6 p-0 shrink-0"
                                onClick={() => {
                                  setEditingSegmentId(seg.id);
                                  setEditedSegmentText(seg.corrected_text || seg.original_text);
                                }}
                              >
                                <Edit className="w-3 h-3 text-text-2" />
                              </Button>
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                )}
              </Card>
            </div>

            {/* Clinical Facts & Grounding Evidence (Right 6 cols) */}
            <div className="lg:col-span-6 space-y-4">
              <Card
                title="Clinical Facts & Evidence Grounding"
                subtitle="Source-linked entities extracted from consultation dialogue"
              >
                {facts.length === 0 ? (
                  <div className="text-xs text-text-2 py-6 text-center">
                    No clinical facts extracted yet.
                  </div>
                ) : (
                  <div className="space-y-3 max-h-[600px] overflow-y-auto pr-1">
                    {facts.map((fact) => (
                      <div
                        key={fact.id}
                        className={`p-3 rounded-lg border text-xs space-y-2 ${fact.doctor_review_status === 'ACCEPTED'
                            ? 'bg-status-approved-bg/40 border-status-approved/30'
                            : fact.doctor_review_status === 'REJECTED'
                              ? 'bg-status-rec-bg/30 border-status-err/20 opacity-60'
                              : 'bg-surface-2 border-line'
                          }`}
                      >
                        <div className="flex items-center justify-between">
                          <span className="font-bold uppercase tracking-wider text-[10px] text-text-2">
                            {fact.category} • {fact.fact_key}
                          </span>
                          <span
                            className={`text-[10px] font-semibold px-2 py-0.5 rounded ${fact.doctor_review_status === 'ACCEPTED'
                                ? 'bg-status-approved-bg text-status-approved'
                                : fact.doctor_review_status === 'REJECTED'
                                  ? 'bg-status-rec-bg text-status-err'
                                  : 'bg-status-warn-bg text-status-warn'
                              }`}
                          >
                            {fact.doctor_review_status}
                          </span>
                        </div>

                        <FactValueRenderer value={fact.fact_value} />

                        {/* Transcript Grounding Evidence */}
                        {fact.evidence && fact.evidence.length > 0 && (
                          <div className="p-2 bg-surface/70 rounded border border-line/40 text-[11px] text-text-2 italic">
                            <span className="font-semibold text-ink">Grounding Quote: </span>
                            "{fact.evidence[0].evidence_quotation}"
                          </div>
                        )}

                        {/* Review Controls */}
                        <div className="flex items-center justify-end gap-1.5 pt-1">
                          <Button
                            variant="outline"
                            size="sm"
                            className="text-xs h-6 px-2 text-status-approved"
                            onClick={() => handleReviewFact(fact.id, 'ACCEPTED')}
                          >
                            Accept
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            className="text-xs h-6 px-2 text-status-err"
                            onClick={() => handleReviewFact(fact.id, 'REJECTED')}
                          >
                            Reject
                          </Button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </Card>
            </div>
          </div>
        )}

        {/* ========================================================== */}
        {/* STAGE 3: Medication Verification & Safety Gate             */}
        {/* ========================================================== */}
        {activeStage === 2 && (
          <div className="space-y-4">
            <Card
              title="Medication Safety & Verification Gate"
              subtitle="All medications require explicit doctor confirmation of dose, frequency & duration."
            >
              {unverifiedCount > 0 ? (
                <div className="p-3.5 bg-status-warn-bg border border-status-warn/30 rounded-lg text-xs text-status-warn mb-4 font-medium flex items-center gap-2">
                  <AlertTriangle className="w-4 h-4 shrink-0" />
                  <span>
                    Approval Blocked: {unverifiedCount} prescription(s) have unverified dosages or uncertainty flags.
                    Verify each medication row below to enable report sign-off.
                  </span>
                </div>
              ) : (
                <div className="p-3 bg-status-approved-bg border border-status-approved/30 rounded-lg text-xs text-status-approved mb-4 font-semibold flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 shrink-0" />
                  <span>All medication instructions verified. Safety gate cleared for Doctor Sign-Off!</span>
                </div>
              )}

              {medications.length === 0 ? (
                <div className="text-xs text-text-2 py-6 text-center">
                  No medications extracted for this consultation.
                </div>
              ) : (
                <div className="space-y-3">
                  {medications.map((med) => {
                    const isUnverified = !med.doctor_verified || (med.uncertainty_flags && med.uncertainty_flags.length > 0);
                    return (
                      <div
                        key={med.id}
                        className={`p-4 rounded-lg border flex flex-col md:flex-row md:items-center md:justify-between gap-4 ${isUnverified
                            ? 'bg-status-warn-bg/30 border-status-warn/40'
                            : 'bg-surface border-line'
                          }`}
                      >
                        <div className="space-y-1">
                          <div className="flex items-center gap-2">
                            <span className="font-bold text-ink text-base">
                              {med.medication_name} {med.strength && `(${med.strength})`}
                            </span>
                            {med.is_historical && (
                              <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-surface-2 text-text-2 border border-line">
                                Historical
                              </span>
                            )}
                            <span
                              className={`text-[10px] font-semibold px-2 py-0.5 rounded ${med.doctor_verified
                                  ? 'bg-status-approved-bg text-status-approved'
                                  : 'bg-status-warn-bg text-status-warn'
                                }`}
                            >
                              {med.doctor_verified ? 'Verified' : 'Verification Needed'}
                            </span>
                          </div>

                          <div className="text-xs text-text-2 font-mono flex items-center gap-3">
                            <span>Dosage: <strong className="text-ink">{med.dosage || 'Missing'}</strong></span>
                            <span>•</span>
                            <span>Frequency: <strong className="text-ink">{med.frequency || 'Missing'}</strong></span>
                            <span>•</span>
                            <span>Duration: <strong className="text-ink">{med.duration || 'Missing'}</strong></span>
                          </div>

                          {med.uncertainty_flags && med.uncertainty_flags.length > 0 && (
                            <div className="text-[11px] font-semibold text-status-err">
                              ⚠️ Flags: {med.uncertainty_flags.join(', ')}
                            </div>
                          )}
                        </div>

                        <div>
                          <Button
                            variant={med.doctor_verified ? 'outline' : 'primary'}
                            size="sm"
                            isLoading={verifyingMedId === med.id}
                            leftIcon={<CheckCircle2 className="w-3.5 h-3.5" />}
                            onClick={() => handleVerifyMedication(med)}
                          >
                            {med.doctor_verified ? 'Re-verify' : 'Verify Prescription'}
                          </Button>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </Card>
          </div>
        )}

        {/* ========================================================== */}
        {/* STAGE 4: Dual Reports Editor & Doctor Sign-Off             */}
        {/* ========================================================== */}
        {activeStage === 3 && (
          <div className="space-y-6">
            {/* Report Selector Tabs */}
            <div className="flex items-center justify-between border-b border-line pb-2 flex-wrap gap-3">
              <div className="flex gap-2">
                <button
                  onClick={() => setSelectedReportType('DOCTOR_CLINICAL')}
                  className={`px-4 py-2 rounded-md text-xs font-semibold tracking-wide transition-colors ${selectedReportType === 'DOCTOR_CLINICAL'
                      ? 'bg-ink text-surface shadow-sm'
                      : 'bg-surface text-text-2 hover:bg-surface-2'
                    }`}
                >
                  Doctor Clinical Note (SOAP)
                </button>
                <button
                  onClick={() => setSelectedReportType('PATIENT_SUMMARY')}
                  className={`px-4 py-2 rounded-md text-xs font-semibold tracking-wide transition-colors ${selectedReportType === 'PATIENT_SUMMARY'
                      ? 'bg-ink text-surface shadow-sm'
                      : 'bg-surface text-text-2 hover:bg-surface-2'
                    }`}
                >
                  Bilingual Patient Handout (मरीज़ सारांश)
                </button>
              </div>

              {currentReport && (
                <div className="flex items-center gap-2">
                  <span className="font-mono text-xs font-bold text-ink">
                    Version v{currentReport.current_version_number}
                  </span>
                  <StatusBadge status={currentReport.current_status} />
                </div>
              )}
            </div>

            {/* Markdown Report Editor */}
            <Card
              title={
                selectedReportType === 'DOCTOR_CLINICAL'
                  ? 'Doctor Clinical Record (Internal Encounter Note)'
                  : 'Patient Vernacular Summary (Handout Copy)'
              }
              subtitle="Edit sections directly before official cryptographic doctor sign-off."
            >
              <div className="space-y-4">
                <textarea
                  rows={16}
                  value={editedMarkdown}
                  onChange={(e) => setEditedMarkdown(e.target.value)}
                  className="w-full p-4 bg-surface border border-line rounded-lg font-mono text-xs text-ink leading-relaxed focus:outline-none focus:ring-1 focus:ring-ink"
                  placeholder="Clinical report content..."
                />

                <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 pt-2 border-t border-line/40">
                  <Button
                    variant="outline"
                    size="sm"
                    isLoading={isSavingDraft}
                    onClick={handleSaveReportDraft}
                  >
                    Save Draft Edits
                  </Button>

                  <div className="flex items-center gap-3">
                    <Button
                      variant="primary"
                      size="lg"
                      isLoading={isApproving}
                      disabled={unverifiedCount > 0}
                      leftIcon={<ShieldCheck className="w-5 h-5 text-status-approved" />}
                      onClick={handleApproveReports}
                    >
                      Digitally Approve & Generate PDFs
                    </Button>
                  </div>
                </div>

                {isApproved && (
                  <div className="p-4 bg-status-approved-bg/60 border border-status-approved/30 rounded-lg space-y-3">
                    <div className="text-xs font-bold text-status-approved uppercase tracking-wider flex items-center gap-2">
                      <CheckCircle2 className="w-4 h-4" />
                      Approved & Signed with SHA-256 Signature
                    </div>

                    <div className="flex items-center gap-3 flex-wrap">
                      <Button
                        variant="outline"
                        size="sm"
                        leftIcon={<Download className="w-4 h-4" />}
                        onClick={() => handleDownloadPdf('DOCTOR_CLINICAL')}
                      >
                        Doctor Note PDF
                      </Button>

                      <Button
                        variant="outline"
                        size="sm"
                        leftIcon={<Download className="w-4 h-4" />}
                        onClick={() => handleDownloadPdf('PATIENT_SUMMARY')}
                      >
                        Patient Handout PDF
                      </Button>

                      <Button
                        variant="outline"
                        size="sm"
                        leftIcon={<Printer className="w-4 h-4" />}
                        onClick={() => window.print()}
                      >
                        Print Indic Summary (Unicode)
                      </Button>

                      {deliveryOpts?.whatsapp_url && (
                        <a
                          href={deliveryOpts.whatsapp_url}
                          target="_blank"
                          rel="noopener noreferrer"
                        >
                          <Button
                            variant="primary"
                            size="sm"
                            leftIcon={<MessageSquare className="w-4 h-4" />}
                          >
                            Send WhatsApp
                          </Button>
                        </a>
                      )}
                    </div>
                  </div>
                )}
              </div>
            </Card>
          </div>
        )}
      </div>

      {/* Printable Indic Report Container (Visible Only in Print) */}
      <div className={`printable-report p-8 ${consent?.consent_language || 'en'}`}>
        <div className="border-b-2 border-black pb-4 mb-6 flex justify-between items-center">
          <div>
            <h1 className="text-2xl font-bold font-serif">ArogyaScribe Clinical Summary</h1>
            <p className="text-sm text-gray-600">Patient Vernacular Medical Record</p>
          </div>
          <div className="text-right text-xs">
            <p><strong>Encounter ID:</strong> {consultationId}</p>
            <p><strong>Language:</strong> {(consent?.consent_language || 'en').toUpperCase()}</p>
          </div>
        </div>

        <div className="whitespace-pre-wrap font-sans text-sm leading-relaxed text-black">
          {editedMarkdown || 'No approved clinical summary available.'}
        </div>

        <div className="mt-8 pt-4 border-t border-gray-400 text-[10px] text-gray-500 flex justify-between">
          <span>Digitally Verified & Signed by Doctor</span>
          <span>ArogyaScribe Sovereign Clinical AI Platform</span>
        </div>
      </div>
    </AppLayout>
  );
};

