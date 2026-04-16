import React, { useState, useEffect, useCallback } from 'react';
import { useApi } from '../../hooks/useApi';

const EVENT_ICONS = {
  'workflow.launched': '🚀',
  'workflow.completed': '✓',
  'workflow.failed': '✕',
  'agent.invoked': '🤖',
  'agent.completed': '✓',
  'tool.called': '🔧',
  'revenue.recorded': '💰',
  'approval.requested': '⏸️',
  'approval.granted': '✓',
  'approval.denied': '✕',
  'token.issued': '🎫',
  'constitution.violation': '⚠️',
};

const EVENT_COLORS = {
  'workflow.launched': 'text-cyan-400',
  'workflow.completed': 'text-green-400',
  'workflow.failed': 'text-red-400',
  'agent.invoked': 'text-blue-400',
  'agent.completed': 'text-green-400',
  'tool.called': 'text-yellow-400',
  'revenue.recorded': 'text-green-400',
  'approval.requested': 'text-yellow-400',
  'approval.granted': 'text-green-400',
  'approval.denied': 'text-red-400',
  'token.issued': 'text-purple-400',
  'constitution.violation': 'text-red-400',
};

export function LedgerAuditTrail({ businessId, roomId, limit = 50 }) {
  const { get, loading } = useApi();
  const [events, setEvents] = useState([]);
  const [filter, setFilter] = useState('all');
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedEvent, setSelectedEvent] = useState(null);

  const loadAuditTrail = useCallback(async () => {
    const params = new URLSearchParams();
    if (businessId) params.append('business_id', businessId);
    if (roomId) params.append('room_id', roomId);
    if (filter !== 'all') params.append('event_type', filter);
    params.append('limit', limit.toString());

    const data = await get(`/governance/v2/audit/logs?${params.toString()}`);
    if (data) {
      setEvents(data.events || []);
    }
  }, [get, businessId, roomId, filter, limit]);

  useEffect(() => {
    loadAuditTrail();
    // Real-time updates via WebSocket could be added here
    const interval = setInterval(loadAuditTrail, 30000); // Poll every 30s
    return () => clearInterval(interval);
  }, [loadAuditTrail]);

  const filteredEvents = events.filter(event => {
    if (!searchTerm) return true;
    const search = searchTerm.toLowerCase();
    return (
      event.event_type?.toLowerCase().includes(search) ||
      event.agent_id?.toLowerCase().includes(search) ||
      event.step_name?.toLowerCase().includes(search) ||
      JSON.stringify(event.payload).toLowerCase().includes(search)
    );
  });

  const eventTypes = [...new Set(events.map(e => e.event_type))];

  if (loading && events.length === 0) {
    return (
      <div className="p-6 text-center">
        <div className="animate-spin w-8 h-8 border-4 border-cyan-400 border-t-transparent rounded-full mx-auto mb-4" />
        <p className="text-white/50">Loading audit trail...</p>
      </div>
    );
  }

  return (
    <div className="ledger-audit-trail">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-4">
        <div>
          <h2 className="text-xl font-bold text-white flex items-center gap-2">
            📊 Audit Trail
            <span className="text-sm font-normal text-white/50">
              ({events.length} events)
            </span>
          </h2>
          <p className="text-sm text-white/50">
            Immutable log of all agent actions and governance decisions
          </p>
        </div>

        <div className="flex gap-2">
          <input
            type="text"
            placeholder="Search events..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="px-3 py-2 bg-white/5 border border-white/10 rounded-lg text-sm text-white placeholder-white/30 focus:border-cyan-500/50 focus:outline-none"
          />
          
          <select
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            className="px-3 py-2 bg-white/5 border border-white/10 rounded-lg text-sm text-white focus:border-cyan-500/50 focus:outline-none"
          >
            <option value="all">All Types</option>
            {eventTypes.map(type => (
              <option key={type} value={type}>{type}</option>
            ))}
          </select>

          <button
            onClick={loadAuditTrail}
            className="px-3 py-2 bg-cyan-500/20 border border-cyan-500/30 rounded-lg text-cyan-400 text-sm hover:bg-cyan-500/30"
          >
            ↻
          </button>
        </div>
      </div>

      {/* Timeline */}
      <div className="space-y-2 max-h-[600px] overflow-y-auto pr-2">
        {filteredEvents.length === 0 ? (
          <div className="p-8 text-center bg-white/5 rounded-xl border border-white/10">
            <div className="text-4xl mb-3">📭</div>
            <p className="text-white/70">No audit events found</p>
            <p className="text-sm text-white/40 mt-1">
              {searchTerm ? "Try adjusting your search" : "Events will appear as agents take actions"}
            </p>
          </div>
        ) : (
          filteredEvents.map((event, index) => (
            <AuditEventRow
              key={event.event_id || index}
              event={event}
              isSelected={selectedEvent?.event_id === event.event_id}
              onClick={() => setSelectedEvent(selectedEvent?.event_id === event.event_id ? null : event)}
            />
          ))
        )}
      </div>

      {/* Selected Event Detail */}
      {selectedEvent && (
        <EventDetailPanel event={selectedEvent} onClose={() => setSelectedEvent(null)} />
      )}
    </div>
  );
}

