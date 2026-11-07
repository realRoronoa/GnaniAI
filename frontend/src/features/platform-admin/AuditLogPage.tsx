import React, { useEffect, useState } from 'react';
import { AppLayout } from '@/components/layout/AppLayout';
import { DataTable, Column } from '@/components/common/DataTable';
import { StatusBadge } from '@/components/common/StatusBadge';
import api from '@/services/api';
import { AuditEvent } from '@/types';
import { Search, ShieldAlert } from 'lucide-react';

export const AuditLogPage: React.FC = () => {
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [isLoading, setIsLoading] = useState(true);

  const fetchAuditEvents = async () => {
    setIsLoading(true);
    try {
      const response = await api.get('/platform/audit-events');
      setEvents(Array.isArray(response.data) ? response.data : []);
    } catch (err) {
      console.error('Failed to fetch audit events:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchAuditEvents();
  }, []);

  const filteredEvents = events.filter(
    (ev) =>
      ev.action?.toLowerCase().includes(searchQuery.toLowerCase()) ||
      ev.resource_type?.toLowerCase().includes(searchQuery.toLowerCase()) ||
      ev.actor_role?.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const columns: Column<AuditEvent>[] = [
    {
      header: 'Timestamp',
      render: (ev) => (
        <span className="text-xs font-mono text-text-2">
          {new Date(ev.created_at).toLocaleString('en-IN', {
            day: '2-digit',
            month: 'short',
            year: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit',
          })}
        </span>
      ),
    },
    {
      header: 'Action',
      render: (ev) => (
        <span className="font-semibold text-xs text-ink font-mono uppercase bg-surface-2 px-2 py-0.5 rounded">
          {ev.action}
        </span>
      ),
    },
    {
      header: 'Actor Role',
      render: (ev) => (
        <span className="text-xs font-medium text-text-2">
          {ev.actor_role || 'SYSTEM'}
        </span>
      ),
    },
    {
      header: 'Resource',
      render: (ev) => (
        <div className="text-xs">
          <span className="font-medium text-ink">{ev.resource_type}</span>
          {ev.resource_id && (
            <span className="text-text-2 font-mono text-[11px] block truncate max-w-[140px]">
              {ev.resource_id}
            </span>
          )}
        </div>
      ),
    },
    {
      header: 'Client IP',
      render: (ev) => (
        <span className="text-xs font-mono text-text-2">
          {ev.ip_address || '127.0.0.1'}
        </span>
      ),
    },
  ];

  return (
    <AppLayout>
      <div className="space-y-6">
        {/* Header */}
        <div>
          <div className="text-xs font-semibold uppercase tracking-[0.14em] text-accent mb-1">
            PLATFORM CONSOLE
          </div>
          <h1 className="font-serif text-3xl font-bold text-ink">Audit Log</h1>
          <p className="text-sm text-text-2 mt-1">
            Immutable log of administrative, authentication, and clinical state transitions.
          </p>
        </div>

        {/* Privacy notice banner */}
        <div className="p-3 bg-surface border border-line rounded-lg flex items-center gap-2 text-xs text-text-2">
          <ShieldAlert className="w-4 h-4 text-accent shrink-0" />
          <span>
            Audit events contain security and operational metadata only. Clinical transcripts and patient
            identifiers are strictly excluded from Platform Owner views.
          </span>
        </div>

        {/* Search */}
        <div className="bg-surface border border-line rounded-lg p-3 flex items-center gap-2 shadow-card">
          <Search className="w-4 h-4 text-text-2" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Filter by action (e.g., ORG_ONBOARDED, DOCTOR_APPROVAL), role, or resource..."
            className="flex-1 bg-transparent text-sm text-ink placeholder:text-text-2/60 focus:outline-none"
          />
        </div>

        {/* Audit Table */}
        <DataTable
          columns={columns}
          data={filteredEvents}
          isLoading={isLoading}
          emptyMessage="No audit events found."
        />
      </div>
    </AppLayout>
  );
};

