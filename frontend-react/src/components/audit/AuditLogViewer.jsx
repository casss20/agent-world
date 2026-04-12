import React, { useState, useEffect } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Calendar, Download, Filter, RefreshCw, Search, Shield, AlertTriangle, CheckCircle } from 'lucide-react';

const API_BASE = '/governance/v2/audit';

export default function AuditLogViewer() {
  const [logs, setLogs] = useState([]);
  const [stats, setStats] = useState(null);
  const [integrity, setIntegrity] = useState(null);
  const [loading, setLoading] = useState(false);
  const [selectedEvent, setSelectedEvent] = useState(null);
  const [detailOpen, setDetailOpen] = useState(false);
  const [viewMode, setViewMode] = useState('table'); // 'table' | 'timeline'
  
  const [filters, setFilters] = useState({
    actor_type: '',
    actor_role: '',
    action: '',
    decision: '',
    start_date: '',
    end_date: '',
    request_id: '',
    limit: 100
  });
  const [actions, setActions] = useState([]);

  const fetchLogs = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      Object.entries(filters).forEach(([key, value]) => {
        if (value) params.append(key, value);
      });
      
      const response = await fetch(`${API_BASE}/logs?${params}`);
      if (response.ok) {
        const data = await response.json();
        setLogs(data);
      }
    } catch (error) {
      console.error('Failed to fetch logs:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchStats = async () => {
    try {
      const response = await fetch(`${API_BASE}/stats?days=7`);
      if (response.ok) {
        const data = await response.json();
        setStats(data);
      }
    } catch (error) {
      console.error('Failed to fetch stats:', error);
    }
  };

  const fetchIntegrity = async () => {
    try {
      const response = await fetch(`${API_BASE}/integrity`);
      if (response.ok) {
        const data = await response.json();
        setIntegrity(data);
      }
    } catch (error) {
      console.error('Failed to fetch integrity:', error);
    }
  };

  const fetchActions = async () => {
    try {
      const response = await fetch(`${API_BASE}/actions`);
      if (response.ok) {
        const data = await response.json();
        setActions(data.actions);
      }
    } catch (error) {
      console.error('Failed to fetch actions:', error);
    }
  };

  const exportLogs = async (format) => {
    try {
      const params = new URLSearchParams();
      Object.entries(filters).forEach(([key, value]) => {
        if (value && key !== 'limit') params.append(key, value);
      });
      
      const response = await fetch(`${API_BASE}/export/${format}?${params}`);
      if (response.ok) {
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `audit_logs_${new Date().toISOString().split('T')[0]}.${format}`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
      }
    } catch (error) {
      console.error('Failed to export logs:', error);
    }
  };

  const viewEventDetail = (event) => {
    setSelectedEvent(event);
    setDetailOpen(true);
  };

  useEffect(() => {
    fetchLogs();
    fetchStats();
    fetchActions();
    fetchIntegrity();
  }, []);

  const getDecisionBadge = (decision) => {
    const styles = {
      allowed: 'bg-green-100 text-green-800 border-green-300',
      denied: 'bg-yellow-100 text-yellow-800 border-yellow-300',
      error: 'bg-red-100 text-red-800 border-red-300',
      timeout: 'bg-gray-100 text-gray-800 border-gray-300'
    };
    return <Badge variant="outline" className={styles[decision] || ''}>{decision}</Badge>;
  };

  const getActorBadge = (type) => {
    const styles = {
      user: 'bg-blue-100 text-blue-800',
      agent: 'bg-purple-100 text-purple-800',
      system: 'bg-gray-100 text-gray-800'
    };
    return <Badge className={styles[type] || ''}>{type}</Badge>;
  };

  const getSeverityIcon = (decision) => {
    if (decision === 'error') return <AlertTriangle className="w-4 h-4 text-red-500" />;
    if (decision === 'denied') return <AlertTriangle className="w-4 h-4 text-yellow-500" />;
    return <CheckCircle className="w-4 h-4 text-green-500" />;
  };

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold flex items-center gap-2">
            <Shield className="w-8 h-8 text-blue-600" />
            Audit Log Viewer
          </h1>
          <p className="text-muted-foreground">
            Immutable audit trail with integrity verification
          </p>
        </div>
        <div className="flex gap-2">
          <Button 
            variant={viewMode === 'table' ? 'default' : 'outline'} 
            onClick={() => setViewMode('table')}
          >
            Table
          </Button>
          <Button 
            variant={viewMode === 'timeline' ? 'default' : 'outline'} 
            onClick={() => setViewMode('timeline')}
          >
            Timeline
          </Button>
          <Button variant="outline" onClick={() => exportLogs('json')}>
            <Download className="w-4 h-4 mr-2" />
            JSON
          </Button>
          <Button variant="outline" onClick={() => exportLogs('csv')}>
            <Download className="w-4 h-4 mr-2" />
            CSV
          </Button>
        </div>
      </div>

      {/* Stats & Integrity Cards */}
      <div className="grid grid-cols-5 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Total Events (7d)</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats?.total_entries?.toLocaleString() || 0}</div>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Allowed Rate</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">
              {stats?.decision_breakdown?.allowed 
                ? Math.round((stats.decision_breakdown.allowed / stats.total_entries) * 100)
                : 0}%
            </div>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Denied/Failed</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-red-600">
              {(stats?.decision_breakdown?.denied || 0) + (stats?.decision_breakdown?.error || 0)}
            </div>
          </CardContent>
        </Card>
        
        <Card className={integrity?.chain_intact ? 'border-green-300' : 'border-red-300'}>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              <Shield className="w-4 h-4" />
              Chain Integrity
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className={`text-lg font-bold ${integrity?.chain_intact ? 'text-green-600' : 'text-red-600'}`}>
              {integrity?.chain_intact ? 'VERIFIED' : 'FAILED'}
            </div>
            <div className="text-xs text-muted-foreground">
              {integrity?.verified_events || 0} / {integrity?.total_events || 0} events
            </div>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Last Event</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-xs font-mono text-muted-foreground truncate">
              {integrity?.last_event_id 
                ? `${integrity.last_event_id.substring(0, 16)}...` 
                : 'N/A'}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Filters */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Filter className="w-4 h-4" />
            Filters
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-8 gap-4">
            <div>
              <label className="text-sm font-medium mb-2 block">Actor Type</label>
              <Select 
                value={filters.actor_type} 
                onValueChange={(v) => setFilters({...filters, actor_type: v})}
              >
                <SelectTrigger><SelectValue placeholder="All" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="">All</SelectItem>
                  <SelectItem value="user">User</SelectItem>
                  <SelectItem value="agent">Agent</SelectItem>
                  <SelectItem value="system">System</SelectItem>
                </SelectContent>
              </Select>
            </div>
            
            <div>
              <label className="text-sm font-medium mb-2 block">Actor Role</label>
              <Input 
                placeholder="e.g., admin"
                value={filters.actor_role}
                onChange={(e) => setFilters({...filters, actor_role: e.target.value})}
              />
            </div>
            
            <div>
              <label className="text-sm font-medium mb-2 block">Action</label>
              <Select 
                value={filters.action} 
                onValueChange={(v) => setFilters({...filters, action: v})}
              >
                <SelectTrigger><SelectValue placeholder="All" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="">All</SelectItem>
                  {actions.map(action => (
                    <SelectItem key={action} value={action}>{action}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            
            <div>
              <label className="text-sm font-medium mb-2 block">Decision</label>
              <Select 
                value={filters.decision} 
                onValueChange={(v) => setFilters({...filters, decision: v})}
              >
                <SelectTrigger><SelectValue placeholder="All" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="">All</SelectItem>
                  <SelectItem value="allowed">Allowed</SelectItem>
                  <SelectItem value="denied">Denied</SelectItem>
                  <SelectItem value="error">Error</SelectItem>
                  <SelectItem value="timeout">Timeout</SelectItem>
                </SelectContent>
              </Select>
            </div>
            
            <div>
              <label className="text-sm font-medium mb-2 block">Start Date</label>
              <Input 
                type="date" 
                value={filters.start_date}
                onChange={(e) => setFilters({...filters, start_date: e.target.value})}
              />
            </div>
            
            <div>
              <label className="text-sm font-medium mb-2 block">End Date</label>
              <Input 
                type="date" 
                value={filters.end_date}
                onChange={(e) => setFilters({...filters, end_date: e.target.value})}
              />
            </div>
            
            <div>
              <label className="text-sm font-medium mb-2 block">Request ID</label>
              <Input 
                placeholder="Filter by request..."
                value={filters.request_id}
                onChange={(e) => setFilters({...filters, request_id: e.target.value})}
              />
            </div>
            
            <div className="flex items-end">
              <Button onClick={fetchLogs} disabled={loading} className="w-full">
                <RefreshCw className={`w-4 h-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
                Apply
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Table View */}
      {viewMode === 'table' && (
        <Card>
          <CardHeader>
            <CardTitle>Audit Events ({logs.length} shown)</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="border rounded-md">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-10"></TableHead>
                    <TableHead>Timestamp</TableHead>
                    <TableHead>Actor</TableHead>
                    <TableHead>Action</TableHead>
                    <TableHead>Resource</TableHead>
                    <TableHead>Decision</TableHead>
                    <TableHead>Request ID</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {logs.map((log) => (
                    <TableRow 
                      key={log.event_id}
                      className="cursor-pointer hover:bg-muted/50"
                      onClick={() => viewEventDetail(log)}
                    >
                      <TableCell>{getSeverityIcon(log.decision)}</TableCell>
                      <TableCell className="font-mono text-xs">
                        {new Date(log.created_at).toLocaleString()}
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center gap-2">
                          {getActorBadge(log.actor_type)}
                          <span className="text-sm truncate max-w-[100px]" title={log.actor_id}>
                            {log.actor_id}
                          </span>
                        </div>
                      </TableCell>
                      <TableCell>
                        <Badge variant="outline" className="font-mono text-xs">{log.action}</Badge>
                      </TableCell>
                      <TableCell>
                        <span className="text-sm text-muted-foreground">
                          {log.resource_type}:{log.resource_id || '-'}
                        </span>
                      </TableCell>
                      <TableCell>{getDecisionBadge(log.decision)}</TableCell>
                      <TableCell className="font-mono text-xs">
                        {log.request_id?.substring(0, 8) || '-'}...
                      </TableCell>
                    </TableRow>
                  ))}
                  {logs.length === 0 && (
                    <TableRow>
                      <TableCell colSpan={7} className="text-center text-muted-foreground py-8">
                        No audit events found
                      </TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Timeline View */}
      {viewMode === 'timeline' && (
        <Card>
          <CardHeader>
            <CardTitle>Timeline View</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {logs.map((log, index) => (
                <div 
                  key={log.event_id}
                  className="flex gap-4 p-4 border rounded-lg hover:bg-muted/50 cursor-pointer"
                  onClick={() => viewEventDetail(log)}
                >
                  <div className="flex flex-col items-center">
                    {getSeverityIcon(log.decision)}
                    {index < logs.length - 1 && (
                      <div className="w-px h-full bg-border mt-2" />
                    )}
                  </div>
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="font-mono text-xs text-muted-foreground">
                        {new Date(log.created_at).toLocaleString()}
                      </span>
                      {getActorBadge(log.actor_type)}
                      {getDecisionBadge(log.decision)}
                    </div>
                    <div className="font-medium">
                      {log.action}
                    </div>
                    <div className="text-sm text-muted-foreground">
                      {log.actor_id} → {log.resource_type}:{log.resource_id || '-'}
                    </div>
                    <div className="text-xs font-mono text-muted-foreground mt-1">
                      req: {log.request_id?.substring(0, 16) || 'N/A'}...
                    </div>
                  </div>
                </div>
              ))}
              {logs.length === 0 && (
                <div className="text-center text-muted-foreground py-8">
                  No audit events found
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Event Detail Dialog */}
      <Dialog open={detailOpen} onOpenChange={setDetailOpen}>
        <DialogContent className="max-w-3xl max-h-[80vh]">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              Event Details
              {selectedEvent && getDecisionBadge(selectedEvent.decision)}
            </DialogTitle>
          </DialogHeader>
          
          {selectedEvent && (
            <ScrollArea className="h-[60vh]">
              <div className="space-y-6">
                {/* Event Identity */}
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="text-sm font-medium text-muted-foreground">Event ID</label>
                    <div className="font-mono text-sm">{selectedEvent.event_id}</div>
                  </div>
                  <div>
                    <label className="text-sm font-medium text-muted-foreground">Timestamp</label>
                    <div>{new Date(selectedEvent.created_at).toLocaleString()}</div>
                  </div>
                  
                  <div>
                    <label className="text-sm font-medium text-muted-foreground">Request ID</label>
                    <div className="font-mono text-sm">{selectedEvent.request_id || 'N/A'}</div>
                  </div>
                  
                  <div>
                    <label className="text-sm font-medium text-muted-foreground">Business ID</label>
                    <div>{selectedEvent.business_id || 'N/A'}</div>
                  </div>
                </div>
                
                {/* Actor */}
                <div className="border rounded-lg p-4">
                  <h4 className="font-medium mb-3">Actor</h4>
                  <div className="grid grid-cols-3 gap-4">
                    <div>
                      <label className="text-sm text-muted-foreground">Type</label>
                      <div>{getActorBadge(selectedEvent.actor_type)}</div>
                    </div>
                    <div>
                      <label className="text-sm text-muted-foreground">ID</label>
                      <div className="font-mono text-sm">{selectedEvent.actor_id}</div>
                    </div>
                    <div>
                      <label className="text-sm text-muted-foreground">Role</label>
                      <div>{selectedEvent.actor_role || 'N/A'}</div>
                    </div>
                  </div>
                </div>
                
                {/* Action */}
                <div className="border rounded-lg p-4">
                  <h4 className="font-medium mb-3">Action</h4>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="text-sm text-muted-foreground">Action</label>
                      <div className="font-mono">{selectedEvent.action}</div>
                    </div>
                    <div>
                      <label className="text-sm text-muted-foreground">Decision</label>
                      <div>{getDecisionBadge(selectedEvent.decision)}</div>
                    </div>
                    
                    <div>
                      <label className="text-sm text-muted-foreground">Route</label>
                      <div className="font-mono text-sm">{selectedEvent.route || 'N/A'}</div>
                    </div>
                    
                    <div>
                      <label className="text-sm text-muted-foreground">Method</label>
                      <div>{selectedEvent.method || 'N/A'}</div>
                    </div>
                  </div>
                </div>
                
                {/* Resource */}
                <div className="border rounded-lg p-4">
                  <h4 className="font-medium mb-3">Resource</h4>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="text-sm text-muted-foreground">Type</label>
                      <div>{selectedEvent.resource_type}</div>
                    </div>
                    
                    <div>
                      <label className="text-sm text-muted-foreground">ID</label>
                      <div className="font-mono text-sm">{selectedEvent.resource_id || 'N/A'}</div>
                    </div>
                  </div>
                </div>
                
                {/* Context */}
                <div className="border rounded-lg p-4">
                  <h4 className="font-medium mb-3">Context</h4>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="text-sm text-muted-foreground">IP Address</label>
                      <div className="font-mono">{selectedEvent.ip_address || 'N/A'}</div>
                    </div>
                    
                    <div>
                      <label className="text-sm text-muted-foreground">Status Code</label>
                      <div>{selectedEvent.status_code || 'N/A'}</div>
                    </div>
                  </div>
                  
                  {selectedEvent.user_agent && (
                    <div className="mt-3">
                      <label className="text-sm text-muted-foreground">User Agent</label>
                      <div className="text-sm break-all">{selectedEvent.user_agent}</div>
                    </div>
                  )}
                </div>
                
                {/* Details JSON */}
                {selectedEvent.details && Object.keys(selectedEvent.details).length > 0 && (
                  <div className="border rounded-lg p-4">
                    <h4 className="font-medium mb-3">Details</h4>
                    <pre className="text-xs bg-muted p-2 rounded overflow-auto">
                      {JSON.stringify(selectedEvent.details, null, 2)}
                    </pre>
                  </div>
                )}
                
                {/* Integrity */}
                <div className="border rounded-lg p-4 bg-muted/50">
                  <h4 className="font-medium mb-3 flex items-center gap-2">
                    <Shield className="w-4 h-4" />
                    Integrity
                  </h4>
                  <div className="space-y-2">
                    <div>
                      <label className="text-sm text-muted-foreground">Previous Hash</label>
                      <div className="font-mono text-xs truncate">
                        {selectedEvent.prev_hash || 'Genesis (no previous)'}
                      </div>
                    </div>
                    
                    <div>
                      <label className="text-sm text-muted-foreground">Event Hash</label>
                      <div className="font-mono text-xs truncate">{selectedEvent.event_hash}</div>
                    </div>
                  </div>
                </div>
              </div>
            </ScrollArea>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