function AuditEventRow({ event, isSelected, onClick }) {
  const icon = EVENT_ICONS[event.event_type] || '•';
  const colorClass = EVENT_COLORS[event.event_type] || 'text-white/60';
  const timestamp = new Date(event.timestamp);

  return (
    <div
      onClick={onClick}
      className={`p-3 rounded-lg border cursor-pointer transition-all ${
        isSelected
          ? 'bg-cyan-500/10 border-cyan-500/50'
          : 'bg-white/5 border-white/10 hover:border-white/30'
      }`}
    >
      <div className="flex items-start gap-3">
        <div className={`text-lg ${colorClass}`}>{icon}</div>
        
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className={`font-medium ${colorClass}`}>
              {event.event_type}
            </span>
            <span className="text-white/30">|</span>
            <span className="text-sm text-white/60">
              {event.agent_id?.slice(0, 12) || 'System'}
            </span>
            {event.step_name && (
              <>
                <span className="text-white/30">→</span>
                <span className="text-sm text-white/50">{event.step_name}</span>
              </>
            )}
          </div>
          
          <div className="flex items-center gap-4 mt-1 text-xs text-white/40">
            <span>{timestamp.toLocaleTimeString()}</span>
            <span>{timestamp.toLocaleDateString()}</span>
            <span>•</span>
            <span className="font-mono text-white/30">{event.event_id?.slice(0, 8)}</span>
            {event.correlation_id && (
              <>
                <span>•</span>
                <span className="font-mono text-white/30">corr:{event.correlation_id?.slice(0, 6)}</span>
              </>
            )}
          </div>
        </div>

        <div className="text-white/30 text-sm">
          {isSelected ? '▲' : '▼'}
        </div>
      </div>
    </div>
  );
}

function EventDetailPanel({ event, onClose }) {
  return (
    <div className="mt-4 p-4 bg-black/50 rounded-xl border border-cyan-500/30">
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-semibold text-white flex items-center gap-2">
          {EVENT_ICONS[event.event_type] || '•'}
          <span>Event Details</span>
        </h3>
        <button onClick={onClose} className="text-white/50 hover:text-white">✕</button>
      </div>

      <div className="space-y-3 text-sm">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <span className="text-white/40 block text-xs">Event ID</span>
            <span className="font-mono text-white/80">{event.event_id}</span>
          </div>
          <div>
            <span className="text-white/40 block text-xs">Correlation ID</span>
            <span className="font-mono text-white/80">{event.correlation_id}</span>
          </div>
          <div>
            <span className="text-white/40 block text-xs">Timestamp</span>
            <span className="text-white/80">{new Date(event.timestamp).toLocaleString()}</span>
          </div>
          <div>
            <span className="text-white/40 block text-xs">Agent</span>
            <span className="text-white/80">{event.agent_id || 'System'}</span>
          </div>
          <div>
            <span className="text-white/40 block text-xs">Room</span>
            <span className="font-mono text-white/80">{event.room_id?.slice(0, 12)}</span>
          </div>
          <div>
            <span className="text-white/40 block text-xs">User</span>
            <span className="text-white/80">{event.user_id}</span>
          </div>
        </div>

        <div>
          <span className="text-white/40 block text-xs mb-1">Payload</span>
          <pre className="p-3 bg-black/50 rounded-lg text-xs text-white/60 overflow-x-auto">
            {JSON.stringify(event.payload, null, 2)}
          </pre>
        </div>

        {event.metadata && Object.keys(event.metadata).length > 0 && (
          <div>
            <span className="text-white/40 block text-xs mb-1">Metadata</span>
            <pre className="p-3 bg-black/50 rounded-lg text-xs text-white/60 overflow-x-auto">
              {JSON.stringify(event.metadata, null, 2)}
            </pre>
          </div>
        )}

        {/* Governance-specific fields */}
        {(event.metadata?.constitution_check || event.metadata?.risk_level) && (
          <div className="p-3 bg-yellow-500/10 rounded-lg border border-yellow-500/20">
            <span className="text-yellow-400 text-xs font-medium block mb-2">Governance Data</span>
            {event.metadata?.risk_level && (
              <div className="flex items-center gap-2 text-sm">
                <span className="text-white/50">Risk Level:</span>
                <span className={`font-medium ${
                  event.metadata.risk_level === 'critical' ? 'text-red-400' :
                  event.metadata.risk_level === 'medium' ? 'text-yellow-400' :
                  'text-green-400'
                }`}>
                  {event.metadata.risk_level.toUpperCase()}
                </span>
              </div>
            )}
            {event.metadata?.constitution_check && (
              <div className="flex items-center gap-2 text-sm mt-1">
                <span className="text-white/50">Constitution:</span>
                <span className={event.metadata.constitution_check.passed ? 'text-green-400' : 'text-red-400'}>
                  {event.metadata.constitution_check.passed ? '✓ Passed' : '✕ Violation'}
                </span>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
