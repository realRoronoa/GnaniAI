import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { ProtectedRoute } from '@/routes/ProtectedRoute';
import { LandingPage } from '@/features/public/LandingPage';
import { LoginPage } from '@/features/auth/LoginPage';

// Platform Owner pages
import { PlatformOverviewPage } from '@/features/platform-admin/PlatformOverviewPage';
import { OrganizationsPage } from '@/features/platform-admin/OrganizationsPage';
import { OrganizationDetailPage } from '@/features/platform-admin/OrganizationDetailPage';
import { PlansBillingPage } from '@/features/platform-admin/PlansBillingPage';
import { AuditLogPage } from '@/features/platform-admin/AuditLogPage';

// Organization Admin pages
import { OrgOverviewPage } from '@/features/organizations/OrgOverviewPage';
import { OrgBranchesPage } from '@/features/organizations/OrgBranchesPage';
import { OrgStaffPage } from '@/features/organizations/OrgStaffPage';
import { OrgSchedulesPage } from '@/features/organizations/OrgSchedulesPage';

// Receptionist Console pages
import { ReceptionOverviewPage } from '@/features/reception/ReceptionOverviewPage';
import { PatientsDirectoryPage } from '@/features/reception/PatientsDirectoryPage';
import { AppointmentsPage } from '@/features/reception/AppointmentsPage';
import { ReportDeliveryPage } from '@/features/reception/ReportDeliveryPage';

// Doctor Clinical Workspace pages
import { DoctorDashboardPage } from '@/features/doctors/DoctorDashboardPage';
import { PatientLongitudinalHistoryPage } from '@/features/doctors/PatientLongitudinalHistoryPage';
import { ConsultationStudioPage } from '@/features/doctors/ConsultationStudioPage';

// Upcoming Roadmap V2
import { UpcomingRoadmapPage } from '@/features/upcoming/UpcomingRoadmapPage';

export const AppRoutes: React.FC = () => {
  return (
    <Routes>
      {/* Public Marketing & Authentication */}
      <Route path="/" element={<LandingPage />} />
      <Route path="/login" element={<LoginPage />} />

      {/* Platform Owner Workspace */}
      <Route
        path="/platform"
        element={<Navigate to="/platform/overview" replace />}
      />
      <Route
        path="/platform/overview"
        element={
          <ProtectedRoute allowedRoles={['PLATFORM_OWNER']}>
            <PlatformOverviewPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/platform/organizations"
        element={
          <ProtectedRoute allowedRoles={['PLATFORM_OWNER']}>
            <OrganizationsPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/platform/organizations/:organizationId"
        element={
          <ProtectedRoute allowedRoles={['PLATFORM_OWNER']}>
            <OrganizationDetailPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/platform/plans"
        element={
          <ProtectedRoute allowedRoles={['PLATFORM_OWNER']}>
            <PlansBillingPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/platform/audit-log"
        element={
          <ProtectedRoute allowedRoles={['PLATFORM_OWNER']}>
            <AuditLogPage />
          </ProtectedRoute>
        }
      />

      {/* Organization Admin Workspace */}
      <Route path="/org" element={<Navigate to="/org/overview" replace />} />
      <Route
        path="/org/overview"
        element={
          <ProtectedRoute allowedRoles={['ORG_ADMIN']}>
            <OrgOverviewPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/org/branches"
        element={
          <ProtectedRoute allowedRoles={['ORG_ADMIN']}>
            <OrgBranchesPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/org/staff"
        element={
          <ProtectedRoute allowedRoles={['ORG_ADMIN']}>
            <OrgStaffPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/org/schedules"
        element={
          <ProtectedRoute allowedRoles={['ORG_ADMIN']}>
            <OrgSchedulesPage />
          </ProtectedRoute>
        }
      />

      {/* Receptionist Console */}
      <Route
        path="/reception"
        element={<Navigate to="/reception/overview" replace />}
      />
      <Route
        path="/reception/overview"
        element={
          <ProtectedRoute allowedRoles={['RECEPTIONIST', 'ORG_ADMIN']}>
            <ReceptionOverviewPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/reception/queue"
        element={
          <ProtectedRoute allowedRoles={['RECEPTIONIST', 'ORG_ADMIN']}>
            <ReceptionOverviewPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/reception/patients"
        element={
          <ProtectedRoute allowedRoles={['RECEPTIONIST', 'ORG_ADMIN']}>
            <PatientsDirectoryPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/reception/appointments"
        element={
          <ProtectedRoute allowedRoles={['RECEPTIONIST', 'ORG_ADMIN']}>
            <AppointmentsPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/reception/delivery"
        element={
          <ProtectedRoute allowedRoles={['RECEPTIONIST', 'ORG_ADMIN']}>
            <ReportDeliveryPage />
          </ProtectedRoute>
        }
      />

      {/* Doctor Clinical Workspace */}
      <Route
        path="/doctor"
        element={<Navigate to="/doctor/dashboard" replace />}
      />
      <Route
        path="/doctor/dashboard"
        element={
          <ProtectedRoute allowedRoles={['DOCTOR']}>
            <DoctorDashboardPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/doctor/workspace"
        element={
          <ProtectedRoute allowedRoles={['DOCTOR']}>
            <DoctorDashboardPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/doctor/patients/:patientId"
        element={
          <ProtectedRoute allowedRoles={['DOCTOR']}>
            <PatientLongitudinalHistoryPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/doctor/consultations/:consultationId"
        element={
          <ProtectedRoute allowedRoles={['DOCTOR']}>
            <ConsultationStudioPage />
          </ProtectedRoute>
        }
      />

      {/* Upcoming Features & V2 Roadmap (All authenticated roles) */}
      <Route
        path="/upcoming"
        element={
          <ProtectedRoute allowedRoles={['PLATFORM_OWNER', 'ORG_ADMIN', 'RECEPTIONIST', 'DOCTOR']}>
            <UpcomingRoadmapPage />
          </ProtectedRoute>
        }
      />

      {/* Catch-all redirect */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
};
