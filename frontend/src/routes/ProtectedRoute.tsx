import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '@/features/auth/AuthContext';
import { UserRole } from '@/types';

interface ProtectedRouteProps {
  children: React.ReactNode;
  allowedRoles?: UserRole[];
}

export const getRoleHomeRoute = (role?: UserRole | null): string => {
  switch (role) {
    case 'PLATFORM_OWNER':
      return '/platform/overview';
    case 'ORG_ADMIN':
      return '/org/overview';
    case 'RECEPTIONIST':
      return '/reception/overview';
    case 'DOCTOR':
      return '/doctor/dashboard';
    default:
      return '/login';
  }
};

export const ProtectedRoute: React.FC<ProtectedRouteProps> = ({ children, allowedRoles }) => {
  const { user, role, isAuthenticated, isLoading } = useAuth();
  const location = useLocation();

  if (isLoading) {
    return (
      <div className="min-h-screen bg-paper flex flex-col items-center justify-center">
        <div className="w-10 h-10 border-4 border-ink/20 border-t-accent rounded-full animate-spin mb-4" />
        <p className="text-sm font-medium text-text-2">Loading session...</p>
      </div>
    );
  }

  if (!isAuthenticated || !user) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  if (allowedRoles && role && !allowedRoles.includes(role)) {
    return <Navigate to={getRoleHomeRoute(role)} replace />;
  }

  return <>{children}</>;
};

