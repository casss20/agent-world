import React, { useState, useEffect } from 'react';
import { Button } from '../shared/Button';
import { Calendar, Download, Filter, RefreshCw, Search, Shield, AlertTriangle, CheckCircle, X } from 'lucide-react';

const API_BASE = '/governance/v2/audit';

// Simple Card Component
function Card({ children, className = '' }) {
  return (
    <div className={`bg-white/5 border border-white/10 rounded-xl ${className}`}>
      {children}
    </div>
  );
}

function CardHeader({ children, className = '' }) {
  return <div className={`p-4 border-b border-white/10 ${className}`}>{children}</div>;
}

function CardTitle({ children, className = '' }) {
  return <h3 className={`text-lg font-semibold text-white ${className}`}>{children}</h3>;
}

function CardContent({ children, className = '' }) {
  return <div className={`p-4 ${className}`}>{children}</div>;
}

// Simple Input
function Input({ className = '', ...props }) {
  return (
    <input
      className={`px-3 py-2 bg-white/5 border border-white/10 rounded-lg text-white placeholder-white/30 focus:outline-none focus:border-cyan-500/50 ${className}`}
      {...props}
    />
  );
}

// Simple Select
function Select({ value, onChange, options, placeholder, className = '' }) {
  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className={`px-3 py-2 bg-white/5 border border-white/10 rounded-lg text-white focus:outline-none focus:border-cyan-500/50 ${className}`}
    >
      <option value="" className="bg-gray-900">{placeholder}</option>
      {options.map((opt) => (
        <option key={opt.value} value={opt.value} className="bg-gray-900">
          {opt.label}
        </option>
      ))}
    </select>
  );
}

// Simple Badge
function Badge({ children, variant = 'default' }) {
  const variants = {
    default: 'bg-white/10 text-white/80',
    success: 'bg-green-500/20 text-green-400',
    warning: 'bg-yellow-500/20 text-yellow-400',
    danger: 'bg-red-500/20 text-red-400',
    info: 'bg-cyan-500/20 text-cyan-400'
  };
  return (
    <span className={`px-2 py-0.5 rounded text-xs font-medium ${variants[variant] || variants.default}`}>
      {children}
    </span>
  );
}

// Simple Modal/Dialog
function Dialog({ open, onClose, children }) {
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80" onClick={onClose}>
      <div className="bg-gray-900 border border-white/10 rounded-2xl max-w-2xl w-full max-h-[80vh] overflow-auto" onClick={(e) => e.stopPropagation()}>
        {children}
      </div>
    </div>
  );
}

function DialogHeader({ children }) {
  return <div className="p-4 border-b border-white/10 flex items-center justify-between">{children}</div>;
}

function DialogTitle({ children }) {
  return <h3 className="text-lg font-semibold text-white">{children}</h3>;
}

