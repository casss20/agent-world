import React from 'react';
import { useLedger } from '../providers/LedgerProvider';
import { Crown, Shield, Brain, Scroll } from 'lucide-react';

export function GlobalHQ() {
  const { 
    ledgerIdentity, 
    constitution, 
    memorySummaries, 
    recentDecisions,
    pendingApprovals 
  } = useLedger();

  return (
    <div className="p-8 space-y-8">
      {/* Header */}
      <header>
        <div className="flex items-center gap-4">
          <div className="w-16 h-16 rounded-full bg-gradient-to-br from-cyan-500 to-purple-600 flex items-center justify-center">
            <Crown className="w-8 h-8 text-white" />
          </div>
          
          <div>
            <h1 className="text-3xl font-bold">Global HQ</h1>
            <p className="text-gray-500">
              Ledger v{ledgerIdentity?.version} • {ledgerIdentity?.files_loaded} files loaded
            </p>
          </div>
        </div>
      </header>

      {/* Stats Grid */}
      <div className="grid grid-cols-4 gap-6">
        <StatCard 
          icon={<Shield className="w-6 h-6 text-cyan-400" />}
          label="Constitutional Rules"
          value={constitution?.rules ? Object.keys(constitution.rules).length : 0}
        />
        
        <StatCard 
          icon={<Brain className="w-6 h-6 text-purple-400" />}
          label="Memory Entries"
          value={recentDecisions?.length || 0}
        />
        
        <StatCard 
          icon={<Scroll className="w-6 h-6 text-yellow-400" />}
          label="Pending Approvals"
          value={pendingApprovals?.length || 0}
          highlight={pendingApprovals?.length > 0}
        />
        
        <StatCard 
          icon={<Crown className="w-6 h-6 text-green-400" />}
          label="Active Businesses"
          value={8}
        />
      </div>

      {/* Constitution Preview */}
      <section className="bg-gray-900 border border-gray-800 rounded-lg p-6">
        <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
          <Shield className="w-5 h-5 text-cyan-400" />
          Constitutional Guardrails
        </h2>
        
        <div className="grid grid-cols-2 gap-4">
          {constitution?.key_principles?.map((principle, i) => (
            <div key={i} className="flex items-start gap-3">
              <span className="text-cyan-400 mt-1">•</span>
              <span className="text-gray-300">{principle}</span>
            </div>
          ))}
        </div>
      </section>

      {/* Recent Decisions */}
      <section>
        <h2 className="text-lg font-semibold mb-4">Recent Sovereign Decisions</h2>
        
        <div className="space-y-2">
          {recentDecisions?.slice(0, 5).map((decision, i) => (
            <div key={i} className="bg-gray-900 border border-gray-800 rounded-lg p-4 flex items-center justify-between">
              <div>
                <span className={`text-sm font-medium ${
                  decision.approved ? 'text-green-400' : 'text-red-400'
                }`}>
                  {decision.type}
                </span>
                <p className="text-gray-500 text-sm mt-1">{decision.reasoning?.slice(0, 100)}...</p>
              </div>
              
              <span className="text-xs text-gray-600">
                {new Date(decision.timestamp).toLocaleTimeString()}
              </span>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}

function StatCard({ icon, label, value, highlight }) {
  return (
    <div className={`bg-gray-900 border rounded-lg p-6 ${
      highlight ? 'border-red-500/50 bg-red-500/5' : 'border-gray-800'
    }`}>
      <div className="flex items-center gap-3 mb-2">
        {icon}
        <span className="text-gray-500 text-sm">{label}</span>
      </div>
      
      <span className="text-3xl font-bold">{value}</span>
    </div>
  );
}
