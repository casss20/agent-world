import React, { useState, useEffect } from 'react';
import { Users, Zap, Layers, Activity, ChevronRight } from 'lucide-react';

/**
 * AgentDashboard — Overview of all role-based agents
 * Lists CEO, COO, Developer, Content Director, CRM
 */
export default function AgentDashboard({ onSelectAgent }) {
  const [agents, setAgents] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch('/api/agents/')
      .then((r) => r.json())
      .then((data) => {
        setAgents(data.agents || []);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, []);

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
          <h2 className="text-2xl font-bold text-gray-900">Agent Directory</h2>
          <p className="text-sm text-gray-500 mt-1">
            {agents.length} role-based agents available
          </p>
        </div>
        <div className="flex items-center gap-2 text-sm text-gray-500">
          <Zap className="w-4 h-4" />
          <span>All systems operational</span>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {agents.map((agent) => (
          <div
            key={agent.id}
            onClick={() => onSelectAgent?.(agent)}
            className="bg-white rounded-lg border border-gray-200 p-4 hover:shadow-md hover:border-blue-300 cursor-pointer transition-all"
          >
            <div className="flex items-start justify-between">
              <div className="flex items-center gap-3">
                <span className="text-3xl">{agent.emoji}</span>
                <div>
                  <h3 className="font-semibold text-gray-900">{agent.name}</h3>
                  <p className="text-xs text-gray-500">{agent.role}</p>
                </div>
              </div>
              <ChevronRight className="w-4 h-4 text-gray-400" />
            </div>

            <p className="text-sm text-gray-600 mt-3 line-clamp-2">{agent.goal}</p>

            <div className="flex flex-wrap gap-1 mt-3">
              {agent.responsibilities?.slice(0, 3).map((resp, i) => (
                <span
                  key={i}
                  className="px-2 py-0.5 bg-gray-100 text-gray-600 text-xs rounded-full"
                >
                  {resp}
                </span>
              ))}
            </div>

            <div className="flex items-center gap-4 mt-3 text-xs text-gray-400">
              <span className="flex items-center gap-1">
                <Users className="w-3 h-3" />
                Priority: {agent.priority || '—'}
              </span>
              <span className="flex items-center gap-1">
                <Layers className="w-3 h-3" />
                {agent.allowed_tools?.length || 0} tools
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
