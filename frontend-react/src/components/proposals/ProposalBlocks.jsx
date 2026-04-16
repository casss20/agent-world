import React from 'react';
import { Button } from '../shared/Button';
import { usePrefillData, generatePrefillUrl } from '../../hooks/usePrefill';

/**
 * ProposalHeader - Block 1 of proposal
 * Shows title, badge, and organization info
 */
export function ProposalHeader({ 
  name, 
  description, 
  priority = 'Recommended',
  diagnosis,
  organization = {}
}) {
  const prefillData = usePrefillData();
  const hasPrefill = Object.keys(prefillData).length > 0;

  return (
    <div className="p-6 border-b border-white/10">
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1">
          <h2 className="text-2xl font-bold text-white mb-2">
            {name}
          </h2>
          <p className="text-white/60 max-w-xl">
            {description}
          </p>
          
          {organization.name && (
            <p className="text-sm text-white/40 mt-2">
              For: {organization.name}
            </p>
          )}
        </div>
        
        <div className="flex flex-col items-end gap-2">
          <span className="bg-cyan-500/20 text-cyan-300 px-3 py-1 rounded-full text-sm font-medium border border-cyan-500/30">
            {priority}
          </span>
          {diagnosis?.primary_bottleneck && (
            <span className="text-xs text-white/40">
              Targets: {diagnosis.primary_bottleneck.category}
            </span>
          )}
          {hasPrefill && (
            <span className="text-xs text-green-400 flex items-center gap-1">
              ✓ Prefilled from link
            </span>
          )}
        </div>
      </div>
    </div>
  );
}

/**
 * ProposalOutcome - Block 2
 * Shows expected outcome in prominent badge
 */
export function ProposalOutcome({ outcome }) {
  if (!outcome) return null;

  return (
    <div className="px-6 py-3 bg-green-500/10 border-b border-white/10">
      <div className="flex items-center gap-3">
        <span className="text-2xl">🎯</span>
        <div>
          <span className="text-xs text-green-400 uppercase tracking-wide font-medium">
            Expected Outcome
          </span>
          <p className="text-white font-medium">{outcome}</p>
        </div>
      </div>
    </div>
  );
}

/**
 * ProposalCostBreakdown - Block 3
 * Shows investment required (time, budget, return)
 */
