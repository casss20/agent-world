import React, { useState, useEffect, useCallback } from 'react';
import { useApi } from '../../hooks/useApi';
import { Button } from '../shared/Button';

const RISK_COLORS = {
  safe: 'bg-green-500/20 text-green-400 border-green-500/30',
  medium: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
  critical: 'bg-red-500/20 text-red-400 border-red-500/30',
};

const RISK_ICONS = {
  safe: '✓',
  medium: '⚠',
  critical: '✕',
};

export function LedgerApprovalQueue({ businessId, roomId }) {
  const { get, post, loading } = useApi();
  const [approvals, setApprovals] = useState([]);
  const [filter, setFilter] = useState('pending'); // pending | approved | rejected | all

  // Load pending approvals
  const loadApprovals = useCallback(async () => {
    const data = await get(`/governance/v2/approvals?business_id=${businessId}&status=${filter}`);
    if (data) {
      setApprovals(data.approvals || []);
    }
  }, [get, businessId, filter]);

  useEffect(() => {
    loadApprovals();
    // Poll every 10 seconds
    const interval = setInterval(loadApprovals, 10000);
    return () => clearInterval(interval);
  }, [loadApprovals]);

  const handleApprove = async (approvalId) => {
    const result = await post(`/governance/v2/approvals/${approvalId}/respond`, {
      decision: 'approve',
      reasoning: 'Human approved via dashboard'
    });
    if (result) {
      loadApprovals();
    }
  };

  const handleReject = async (approvalId) => {
    const result = await post(`/governance/v2/approvals/${approvalId}/respond`, {
      decision: 'reject',
      reasoning: 'Human rejected via dashboard'
    });
    if (result) {
      loadApprovals();
    }
  };

  const handleRequestChanges = async (approvalId) => {
    const result = await post(`/governance/v2/approvals/${approvalId}/respond`, {
      decision: 'request_changes',
      reasoning: 'Needs revision before approval'
    });
    if (result) {
      loadApprovals();
    }
  };

  if (loading && approvals.length === 0) {
    return (
      <div className="p-6 text-center">
        <div className="animate-spin w-8 h-8 border-4 border-cyan-400 border-t-transparent rounded-full mx-auto mb-4" />
        <p className="text-white/50">Loading approval queue...</p>
      </div>
    );
  }

  const pendingCount = approvals.filter(a => a.status === 'pending').length;

  return (
    <div className="ledger-approval-queue">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div>
          <h2 className="text-xl font-bold text-white flex items-center gap-2">
            ⏸️ Pending Approvals
            {pendingCount > 0 && (
              <span className="bg-red-500 text-white text-xs px-2 py-1 rounded-full">
                {pendingCount}
              </span>
            )}
          </h2>
          <p className="text-sm text-white/50">
            Ledger requires human approval for critical actions
          </p>
        </div>
        
        <div className="flex gap-2">
          {['pending', 'approved', 'rejected', 'all'].map((f) => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`px-3 py-1 text-sm rounded-lg border transition-colors ${
                filter === f
                  ? 'bg-cyan-500/20 border-cyan-500/50 text-cyan-400'
                  : 'bg-white/5 border-white/10 text-white/50 hover:border-white/30'
              }`}
            >
              {f.charAt(0).toUpperCase() + f.slice(1)}
            </button>
          ))}
        </div>
      </div>

      {/* Approval List */}
      <div className="space-y-3">
        {approvals.length === 0 ? (
          <div className="p-8 text-center bg-white/5 rounded-xl border border-white/10">
            <div className="text-4xl mb-3">✓</div>
            <p className="text-white/70">No {filter} approvals</p>
            <p className="text-sm text-white/40 mt-1">
              {filter === 'pending' 
                ? "All systems operating within approved parameters"
                : "Check 'all' filter to see history"}
            </p>
          </div>
        ) : (
          approvals.map((approval) => (
            <ApprovalCard
              key={approval.id}
              approval={approval}
              onApprove={() => handleApprove(approval.id)}
              onReject={() => handleReject(approval.id)}
              onRequestChanges={() => handleRequestChanges(approval.id)}
              loading={loading}
            />
          ))
        )}
      </div>
    </div>
  );
}