export function AuditLogViewer() {
  const [logs, setLogs] = useState([]);
  const [stats, setStats] = useState(null);
  const [integrity, setIntegrity] = useState(null);
  const [loading, setLoading] = useState(false);
  const [selectedEvent, setSelectedEvent] = useState(null);
  const [detailOpen, setDetailOpen] = useState(false);
  
  const [filters, setFilters] = useState({
    actor_type: '',
    actor_role: '',
    action: '',
    decision: '',
    start_date: '',
    end_date: '',
    request_id: '',
    search: ''
  });

  // Mock data for demo
  const mockLogs = [
    {
      event_id: 'evt_001',
      actor_type: 'user',
      actor_role: 'governor',
      action: 'approve',
      resource: 'strategy_recommendation',
      decision: 'approved',
      timestamp: '2025-04-16T10:30:00Z',
      context: { strategy_id: 'str_123', business_id: 'biz_456' },
      hash: 'a1b2c3d4',
      prev_hash: '00000000'
    },
    {
      event_id: 'evt_002',
      actor_type: 'agent',
      actor_role: 'nova',
      action: 'execute',
      resource: 'trend_research',
      decision: 'completed',
      timestamp: '2025-04-16T09:15:00Z',
      context: { query: 'productivity planners', results_count: 15 },
      hash: 'e5f6g7h8',
      prev_hash: 'a1b2c3d4'
    },
    {
      event_id: 'evt_003',
      actor_type: 'user',
      actor_role: 'operator',
      action: 'modify',
      resource: 'ad_campaign',
      decision: 'approved',
      timestamp: '2025-04-16T08:45:00Z',
      context: { campaign_id: 'camp_789', changes: ['budget', 'targeting'] },
      hash: 'i9j0k1l2',
      prev_hash: 'e5f6g7h8'
    }
  ];

  const mockStats = {
    total_events: 3,
    events_by_action: { approve: 2, execute: 1, modify: 1 },
    events_by_decision: { approved: 3, rejected: 0, pending: 0 },
    chain_valid: true
  };

  const fetchLogs = async () => {
    setLoading(true);
    // TODO: Replace with actual API call
    await new Promise(r => setTimeout(r, 500));
    setLogs(mockLogs);
    setStats(mockStats);
    setLoading(false);
  };

  const fetchIntegrity = async () => {
    // TODO: Replace with actual API call
    setIntegrity({ valid: true, chain_hash: 'abc123...' });
  };

  const exportLogs = () => {
    const dataStr = JSON.stringify(logs, null, 2);
    const dataBlob = new Blob([dataStr], { type: 'application/json' });
    const url = URL.createObjectURL(dataBlob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `audit-logs-${new Date().toISOString().split('T')[0]}.json`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  useEffect(() => {
    fetchLogs();
    fetchIntegrity();
  }, []);

  const filteredLogs = logs.filter(log => {
    const matchesSearch = !filters.search || 
      log.event_id.includes(filters.search) ||
      log.action.includes(filters.search) ||
      log.actor_role.includes(filters.search);
    
    const matchesFilters = 
      (!filters.actor_type || log.actor_type === filters.actor_type) &&
      (!filters.actor_role || log.actor_role === filters.actor_role) &&
      (!filters.action || log.action === filters.action) &&
      (!filters.decision || log.decision === filters.decision);
    
    return matchesSearch && matchesFilters;
  });

  const viewEventDetail = (event) => {
    setSelectedEvent(event);
    setDetailOpen(true);
  };

  const actionOptions = [
    { value: 'approve', label: 'Approve' },
    { value: 'reject', label: 'Reject' },
    { value: 'modify', label: 'Modify' },
    { value: 'execute', label: 'Execute' },
    { value: 'create', label: 'Create' },
    { value: 'delete', label: 'Delete' }
  ];

  const decisionOptions = [
    { value: 'approved', label: 'Approved' },
    { value: 'rejected', label: 'Rejected' },
    { value: 'pending', label: 'Pending' },
    { value: 'completed', label: 'Completed' },
    { value: 'failed', label: 'Failed' }
  ];

  const actorTypeOptions = [
    { value: 'user', label: 'User' },
    { value: 'agent', label: 'Agent' },
    { value: 'system', label: 'System' }
  ];

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2">
            <Shield className="w-6 h-6 text-cyan-400" />
            Audit Log Viewer
          </h1>
          <p className="text-white/50 mt-1">Immutable audit trail with hash verification</p>
        </div>
        
        <div className="flex gap-2">
          <Button variant="secondary" onClick={fetchLogs} loading={loading}>
            <RefreshCw className="w-4 h-4 mr-2" />
            Refresh
          </Button>
          <Button variant="secondary" onClick={exportLogs}>
            <Download className="w-4 h-4 mr-2" />
            Export
          </Button>
        </div>
      </div>

      {/* Stats */}
      {stats && (
        <div className="grid grid-cols-4 gap-4">
          <Card>
            <CardContent className="p-4">
              <div className="text-2xl font-bold text-white">{stats.total_events}</div>
              <div className="text-sm text-white/50">Total Events</div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4">
              <div className="text-2xl font-bold text-green-400">{stats.events_by_decision?.approved || 0}</div>
              <div className="text-sm text-white/50">Approved</div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4">
              <div className="text-2xl font-bold text-yellow-400">{stats.events_by_decision?.pending || 0}</div>
              <div className="text-sm text-white/50">Pending</div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4">
              <div className="flex items-center gap-2">
                <div className="text-2xl font-bold text-cyan-400">
                  {integrity?.valid !== false ? <CheckCircle className="w-6 h-6" /> : <AlertTriangle className="w-6 h-6" />}
                </div>
                <div className="text-sm text-white/50">
                  {integrity?.valid !== false ? 'Chain Valid' : 'Chain Invalid'}
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Filters */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Filter className="w-4 h-4" />
            Filters
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <Select
              value={filters.actor_type}
              onChange={(val) => setFilters({ ...filters, actor_type: val })}
              options={actorTypeOptions}
              placeholder="Actor Type"
            />
            <Select
              value={filters.action}
              onChange={(val) => setFilters({ ...filters, action: val })}
              options={actionOptions}
              placeholder="Action"
            />
            <Select
              value={filters.decision}
              onChange={(val) => setFilters({ ...filters, decision: val })}
              options={decisionOptions}
              placeholder="Decision"
            />
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-white/30" />
              <Input
                placeholder="Search..."
                value={filters.search}
                onChange={(e) => setFilters({ ...filters, search: e.target.value })}
                className="pl-9"
              />
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Logs Table */}
      <Card>
        <CardHeader>
          <CardTitle>Audit Events</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-white/10">
                  <th className="text-left py-3 px-4 text-sm font-medium text-white/50">Event ID</th>
                  <th className="text-left py-3 px-4 text-sm font-medium text-white/50">Timestamp</th>
                  <th className="text-left py-3 px-4 text-sm font-medium text-white/50">Actor</th>
                  <th className="text-left py-3 px-4 text-sm font-medium text-white/50">Action</th>
                  <th className="text-left py-3 px-4 text-sm font-medium text-white/50">Decision</th>
                  <th className="text-left py-3 px-4 text-sm font-medium text-white/50">Resource</th>
                </tr>
              </thead>
              <tbody>
                {filteredLogs.map((log) => (
                  <tr
                    key={log.event_id}
                    className="border-b border-white/5 hover:bg-white/5 cursor-pointer transition-colors"
                    onClick={() => viewEventDetail(log)}
                  >
                    <td className="py-3 px-4 text-sm font-mono text-white/80">{log.event_id}</td>
                    <td className="py-3 px-4 text-sm text-white/60">
                      {new Date(log.timestamp).toLocaleString()}
                    </td>
                    <td className="py-3 px-4">
                      <div className="flex items-center gap-2">
                        <Badge variant={log.actor_type === 'user' ? 'info' : 'default'}>
                          {log.actor_type}
                        </Badge>
                        <span className="text-sm text-white/70">{log.actor_role}</span>
                      </div>
                    </td>
                    <td className="py-3 px-4 text-sm text-white/80 capitalize">{log.action}</td>
                    <td className="py-3 px-4">
                      <Badge 
                        variant={
                          log.decision === 'approved' ? 'success' :
                          log.decision === 'rejected' ? 'danger' :
                          log.decision === 'pending' ? 'warning' :
                          'default'
                        }
                      >
                        {log.decision}
                      </Badge>
                    </td>
                    <td className="py-3 px-4 text-sm text-white/60">{log.resource}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          
          {filteredLogs.length === 0 && (
            <div className="text-center py-8 text-white/50">
              No audit events found matching your filters
            </div>
          )}
        </CardContent>
      </Card>

      {/* Event Detail Dialog */}
      <Dialog open={detailOpen} onClose={() => setDetailOpen(false)}>
        <DialogHeader>
          <DialogTitle>Event Details</DialogTitle>
          <button onClick={() => setDetailOpen(false)} className="text-white/50 hover:text-white">
            <X className="w-5 h-5" />
          </button>
        </DialogHeader>
        <div className="p-4 space-y-4">
          {selectedEvent && (
            <>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-xs text-white/50 uppercase">Event ID</label>
                  <p className="text-sm font-mono text-white">{selectedEvent.event_id}</p>
                </div>
                <div>
                  <label className="text-xs text-white/50 uppercase">Timestamp</label>
                  <p className="text-sm text-white">{new Date(selectedEvent.timestamp).toLocaleString()}</p>
                </div>
                <div>
                  <label className="text-xs text-white/50 uppercase">Actor</label>
                  <p className="text-sm text-white">{selectedEvent.actor_type} / {selectedEvent.actor_role}</p>
                </div>
                <div>
                  <label className="text-xs text-white/50 uppercase">Action</label>
                  <p className="text-sm text-white capitalize">{selectedEvent.action}</p>
                </div>
                <div>
                  <label className="text-xs text-white/50 uppercase">Decision</label>
                  <p className="text-sm text-white">{selectedEvent.decision}</p>
                </div>
                <div>
                  <label className="text-xs text-white/50 uppercase">Resource</label>
                  <p className="text-sm text-white">{selectedEvent.resource}</p>
                </div>
              </div>
              
              <div>
                <label className="text-xs text-white/50 uppercase">Context</label>
                <pre className="mt-1 p-3 bg-black/30 rounded-lg text-sm text-white/80 overflow-auto">
                  {JSON.stringify(selectedEvent.context, null, 2)}
                </pre>
              </div>
              
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-xs text-white/50 uppercase">Hash</label>
                  <p className="text-sm font-mono text-white/70">{selectedEvent.hash}</p>
                </div>
                <div>
                  <label className="text-xs text-white/50 uppercase">Previous Hash</label>
                  <p className="text-sm font-mono text-white/70">{selectedEvent.prev_hash}</p>
                </div>
              </div>
            </>
          )}
        </div>
      </Dialog>
    </div>
  );
}
