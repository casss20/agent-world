import React, { useState, useEffect } from 'react';
import { useApi } from '../../hooks/useApi';

const GUARDRAIL_STATUS = {
  active: { color: 'bg-green-500', text: 'Active', icon: '✓' },
  triggered: { color: 'bg-yellow-500', text: 'Triggered', icon: '⚠' },
  violated: { color: 'bg-red-500', text: 'Violation', icon: '✕' },
  disabled: { color: 'bg-gray-500', text: 'Disabled', icon: '○' },
};

export function LedgerStatusPanel() {
  const { get, loading } = useApi();
  const [status, setStatus] = useState(null);
  const [constitution, setConstitution] = useState(null);
  const [activeTab, setActiveTab] = useState('overview'); // overview | constitution | memory

  useEffect(() => {
    loadStatus();
    loadConstitution();
  }, []);

  const loadStatus = async () => {
    const data = await get('/ledger/status');
    if (data) setStatus(data);
  };

  const loadConstitution = async () => {
    const data = await get('/ledger/constitution');
    if (data) setConstitution(data);
  };

  if (loading && !status) {
    return (
      <div className="p-6 text-center">
        <div className="animate-spin w-8 h-8 border-4 border-cyan-400 border-t-transparent rounded-full mx-auto mb-4" />
        <p className="text-white/50">Loading Ledger status...</p>
      </div>
    );
  }

  return (
    <div className="ledger-status-panel">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-cyan-500 to-blue-600 flex items-center justify-center text-white font-bold text-lg">
            📜
          </div>
          <div>
            <h2 className="text-xl font-bold text-white">Ledger Sovereign</h2>
            <p className="text-sm text-white/50">
              v{status?.version || '1.0.0'} • {status?.loaded_at ? new Date(status.loaded_at).toLocaleDateString() : 'Active'}
            </p>
          </div>
        </div>

        <div className="flex gap-2">
          {['overview', 'constitution', 'memory'].map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`px-3 py-1.5 text-sm rounded-lg border transition-colors ${
                activeTab === tab
                  ? 'bg-cyan-500/20 border-cyan-500/50 text-cyan-400'
                  : 'bg-white/5 border-white/10 text-white/50 hover:border-white/30'
              }`}
            >
              {tab.charAt(0).toUpperCase() + tab.slice(1)}
            </button>
          ))}
        </div>
      </div>

      {/* Content */}
      {activeTab === 'overview' && <OverviewTab status={status} />}
      {activeTab === 'constitution' && <ConstitutionTab constitution={constitution} />}
      {activeTab === 'memory' && <MemoryTab status={status} />}
    </div>
  );
}

