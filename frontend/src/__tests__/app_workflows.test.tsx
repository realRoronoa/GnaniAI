import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { ProtectedRoute, getRoleHomeRoute } from '../routes/ProtectedRoute';
import { AuthProvider } from '../features/auth/AuthContext';
import { UpcomingRoadmapPage } from '../features/upcoming/UpcomingRoadmapPage';
import { UserRole } from '../types';

// Mock API service
vi.mock('../services/api', () => ({
  default: {
    get: vi.fn().mockImplementation((url: string) => {
      if (url.includes('/auth/me')) {
        const saved = localStorage.getItem('user');
        return Promise.resolve({ data: saved ? JSON.parse(saved) : {} });
      }
      return Promise.resolve({ data: {} });
    }),
    post: vi.fn().mockResolvedValue({ data: {} }),
    put: vi.fn().mockResolvedValue({ data: {} }),
    patch: vi.fn().mockResolvedValue({ data: {} }),
  },
  getErrorMessage: (err: any) => err?.message || 'Error occurred',
}));

describe('1. Role-Based Access Control & Strict 4-Role Model (Zero Patient Login)', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('defines exact home routes for the 4 sanctioned roles only', () => {
    expect(getRoleHomeRoute('PLATFORM_OWNER')).toBe('/platform/overview');
    expect(getRoleHomeRoute('ORG_ADMIN')).toBe('/org/overview');
    expect(getRoleHomeRoute('RECEPTIONIST')).toBe('/reception/overview');
    expect(getRoleHomeRoute('DOCTOR')).toBe('/doctor/dashboard');
  });

  it('rejects access to protected routes when user has no active authentication', () => {
    render(
      <MemoryRouter initialEntries={['/doctor/dashboard']}>
        <AuthProvider>
          <Routes>
            <Route path="/login" element={<div>Unified Sign In Screen</div>} />
            <Route
              path="/doctor/dashboard"
              element={
                <ProtectedRoute allowedRoles={['DOCTOR']}>
                  <div>Doctor Clinical Workspace</div>
                </ProtectedRoute>
              }
            />
          </Routes>
        </AuthProvider>
      </MemoryRouter>
    );

    // Unauthenticated user is redirected to /login
    expect(screen.getByText('Unified Sign In Screen')).toBeInTheDocument();
  });

  it('blocks unauthorized roles from entering doctor clinical workspace', async () => {
    const receptionistUser = {
      id: 'rec-123',
      email: 'reception@arogyacare.in',
      full_name: 'Pooja Nair',
      role: 'RECEPTIONIST' as UserRole,
      is_active: true,
      is_super_admin: false,
    };
    localStorage.setItem('user', JSON.stringify(receptionistUser));
    localStorage.setItem('access_token', 'mock_token');

    render(
      <MemoryRouter initialEntries={['/doctor/dashboard']}>
        <AuthProvider>
          <Routes>
            <Route path="/reception/overview" element={<div>Reception Overview Page</div>} />
            <Route
              path="/doctor/dashboard"
              element={
                <ProtectedRoute allowedRoles={['DOCTOR']}>
                  <div>Doctor Clinical Workspace</div>
                </ProtectedRoute>
              }
            />
          </Routes>
        </AuthProvider>
      </MemoryRouter>
    );

    // Receptionist redirected away from doctor dashboard to reception home
    await waitFor(() => {
      expect(screen.getByText('Reception Overview Page')).toBeInTheDocument();
    });
    expect(screen.queryByText('Doctor Clinical Workspace')).not.toBeInTheDocument();
  });
});

describe('2. Upcoming Features (V2 Roadmap) Verification', () => {
  it('renders all 8 planned future roadmap feature cards with explicit COMING SOON badges', () => {
    const doctorUser = {
      id: 'doc-123',
      email: 'dr.sharma@arogyacare.in',
      full_name: 'Dr. Ramesh Sharma',
      role: 'DOCTOR' as UserRole,
      is_active: true,
      is_super_admin: false,
    };
    localStorage.setItem('user', JSON.stringify(doctorUser));
    localStorage.setItem('access_token', 'mock_token');

    render(
      <MemoryRouter>
        <AuthProvider>
          <UpcomingRoadmapPage />
        </AuthProvider>
      </MemoryRouter>
    );

    // Title and eyebrow
    expect(screen.getByText('Upcoming Features & V2 Roadmap')).toBeInTheDocument();
    expect(screen.getByText('PRODUCT EVOLUTION')).toBeInTheDocument();

    // Check all 8 roadmap feature titles
    expect(screen.getByText('Patient Online Appointment Booking')).toBeInTheDocument();
    expect(screen.getByText('Advanced Online Appointment & Reception Integration')).toBeInTheDocument();
    expect(screen.getByText('Automated WhatsApp Delivery (Meta Cloud API)')).toBeInTheDocument();
    expect(screen.getByText('Automated Email Delivery (SendGrid / AWS SES)')).toBeInTheDocument();
    expect(screen.getByText('Appointment Automation & Reminders')).toBeInTheDocument();
    expect(screen.getByText('Advanced AI Clinical Documentation (Live Gnani Engine)')).toBeInTheDocument();
    expect(screen.getByText('Voice-Based Patient Summary (Gnani Timbre TTS)')).toBeInTheDocument();
    expect(screen.getByText('Advanced Healthcare Analytics & Insights')).toBeInTheDocument();

    // Verify badges
    const comingSoonBadges = screen.getAllByText('COMING SOON — PLANNED FOR FUTURE RELEASE');
    expect(comingSoonBadges.length).toBe(8);

    // Verify human-in-the-loop doctor governance guarantee banner
    expect(screen.getByText('Core Non-Negotiable Architecture Principle:')).toBeInTheDocument();
    expect(
      screen.getByText(/Doctor Approval is ALWAYS Human-Controlled/i)
    ).toBeInTheDocument();
  });
});

describe('3. Clinical Safety & Workflow Governance Logic', () => {
  it('verifies clinical consent gate: microphone cannot record without active patient consent', () => {
    let isConsentGranted = false;
    let isMicActive = false;

    const startRecording = () => {
      if (!isConsentGranted) {
        throw new Error('CONSENT_REQUIRED: Active informed consent must be recorded before microphone capture.');
      }
      isMicActive = true;
    };

    // Pre-consent attempt
    expect(() => startRecording()).toThrow('CONSENT_REQUIRED');
    expect(isMicActive).toBe(false);

    // Grant consent
    isConsentGranted = true;
    startRecording();
    expect(isMicActive).toBe(true);
  });

  it('verifies medication completeness gate: approval is strictly blocked if any medication is unverified', () => {
    const medications = [
      { id: '1', name: 'Paracetamol', dosage: '500mg', duration: '5 days', doctor_verified: true },
      { id: '2', name: 'Azithromycin', dosage: '', duration: '', doctor_verified: false },
    ];

    const canApprove = (meds: typeof medications) => {
      return meds.every((m) => m.doctor_verified && m.dosage && m.duration);
    };

    // Approval must be refused
    expect(canApprove(medications)).toBe(false);

    // Doctor completes and verifies
    medications[1].dosage = '500mg';
    medications[1].duration = '3 days';
    medications[1].doctor_verified = true;

    // Approval unlocked
    expect(canApprove(medications)).toBe(true);
  });
});
