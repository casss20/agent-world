import React, { useState, useEffect } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { Calendar, Download, Filter, RefreshCw, Search } from 'lucide-react';

const API_BASE = '/governance/v2/audit';

export default function AuditLogViewer() {
  const [logs, setLogs] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(false);
  const [filters, setFilters] = useState({
    actor_type: '',
    action: '',
    result: '',
    start_date: '',
    end_date: '',
    limit: 100
  });
  const [actions, setActions] = useState([]);

  // Fetch audit logs
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

  // Fetch stats
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

  // Fetch action types
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

  // Export logs
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

  useEffect(() => {
    fetchLogs();
    fetchStats();
    fetchActions();
  }, []);

  const getResultBadge = (result) => {
    const styles = {
      success: 'bg-green-100 text-green-800',
      failure: 'bg-red-100 text-red-800',
      denied: 'bg-yellow-100 text-yellow-800',
      error: 'bg-red-100 text-red-800',
      timeout: 'bg-gray-100 text-gray-800'
    };
    return <Badge className={styles[result] || ''}>{result}</Badge>;
  };

  const getActorBadge = (type) => {
    const styles = {
      user: 'bg-blue-100 text-blue-800',
      agent: 'bg-purple-100 text-purple-800',
      system: 'bg-gray-100 text-gray-800'
    };
    return <Badge className={styles[type] || ''}>{type}</Badge>;
  };

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold">Audit Log Viewer</h1>
          <p className="text-muted-foreground">
            View and export system audit logs
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={() => exportLogs('json')}>
            <Download className="w-4 h-4 mr-2" />
            Export JSON
          </Button>
          <Button variant="outline" onClick={() => exportLogs('csv')}>
            <Download className="w-4 h-4 mr-2" />
            Export CSV
          </Button>
        </div>
      </div>

      {/* Stats Cards */}
      {stats && (
        <div className="grid grid-cols-4 gap-4">
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium">Total Entries (7d)</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats.total_entries.toLocaleString()}</div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium">Success Rate</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-green-600">
                {stats.result_breakdown?.success 
                  ? Math.round((stats.result_breakdown.success / stats.total_entries) * 100)
                  : 0}%
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium">Failed Actions</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-red-600">
                {(stats.result_breakdown?.failure || 0) + (stats.result_breakdown?.error || 0)}
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium">Denied Access</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-yellow-600">
                {stats.result_breakdown?.denied || 0}
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Filters */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Filter className="w-4 h-4" />
            Filters
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-6 gap-4">
            <div>
              <label className="text-sm font-medium mb-2 block">Actor Type</label>
              <Select 
                value={filters.actor_type} 
                onValueChange={(v) => setFilters({...filters, actor_type: v})}
              >
                <SelectTrigger>
                  <SelectValue placeholder="All" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="">All</SelectItem>
                  <SelectItem value="user">User</SelectItem>
                  <SelectItem value="agent">Agent</SelectItem>
                  <SelectItem value="system">System</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <label className="text-sm font-medium mb-2 block">Action</label>
              <Select 
                value={filters.action} 
                onValueChange={(v) => setFilters({...filters, action: v})}
              >
                <SelectTrigger>
                  <SelectValue placeholder="All" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="">All</SelectItem>
                  {actions.map(action => (
                    <SelectItem key={action} value={action}>{action}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <label className="text-sm font-medium mb-2 block">Result</label>
              <Select 
                value={filters.result} 
                onValueChange={(v) => setFilters({...filters, result: v})}
              >
                <SelectTrigger>
                  <SelectValue placeholder="All" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="">All</SelectItem>
                  <SelectItem value="success">Success</SelectItem>
                  <SelectItem value="failure">Failure</SelectItem>
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
            <div className="flex items-end">
              <Button onClick={fetchLogs} disabled={loading} className="w-full">
                <RefreshCw className={`w-4 h-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
                Apply
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Logs Table */}
      <Card>
        <CardHeader>
          <CardTitle>Audit Logs ({logs.length} entries)</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="border rounded-md">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Timestamp</TableHead>
                  <TableHead>Actor</TableHead>
                  <TableHead>Action</TableHead>
                  <TableHead>Resource</TableHead>
                  <TableHead>Result</TableHead>
                  <TableHead>Request ID</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {logs.map((log) => (
                  <TableRow key={log.id}>
                    <TableCell className="font-mono text-xs">
                      {new Date(log.timestamp).toLocaleString()}
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        {getActorBadge(log.actor_type)}
                        <span className="text-sm truncate max-w-[150px]">{log.actor_id}</span>
                      </div>
                    </TableCell>
                    <TableCell>
                      <Badge variant="outline">{log.action}</Badge>
                    </TableCell>
                    <TableCell>
                      <span className="text-sm text-muted-foreground">
                        {log.resource_type}:{log.resource_id}
                      </span>
                    </TableCell>
                    <TableCell>{getResultBadge(log.result)}</TableCell>
                    <TableCell className="font-mono text-xs">
                      {log.request_id?.substring(0, 8)}...
                    </TableCell>
                  </TableRow>
                ))}
                {logs.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={6} className="text-center text-muted-foreground py-8">
                      No audit logs found
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
