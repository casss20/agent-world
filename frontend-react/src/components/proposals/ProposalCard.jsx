import React from 'react';
import { Button } from '../shared/Button';

const agentIcons = {
  Nova: '📈',
  Pixel: '🎨',
  Forge: '✍️',
  Cipher: '🔍',
  Merchant: '🛍️',
  Promoter: '📢',
  Growth: '🌱',
  Ultron: '🎯'
};

const agentColors = {
  Nova: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
  Pixel: 'bg-purple-500/20 text-purple-400 border-purple-500/30',
  Forge: 'bg-orange-500/20 text-orange-400 border-orange-500/30',
  Cipher: 'bg-indigo-500/20 text-indigo-400 border-indigo-500/30',
  Merchant: 'bg-green-500/20 text-green-400 border-green-500/30',
  Promoter: 'bg-pink-500/20 text-pink-400 border-pink-500/30',
  Growth: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30',
  Ultron: 'bg-cyan-500/20 text-cyan-400 border-cyan-500/30'
};

export function ProposalCard({ 
  strategy, 
  diagnosis,
  onApprove, 
  onModify, 
  onDecline,
  loading = false 
}) {
  if (!strategy) return null;

  const primary = strategy.primary_strategy;
  const agents = strategy.agents_assigned || ['Nova', 'Pixel', 'Forge'];
  
  // Calculate total investment
  const timeInvestment = primary?.effort_hours || 0;
  const budgetInvestment = primary?.budget_required || 0;
  
  return (
    <div className="bg-gradient-to-br from-white/10 to-white/5 rounded-2xl border border-cyan-500/30 overflow-hidden">
      {/* Header */}
      <div className="p-6 border-b border-white/10">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h2 className="text-2xl font-bold text-white mb-2">
              {primary?.name || 'Growth Strategy'}
            </h2>
            <p className="text-white/60 max-w-xl">
              {primary?.description}
            </p>
          </div>
          <div className="flex flex-col items-end gap-2">
            <span className="bg-cyan-500/20 text-cyan-300 px-3 py-1 rounded-full text-sm font-medium border border-cyan-500/30">
              {strategy.priority || 'Recommended'}
            </span>
            {diagnosis?.primary_bottleneck && (
              <span className="text-xs text-white/40">
                Targets: {diagnosis.primary_bottleneck.category}
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Expected Outcome Badge */}
      <div className="px-6 py-3 bg-green-500/10 border-b border-white/10">
        <div className="flex items-center gap-3">
          <span className="text-2xl">🎯</span>
          <div>
            <span className="text-xs text-green-400 uppercase tracking-wide font-medium">
              Expected Outcome
            </span>
            <p className="text-white font-medium">
              {primary?.expected_impact || strategy.expected_outcome}
            </p>
          </div>
        </div>
      </div>

      <div className="p-6 space-y-6">
        {/* Cost Breakdown */}
        <div>
          <h3 className="text-sm font-medium text-white/50 uppercase tracking-wide mb-4 flex items-center gap-2">
            <span>💰</span> Investment Required
          </h3>
          <div className="grid grid-cols-3 gap-4">
            <CostBox
              icon="⏱️"
              label="Your Time"
              value={`${timeInvestment}h`}
              sub="over 4 weeks"
            />
            <CostBox
              icon="💵"
              label="Budget"
              value={budgetInvestment === 0 ? 'Free' : `$${budgetInvestment}`}
              sub="tools & resources"
            />
            <CostBox
              icon="📈"
              label="Expected Return"
              value={primary?.roi_projection || strategy.expected_outcome}
              sub="ROI positive"
              highlight
            />
          </div>
        </div>

        {/* Timeline */}
        {strategy.timeline?.weekly_breakdown && (
          <div>
            <h3 className="text-sm font-medium text-white/50 uppercase tracking-wide mb-4 flex items-center gap-2">
              <span>📅</span> Timeline
            </h3>
            <div className="grid grid-cols-4 gap-3">
              {strategy.timeline.weekly_breakdown.map((week, i) => (
                <div 
                  key={i} 
                  className="p-4 bg-white/5 rounded-xl border border-white/10 hover:border-cyan-500/30 transition-colors"
                >
                  <div className="flex items-center gap-2 mb-2">
                    <span className="w-6 h-6 rounded-full bg-cyan-500/20 text-cyan-300 flex items-center justify-center text-xs font-medium">
                      {week.week}
                    </span>
                    <span className="text-cyan-400 text-xs font-medium uppercase">
                      Week {week.week}
                    </span>
                  </div>
                  <p className="text-white/70 text-sm">{week.focus}</p>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Agents Assigned */}
        <div>
          <h3 className="text-sm font-medium text-white/50 uppercase tracking-wide mb-4 flex items-center gap-2">
            <span>🤖</span> Agents Assigned
          </h3>
          <div className="flex flex-wrap gap-3">
            {agents.map((agent) => (
              <div 
                key={agent}
                className={`flex items-center gap-2 px-4 py-2 rounded-xl border ${agentColors[agent] || agentColors.Ultron}`}
              >
                <span className="text-lg">{agentIcons[agent] || '🤖'}</span>
                <div>
                  <span className="font-medium text-sm">{agent}</span>
                  <p className="text-xs opacity-70">{getAgentTask(agent)}</p>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Steps Preview */}
        {primary?.steps && (
          <div>
            <h3 className="text-sm font-medium text-white/50 uppercase tracking-wide mb-4 flex items-center gap-2">
              <span>📝</span> Key Steps
            </h3>
            <div className="space-y-2">
              {primary.steps.slice(0, 4).map((step, i) => (
                <div key={i} className="flex items-start gap-3 text-white/70">
                  <span className="w-5 h-5 rounded-full bg-white/10 flex items-center justify-center text-xs shrink-0">
                    {i + 1}
                  </span>
                  <span className="text-sm">{step}</span>
                </div>
              ))}
              {primary.steps.length > 4 && (
                <p className="text-sm text-white/40 pl-8">
                  +{primary.steps.length - 4} more steps
                </p>
              )}
            </div>
          </div>
        )}

        {/* Risks */}
        {strategy.risks?.length > 0 && (
          <div className="p-4 bg-yellow-500/10 rounded-xl border border-yellow-500/20">
            <h3 className="text-sm font-medium text-yellow-400 uppercase tracking-wide mb-2 flex items-center gap-2">
              <span>⚠️</span> Risks to Watch
            </h3>
            <ul className="space-y-1">
              {strategy.risks.slice(0, 2).map((risk, i) => (
                <li key={i} className="text-sm text-white/70 flex items-start gap-2">
                  <span className="text-yellow-500">•</span>
                  {risk}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>

      {/* Action Bar */}
      <div className="px-6 py-4 bg-white/5 border-t border-white/10">
        <div className="flex items-center gap-3">
          <Button 
            onClick={onApprove}
            loading={loading}
            className="flex-1"
          >
            <span>👍</span> Approve & Activate
          </Button>
          <Button 
            variant="secondary"
            onClick={onModify}
            disabled={loading}
          >
            <span>✏️</span> Modify
          </Button>
          <Button 
            variant="ghost"
            onClick={onDecline}
            disabled={loading}
          >
            <span>👎</span> Decline
          </Button>
        </div>
      </div>
    </div>
  );
}

function CostBox({ icon, label, value, sub, highlight = false }) {
  return (
    <div className={`p-4 rounded-xl border ${highlight ? 'bg-green-500/10 border-green-500/30' : 'bg-white/5 border-white/10'}`}>
      <div className="text-2xl mb-2">{icon}</div>
      <div className={`text-lg font-bold ${highlight ? 'text-green-400' : 'text-white'}`}>
        {value}
      </div>
      <div className="text-xs text-white/50 mt-1">{label}</div>
      {sub && <div className="text-xs text-white/30">{sub}</div>}
    </div>
  );
}

function getAgentTask(agent) {
  const tasks = {
    Nova: 'Trend research',
    Pixel: 'Visual design',
    Forge: 'Content creation',
    Cipher: 'Quality review',
    Merchant: 'Publishing',
    Promoter: 'Paid ads',
    Growth: 'Organic growth',
    Ultron: 'Orchestration'
  };
  return tasks[agent] || 'Task execution';
}