function ApprovalCard({ approval, onApprove, onReject, onRequestChanges, loading }) {
  const [expanded, setExpanded] = useState(false);

  const isPending = approval.status === 'pending';
  const riskLevel = approval.risk_level || 'medium';
  const agentName = approval.agent_name || 'Unknown Agent';
  const action = approval.action || 'Unknown Action';

  return (
    <div className={`p-4 rounded-xl border transition-all ${
      isPending 
        ? 'bg-white/5 border-white/20 hover:border-cyan-500/50' 
        : 'bg-white/3 border-white/10'
    }`}>
      {/* Header Row */}
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-start gap-3">
          <div className={`w-10 h-10 rounded-lg flex items-center justify-center text-lg border ${RISK_COLORS[riskLevel]}`}>
            {RISK_ICONS[riskLevel]}
          </div>
          
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="font-semibold text-white">{agentName}</span>
              <span className="text-white/40">→</span>
              <span className="text-cyan-400">{action}</span>
              <span className={`text-xs px-2 py-0.5 rounded border ${RISK_COLORS[riskLevel]}`}>
                {riskLevel.toUpperCase()}
              </span>
            </div>
            
            <p className="text-sm text-white/60 line-clamp-2">
              {approval.description || approval.reasoning}
            </p>
            
            <div className="flex items-center gap-4 mt-2 text-xs text-white/40">
              <span>Requested: {new Date(approval.requested_at).toLocaleTimeString()}</span>
              <span>•</span>
              <span>Room: {approval.room_name || approval.room_id?.slice(0, 8)}</span>
              {approval.estimated_cost && (
                <>
                  <span>•</span>
                  <span className="text-yellow-400">
                    Est. Cost: ${approval.estimated_cost}
                  </span>
                </>
              )}
            </div>
          </div>
        </div>

        {/* Action Buttons */}
        {isPending ? (
          <div className="flex gap-2">
            <Button 
              onClick={onApprove} 
              disabled={loading}
              className="bg-green-500/20 hover:bg-green-500/30 text-green-400 border-green-500/30"
            >
              ✓ Approve
            </Button>
            <Button 
              onClick={onReject} 
              disabled={loading}
              variant="secondary"
              className="text-red-400"
            >
              ✕ Reject
            </Button>
          </div>
        ) : (
          <div className={`px-3 py-1 rounded text-sm ${
            approval.status === 'approved' 
              ? 'bg-green-500/20 text-green-400' 
              : 'bg-red-500/20 text-red-400'
          }`}>
            {approval.status === 'approved' ? '✓ Approved' : '✕ Rejected'}
          </div>
        )}
      </div>

      {/* Expandable Details */}
      <button 
        onClick={() => setExpanded(!expanded)}
        className="mt-3 text-sm text-cyan-400 hover:text-cyan-300 flex items-center gap-1"
      >
        {expanded ? '▲ Hide' : '▼ Show'} Ledger Analysis
      </button>

      {expanded && (
        <div className="mt-3 p-4 bg-black/30 rounded-lg border border-white/10 space-y-3">
          {/* Constitutional Check */}
          <div>
            <h4 className="text-sm font-medium text-white mb-2">Constitutional Analysis</h4>
            <div className="space-y-1 text-sm">
              <div className="flex items-center gap-2">
                <span className={approval.checks?.external ? 'text-red-400' : 'text-green-400'}>
                  {approval.checks?.external ? '✕' : '✓'}
                </span>
                <span className="text-white/60">External action guardrail</span>
              </div>
              <div className="flex items-center gap-2">
                <span className={approval.checks?.irreversible ? 'text-red-400' : 'text-green-400'}>
                  {approval.checks?.irreversible ? '✕' : '✓'}
                </span>
                <span className="text-white/60">Irreversibility guardrail</span>
              </div>
              <div className="flex items-center gap-2">
                <span className={approval.checks?.monetary ? 'text-yellow-400' : 'text-green-400'}>
                  {approval.checks?.monetary ? '⚠' : '✓'}
                </span>
                <span className="text-white/60">Monetary commitment</span>
              </div>
            </div>
          </div>

          {/* Ledger Reasoning */}
          <div>
            <h4 className="text-sm font-medium text-white mb-2">Ledger Reasoning</h4>
            <p className="text-sm text-white/60 bg-white/5 p-3 rounded">
              {approval.ledger_reasoning || "No specific reasoning provided"}
            </p>
          </div>

          {/* Action Preview */}
          {approval.preview && (
            <div>
              <h4 className="text-sm font-medium text-white mb-2">Action Preview</h4>
              <pre className="text-xs text-white/50 bg-black/50 p-3 rounded overflow-x-auto">
                {JSON.stringify(approval.preview, null, 2)}
              </pre>
            </div>
          )}

          {/* Request Changes Button */}
          {isPending && (
            <Button 
              onClick={onRequestChanges} 
              disabled={loading}
              variant="secondary"
              className="w-full mt-2"
            >
              ✏️ Request Changes (Returns to Agent)
            </Button>
          )}
        </div>
      )}
    </div>
  );
}
