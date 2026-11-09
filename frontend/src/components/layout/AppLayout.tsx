import React, { useState } from 'react';
import { NavLink, useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '@/features/auth/AuthContext';
import { getRoleHomeRoute } from '@/routes/ProtectedRoute';
import api from '@/services/api';
import {
  LayoutDashboard,
  Building2,
  CreditCard,
  ScrollText,
  Users,
  CalendarDays,
  GitBranch,
  LogOut,
  Menu,
  X,
  Stethoscope,
  Send,
  UserPlus,
  Compass,
  Clock,
} from 'lucide-react';

interface AppLayoutProps {
  children: React.ReactNode;
}

export const AppLayout: React.FC<AppLayoutProps> = ({ children }) => {
  const { user, role, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  // Define navigation items based on role
  let navItems: Array<{ label: string; to: string; icon: React.ReactNode }> = [];
  let consoleEyebrow = 'CONSOLE';
  let workspaceTitle = 'ArogyaScribe';

  if (role === 'PLATFORM_OWNER') {
    consoleEyebrow = 'PLATFORM CONSOLE';
    workspaceTitle = 'ArogyaScribe HQ';
    navItems = [
      { label: 'Overview', to: '/platform/overview', icon: <LayoutDashboard className="w-4 h-4" /> },
      { label: 'Organizations', to: '/platform/organizations', icon: <Building2 className="w-4 h-4" /> },
      { label: 'Plans & billing', to: '/platform/plans', icon: <CreditCard className="w-4 h-4" /> },
      { label: 'Audit log', to: '/platform/audit-log', icon: <ScrollText className="w-4 h-4" /> },
    ];
  } else if (role === 'ORG_ADMIN') {
    consoleEyebrow = 'ORGANIZATION CONSOLE';
    workspaceTitle = user?.full_name ? `${user.full_name}'s Clinic` : 'Clinic Admin';
    navItems = [
      { label: 'Overview', to: '/org/overview', icon: <LayoutDashboard className="w-4 h-4" /> },
      { label: 'Branches', to: '/org/branches', icon: <GitBranch className="w-4 h-4" /> },
      { label: 'Staff Roster', to: '/org/staff', icon: <Users className="w-4 h-4" /> },
      { label: 'Doctor Schedules', to: '/org/schedules', icon: <CalendarDays className="w-4 h-4" /> },
      { label: 'V2 Roadmap', to: '/upcoming', icon: <Compass className="w-4 h-4" /> },
    ];
  } else if (role === 'RECEPTIONIST') {
    consoleEyebrow = 'RECEPTION CONSOLE';
    workspaceTitle = 'Front Desk & Triage';
    navItems = [
      { label: 'Live Queue', to: '/reception/overview', icon: <Clock className="w-4 h-4" /> },
      { label: 'Patient Directory', to: '/reception/patients', icon: <Users className="w-4 h-4" /> },
      { label: 'Bookings', to: '/reception/appointments', icon: <CalendarDays className="w-4 h-4" /> },
      { label: 'Report Delivery', to: '/reception/delivery', icon: <Send className="w-4 h-4" /> },
      { label: 'V2 Roadmap', to: '/upcoming', icon: <Compass className="w-4 h-4" /> },
    ];
  } else if (role === 'DOCTOR') {
    consoleEyebrow = 'DOCTOR WORKSPACE';
    workspaceTitle = user?.full_name ? `Dr. ${user.full_name}` : 'Doctor Console';
    navItems = [
      { label: 'Consultations', to: '/doctor/dashboard', icon: <Stethoscope className="w-4 h-4" /> },
      { label: 'V2 Roadmap', to: '/upcoming', icon: <Compass className="w-4 h-4" /> },
    ];
  }

  const roleName = role ? role.replace('_', ' ') : 'Staff';

  const sidebarContent = (
    <div className="flex flex-col h-full bg-paper-2 border-r border-line">
      {/* Brand Header Block (112px high, deep forest) */}
      <div className="h-28 bg-ink px-6 flex flex-col justify-center border-b border-ink-2/60">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-md bg-accent flex items-center justify-center text-white font-bold text-base shadow-sm">
            AS
          </div>
          <div>
            <span className="font-serif font-bold text-lg text-surface tracking-tight">
              ArogyaScribe
            </span>
            <div className="text-[10px] tracking-[0.14em] uppercase font-semibold text-accent-2">
              {consoleEyebrow}
            </div>
          </div>
        </div>
        <div className="text-xs text-paper/70 font-medium mt-1 truncate">
          {workspaceTitle}
        </div>
      </div>

      {/* Navigation block */}
      <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
        {navItems.map((item) => {
          const isActive = location.pathname.startsWith(item.to);
          return (
            <NavLink
              key={item.to}
              to={item.to}
              onClick={() => setMobileMenuOpen(false)}
              className={`flex items-center gap-3 px-3.5 py-2.5 text-sm font-medium rounded-md transition-all relative ${
                isActive
                  ? 'bg-surface text-ink font-semibold shadow-sm'
                  : 'text-text-2 hover:bg-surface/60 hover:text-ink'
              }`}
            >
              {isActive && (
                <div className="absolute left-0 top-1.5 bottom-1.5 w-[3px] bg-accent rounded-r" />
              )}
              <span className={isActive ? 'text-ink' : 'text-text-2'}>{item.icon}</span>
              <span>{item.label}</span>
            </NavLink>
          );
        })}
      </nav>

      {/* Account Footer block pinned to bottom */}
      <div className="p-4 border-t border-line/60 bg-paper-2/90">
        <div className="bg-surface/80 rounded-lg p-3 border border-line/40">
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-full bg-ink-2 text-surface flex items-center justify-center text-xs font-semibold">
              {user?.email ? user.email.charAt(0).toUpperCase() : 'U'}
            </div>
            <div className="flex-1 min-w-0">
              <div className="text-xs font-semibold text-ink capitalize truncate">
                {roleName.toLowerCase()}
              </div>
              <div className="text-[11px] text-text-2 font-mono truncate" title={user?.email}>
                {user?.email}
              </div>
            </div>
          </div>
          <button
            onClick={handleLogout}
            className="mt-2.5 w-full flex items-center justify-center gap-1.5 py-1 px-2 text-xs font-medium text-text-2 hover:text-status-err hover:bg-status-rec-bg/40 rounded transition-colors"
          >
            <LogOut className="w-3.5 h-3.5" />
            <span>Sign out</span>
          </button>
        </div>
      </div>
    </div>
  );

  return (
    <div className="min-h-screen flex bg-paper text-text">
      {/* Desktop Sidebar (250px) */}
      <aside className="hidden lg:block w-[250px] shrink-0 sticky top-0 h-screen">
        {sidebarContent}
      </aside>

      {/* Mobile Drawer */}
      {mobileMenuOpen && (
        <div className="fixed inset-0 z-50 lg:hidden">
          <div
            className="fixed inset-0 bg-ink/50 backdrop-blur-sm"
            onClick={() => setMobileMenuOpen(false)}
          />
          <div className="fixed inset-y-0 left-0 w-[270px] z-50">
            {sidebarContent}
          </div>
        </div>
      )}

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0 overflow-y-auto">
        {/* Mobile Top Bar */}
        <header className="lg:hidden bg-paper-2 border-b border-line px-4 py-3 flex items-center justify-between sticky top-0 z-40">
          <button
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            className="p-1.5 rounded-md text-ink hover:bg-surface"
          >
            {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
          </button>
          <div className="font-serif font-bold text-ink">ArogyaScribe</div>
          <div className="w-8" />
        </header>

        {/* Content Body */}
        <main className="flex-1 p-6 lg:p-8 max-w-7xl w-full mx-auto">{children}</main>
      </div>
    </div>
  );
};