export function ProposalCostBreakdown({ 
  timeInvestment = 0, 
  budgetInvestment = 0, 
  expectedReturn = '' 
}) {
  return (
    <div className="p-6 border-b border-white/10">
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
          value={expectedReturn}
          sub="ROI positive"
          highlight
        />
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

/**
 * ProposalTimeline - Block 4
 * Visual week-by-week timeline
 */
export function ProposalTimeline({ weeklyBreakdown = [] }) {
  if (!weeklyBreakdown?.length) return null;

  return (
    <div className="p-6 border-b border-white/10">
      <h3 className="text-sm font-medium text-white/50 uppercase tracking-wide mb-4 flex items-center gap-2">
        <span>📅</span> Timeline
      </h3>
      <div className="grid grid-cols-4 gap-3">
        {weeklyBreakdown.map((week, i) => (
          <TimelineWeek 
            key={i} 
            week={week.week} 
            focus={week.focus}
            isCurrent={i === 0}
            isComplete={false}
          />
        ))}
      </div>
    </div>
  );
}

function TimelineWeek({ week, focus, isCurrent, isComplete }) {
  return (
    <div 
      className={`p-4 rounded-xl border transition-colors ${
        isCurrent 
          ? 'bg-cyan-500/10 border-cyan-500/50' 
          : isComplete 
            ? 'bg-green-500/10 border-green-500/30' 
            : 'bg-white/5 border-white/10 hover:border-white/20'
      }`}
    >
      <div className="flex items-center gap-2 mb-2">
        <span className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-medium ${
          isComplete 
            ? 'bg-green-500 text-white' 
            : isCurrent 
              ? 'bg-cyan-500 text-white' 
              : 'bg-white/10 text-white/60'
        }`}>
          {isComplete ? '✓' : week}
        </span>
        <span className={`text-xs font-medium uppercase ${
          isCurrent ? 'text-cyan-400' : 'text-white/40'
        }`}>
          Week {week}
        </span>
      </div>
      <p className="text-white/70 text-sm">{focus}</p>
    </div>
  );
}

/**
 * ProposalAgents - Block 5
 * Shows assigned agents with their tasks
 */
export function ProposalAgents({ agents = [] }) {
  const agentIcons = {
    Nova: '📈', Pixel: '🎨', Forge: '✍️', Cipher: '🔍',
    Merchant: '🛍️', Promoter: '📢', Growth: '🌱', Ultron: '🎯'
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

  const agentTasks = {
    Nova: 'Trend research',
    Pixel: 'Visual design',
    Forge: 'Content creation',
    Cipher: 'Quality review',
    Merchant: 'Publishing',
    Promoter: 'Paid ads',
    Growth: 'Organic growth',
    Ultron: 'Orchestration'
  };

  return (
    <div className="p-6 border-b border-white/10">
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
              <p className="text-xs opacity-70">{agentTasks[agent] || 'Task execution'}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

/**
 * ProposalSteps - Block 6
 * Shows key implementation steps
 */
export function ProposalSteps({ steps = [] }) {
  if (!steps?.length) return null;

  return (
    <div className="p-6 border-b border-white/10">
      <h3 className="text-sm font-medium text-white/50 uppercase tracking-wide mb-4 flex items-center gap-2">
        <span>📝</span> Key Steps
      </h3>
      <div className="space-y-2">
        {steps.slice(0, 4).map((step, i) => (
          <div key={i} className="flex items-start gap-3 text-white/70">
            <span className="w-5 h-5 rounded-full bg-white/10 flex items-center justify-center text-xs shrink-0">
              {i + 1}
            </span>
            <span className="text-sm">{step}</span>
          </div>
        ))}
        {steps.length > 4 && (
          <p className="text-sm text-white/40 pl-8">
            +{steps.length - 4} more steps
          </p>
        )}
      </div>
    </div>
  );
}

/**
 * ProposalRisks - Block 7
 * Shows potential risks
 */
export function ProposalRisks({ risks = [] }) {
  if (!risks?.length) return null;

  return (
    <div className="p-6 border-b border-white/10">
      <div className="p-4 bg-yellow-500/10 rounded-xl border border-yellow-500/20">
        <h3 className="text-sm font-medium text-yellow-400 uppercase tracking-wide mb-2 flex items-center gap-2">
          <span>⚠️</span> Risks to Watch
        </h3>
        <ul className="space-y-1">
          {risks.slice(0, 2).map((risk, i) => (
            <li key={i} className="text-sm text-white/70 flex items-start gap-2">
              <span className="text-yellow-500">•</span>
              {risk}
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}

/**
 * ProposalActions - Block 8
 * Action buttons with share functionality
 */
export function ProposalActions({ 
  onApprove, 
  onModify, 
  onDecline, 
  onShare,
  loading = false,
  shareUrl = ''
}) {
  const [showShare, setShowShare] = React.useState(false);
  const [copied, setCopied] = React.useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(shareUrl);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
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
        
        {shareUrl && (
          <div className="relative">
            <Button 
              variant="ghost"
              onClick={() => setShowShare(!showShare)}
            >
              <span>🔗</span>
            </Button>
            
            {showShare && (
              <div className="absolute bottom-full right-0 mb-2 p-3 bg-gray-900 border border-white/10 rounded-xl w-80">
                <p className="text-xs text-white/50 mb-2">Share with prefill:</p>
                <div className="flex gap-2">
                  <input 
                    type="text" 
                    value={shareUrl}
                    readOnly
                    className="flex-1 px-2 py-1 bg-white/5 border border-white/10 rounded text-xs text-white"
                  />
                  <button 
                    onClick={handleCopy}
                    className="px-2 py-1 bg-cyan-500/20 text-cyan-400 rounded text-xs"
                  >
                    {copied ? '✓' : 'Copy'}
                  </button>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

/**
 * Composed ProposalCard using all blocks
 * This replaces the monolithic ProposalCard
 */
export function ProposalCardComposed({ 
  strategy, 
  diagnosis,
  organization,
  onApprove, 
  onModify, 
  onDecline,
  loading = false,
  shareBaseUrl = ''
}) {
  if (!strategy) return null;

  const primary = strategy.primary_strategy;
  const agents = strategy.agents_assigned || ['Nova', 'Pixel', 'Forge'];

  // Generate share URL with prefill data
  const shareUrl = shareBaseUrl ? generatePrefillUrl(shareBaseUrl, {
    business_name: organization?.name || '',
    strategy_name: primary?.name || '',
    budget: primary?.budget_required || 0
  }) : '';

  return (
    <div className="bg-gradient-to-br from-white/10 to-white/5 rounded-2xl border border-cyan-500/30 overflow-hidden">
      <ProposalHeader 
        name={primary?.name || 'Growth Strategy'}
        description={primary?.description}
        diagnosis={diagnosis}
        organization={organization}
      />
      
      <ProposalOutcome outcome={primary?.expected_impact || strategy.expected_outcome} />
      
      <ProposalCostBreakdown 
        timeInvestment={primary?.effort_hours || 0}
        budgetInvestment={primary?.budget_required || 0}
        expectedReturn={primary?.expected_impact}
      />
      
      <ProposalTimeline weeklyBreakdown={strategy.timeline?.weekly_breakdown} />
      
      <ProposalAgents agents={agents} />
      
      <ProposalSteps steps={primary?.steps} />
      
      <ProposalRisks risks={strategy.risks} />
      
      <ProposalActions 
        onApprove={onApprove}
        onModify={onModify}
        onDecline={onDecline}
        loading={loading}
        shareUrl={shareUrl}
      />
    </div>
  );
}