function OverviewTab({ status }) {
  if (!status) return <p className="text-white/50 text-center p-8">No status data available</p>;

  const guardrails = status.guardrails || {};
  const stats = status.stats || {};

  return (
    <div className="space-y-4">
      {/* Stats Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <StatCard
          label="Total Decisions"
          value={stats.total_decisions || 0}
          icon="⚖️"
        />
        <StatCard
          label="Human Overrides"
          value={stats.human_overrides || 0}
          icon="👤"
          color="yellow"
        />
        <StatCard
          label="Constitutional Violations"
          value={stats.violations || 0}
          icon="⚠️"
          color="red"
        />
        <StatCard
          label="Capability Tokens Issued"
          value={stats.tokens_issued || 0}
          icon="🎫"
          color="purple"
        />
      </div>

      {/* Guardrails Status */}
      <div className="p-4 bg-white/5 rounded-xl border border-white/10">
        <h3 className="font-semibold text-white mb-3">Constitutional Guardrails</h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {Object.entries(guardrails).map(([name, isActive]) => {
            const status = isActive ? 'active' : 'disabled';
            const config = GUARDRAIL_STATUS[status];
            
            return (
              <div key={name} className="flex items-center gap-3 p-2 bg-black/20 rounded-lg">
                <div className={`w-2 h-2 rounded-full ${config.color}`} />
                <span className="text-sm text-white/80 flex-1">
                  {name.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                </span>
                <span className={`text-xs px-2 py-0.5 rounded ${config.color.replace('bg-', 'bg-').replace('500', '500/20')} ${config.color.replace('bg-', 'text-')}`}>
                  {config.icon} {config.text}
                </span>
              </div>
            );
          })}
        </div>
      </div>

      {/* Active Rules */}
      <div className="p-4 bg-white/5 rounded-xl border border-white/10">
        <h3 className="font-semibold text-white mb-3">Active Governor Rules</h3>
        <div className="space-y-2">
          {(status.governor_rules || []).map((rule, idx) => (
            <div key={idx} className="p-3 bg-black/20 rounded-lg border border-white/5">
              <div className="flex items-center gap-2 mb-1">
                <span className="text-cyan-400 font-mono text-xs">{rule.rule_id || `rule_${idx}`}</span>
                <span className="text-white/30">|</span>
                <span className={`text-xs px-2 py-0.5 rounded ${
                  rule.severity === 'critical' ? 'bg-red-500/20 text-red-400' :
                  rule.severity === 'high' ? 'bg-yellow-500/20 text-yellow-400' :
                  'bg-blue-500/20 text-blue-400'
                }`}>
                  {rule.severity || 'medium'}
                </span>
              </div>
              <p className="text-sm text-white/70">{rule.description || rule.condition}</p>
            </div>
          ))}
          {(status.governor_rules || []).length === 0 && (
            <p className="text-sm text-white/40 text-center py-4">No active governor rules</p>
          )}
        </div>
      </div>
    </div>
  );
}

function ConstitutionTab({ constitution }) {
  if (!constitution) return <p className="text-white/50 text-center p-8">No constitution data available</p>;

  return (
    <div className="space-y-4">
      <div className="p-4 bg-gradient-to-r from-cyan-500/10 to-blue-500/10 rounded-xl border border-cyan-500/20">
        <h3 className="font-semibold text-cyan-400 mb-2">Constitutional Principles</h3>
        <p className="text-sm text-white/70">
          {constitution.summary || "The Constitution defines the fundamental rules that govern all agent behavior. These rules cannot be violated under any circumstances."}
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {constitution.principles?.map((principle, idx) => (
          <div key={idx} className="p-4 bg-white/5 rounded-xl border border-white/10">
            <div className="flex items-start gap-3">
              <div className="w-8 h-8 rounded-lg bg-cyan-500/20 flex items-center justify-center text-cyan-400 font-bold text-sm">
                {idx + 1}
              </div>
              <div>
                <h4 className="font-medium text-white mb-1">{principle.title}</h4>
                <p className="text-sm text-white/60">{principle.description}</p>
                {principle.rule_reference && (
                  <code className="mt-2 block text-xs text-cyan-400/70 bg-cyan-500/5 px-2 py-1 rounded">
                    {principle.rule_reference}
                  </code>
                )}
              </div>
            </div>
          </div>
        )) || (
          <div className="col-span-2 p-8 text-center text-white/40">
            No constitutional principles defined
          </div>
        )}
      </div>

      {/* Full Text Toggle */}
      <details className="group">
        <summary className="cursor-pointer p-3 bg-white/5 rounded-lg text-sm text-white/70 hover:text-white transition-colors">
          📄 View Full Constitution Text
        </summary>
        <pre className="mt-2 p-4 bg-black/50 rounded-lg text-xs text-white/50 overflow-x-auto whitespace-pre-wrap font-mono leading-relaxed">
          {constitution.full_text || "Constitution text not loaded"}
        </pre>
      </details>
    </div>
  );
}

function MemoryTab({ status }) {
  const memories = status?.recent_memories || [];

  return (
    <div className="space-y-4">
      <div className="p-4 bg-gradient-to-r from-purple-500/10 to-pink-500/10 rounded-xl border border-purple-500/20">
        <h3 className="font-semibold text-purple-400 mb-2">Ledger Memory</h3>
        <p className="text-sm text-white/70">
          Ledger learns from interactions and stores preferences, decisions, and lessons to improve future governance decisions.
        </p>
      </div>

      <div className="space-y-3">
        {memories.length > 0 ? memories.map((memory, idx) => (
          <div key={idx} className="p-3 bg-white/5 rounded-lg border border-white/10">
            <div className="flex items-center gap-2 mb-2">
              <span className={`text-xs px-2 py-0.5 rounded ${
                memory.type === 'preference' ? 'bg-purple-500/20 text-purple-400' :
                memory.type === 'decision' ? 'bg-blue-500/20 text-blue-400' :
                memory.type === 'lesson' ? 'bg-yellow-500/20 text-yellow-400' :
                'bg-white/10 text-white/60'
              }`}>
                {memory.type}
              </span>
              <span className="text-xs text-white/40">
                {new Date(memory.timestamp).toLocaleString()}
              </span>
              <span className="text-xs text-white/30 ml-auto">
                Confidence: {(memory.confidence * 100).toFixed(0)}%
              </span>
            </div>
            <p className="text-sm text-white/80">{memory.content}</p>
            {memory.context && (
              <p className="text-xs text-white/40 mt-1">
                Context: {JSON.stringify(memory.context)}
              </p>
            )}
          </div>
        )) : (
          <div className="p-8 text-center text-white/40 bg-white/5 rounded-xl border border-white/10">
            <div className="text-3xl mb-2">🧠</div>
            <p>No memories stored yet</p>
            <p className="text-sm mt-1">Ledger will learn preferences as you interact with the system</p>
          </div>
        )}
      </div>
    </div>
  );
}

function StatCard({ label, value, icon, color = 'cyan' }) {
  const colorClasses = {
    cyan: 'from-cyan-500/20 to-blue-500/20 border-cyan-500/30',
    yellow: 'from-yellow-500/20 to-orange-500/20 border-yellow-500/30',
    red: 'from-red-500/20 to-pink-500/20 border-red-500/30',
    purple: 'from-purple-500/20 to-pink-500/20 border-purple-500/30',
  };

  return (
    <div className={`p-4 bg-gradient-to-br ${colorClasses[color]} rounded-xl border`}>
      <div className="flex items-center gap-2 mb-1">
        <span className="text-lg">{icon}</span>
        <span className="text-2xl font-bold text-white">{value.toLocaleString()}</span>
      </div>
      <span className="text-sm text-white/60">{label}</span>
    </div>
  );
}
