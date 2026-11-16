import React, { useState, useEffect } from 'react';
import { Activity, Play, CheckCircle, XCircle, Clock, Layers } from 'lucide-react';

/**
 * SwarmMonitor — Real-time swarm execution dashboard
 * Shows active swarms, progress, and metrics
 */
export default function SwarmMonitor() {
  const [swarms, setSwarms] = useState([]);
  const [metrics, setMetrics] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 5000);
    return () => clearInterval(interval);
  }, []);

  const fetchData = async () => {
    try {
      const [swarmsRes, metricsRes] = await Promise.all([
        fetch('/api/orchestrator/swarms'),
        fetch('/api/orchestrator/metrics'),
      ]);
      const swarmsData = await swarmsRes.json();
      const metricsData = await metricsRes.json();
      setSwarms(swarmsData.swarms || []);
      setMetrics(metricsData);
    } catch (err) {
      console.error('Failed to fetch swarm data:', err);
    } finally {
      setLoading(false);
    }
  };

  const spawnSwarm = async () => {
    try {
      const res = await fetch('/api/orchestrator/swarm/spawn', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          description: 'Demo swarm task',
          complexity: 'medium',
          framework: 'native',
        }),
      });
      const data = await res.json();
      if (data.success) {
        fetchData();
      }
    } catch (err) {
      console.error('Failed to spawn swarm:', err);
    }
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="w-4 h-4 text-green-500" />;
      case 'failed':
        return <XCircle className="w-4 h-4 text-red-500" />;
      case 'in_progress':
        return <Activity className="w-4 h-4 text-blue-500 animate-pulse" />;
      default:
        return <Clock className="w-4 h-4 text-gray-400" />;
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Activity className="w-6 h-6 animate-spin text-blue-600" />
      </div>
    );
  }

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">Swarm Monitor</h2>
          <p className="text-sm text-gray-500 mt-1">
            Multi-agent task execution tracking
          </p>
        </div>
        <button
          onClick={spawnSwarm}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
        >
          <Play className="w-4 h-4" />
          Spawn Test Swarm
        </button>
      </div>

      {/* Metrics Cards */}
      {metrics && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          <div className="bg-white rounded-lg border border-gray-200 p-4">
            <p className="text-sm text-gray-500">Total Swarms</p>
            <p className="text-2xl font-bold text-gray-900">{metrics.total_swarms}</p>
          </div>
          <div className="bg-white rounded-lg border border-gray-200 p-4">
            <p className="text-sm text-gray-500">Success Rate</p>
            <p className="text-2xl font-bold text-green-600">
              {(metrics.success_rate * 100).toFixed(0)}%
            </p>
          </div>
          <div className="bg-white rounded-lg border border-gray-200 p-4">
            <p className="text-sm text-gray-500">Active Now</p>
            <p className="text-2xl font-bold text-blue-600">{metrics.active_now}</p>
          </div>
          <div className="bg-white rounded-lg border border-gray-200 p-4">
            <p className="text-sm text-gray-500">Avg Agents/Swarm</p>
            <p className="text-2xl font-bold text-gray-900">
              {metrics.average_agents_per_swarm.toFixed(1)}
            </p>
          </div>
        </div>
      )}

      {/* Swarms Table */}
      <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
        <div className="px-4 py-3 border-b border-gray-100">
          <h3 className="font-semibold text-gray-900">Recent Swarms</h3>
        </div>
        {swarms.length === 0 ? (
          <div className="p-8 text-center text-gray-500">
            <Layers className="w-8 h-8 mx-auto mb-2 text-gray-300" />
            <p>No swarms executed yet</p>
          </div>
        ) : (
          <table className="w-full">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">Swarm ID</th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">Status</th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">Agents</th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">Framework</th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">Started</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {swarms.map((swarm) => (
                <tr key={swarm.swarm_id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 text-sm font-mono text-gray-900">
                    {swarm.swarm_id}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      {getStatusIcon(swarm.status)}
                      <span className="text-sm capitalize">{swarm.status}</span>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-600">
                    {swarm.agents_completed}/{swarm.agents_spawned}
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-600">
                    {swarm.framework}
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-500">
                    {swarm.started_at
                      ? new Date(swarm.started_at).toLocaleTimeString()
                      : '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
