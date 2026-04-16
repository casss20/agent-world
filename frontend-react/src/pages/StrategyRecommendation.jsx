import { useEffect, useState } from 'react';
import { useParams, useNavigate, useLocation } from 'react-router-dom';
import { 
  ProposalCardComposed,
  StrategyAcceptanceForm,
  StrategyTimeline
} from '../components';
import { Button } from '../components/shared/Button';
import { useApi } from '../hooks/useApi';
import { usePrefillData } from '../hooks/usePrefill';

export function StrategyRecommendation() {
  const { diagnosisId } = useParams();
  const navigate = useNavigate();
  const location = useLocation();
  const { post, get, loading, error } = useApi();
  const [strategy, setStrategy] = useState(null);
  const [diagnosis, setDiagnosis] = useState(null);
  const [business, setBusiness] = useState(null);
  const [approved, setApproved] = useState(false);
  const [showAcceptanceForm, setShowAcceptanceForm] = useState(false);
  const [acceptanceLoading, setAcceptanceLoading] = useState(false);
  
  // Check for prefill data from URL
  const prefillData = usePrefillData();
  const hasPrefill = Object.keys(prefillData).length > 0;

  useEffect(() => {
    if (diagnosisId) {
      loadData();
    }
  }, [diagnosisId]);

  const loadData = async () => {
    // Load diagnosis context
    const diagData = await get(`/diagnostics/${diagnosisId}`);
    if (diagData) {
      setDiagnosis(diagData);
      setBusiness(diagData.business);
    }

    // Generate strategy
    const stratData = await post(`/diagnostics/${diagnosisId}/strategy`, {
      max_strategies: 3
    });
    if (stratData) {
      setStrategy(stratData);
      setApproved(stratData.approved || false);
    }
  };

  const handleApprove = () => {
    // Show acceptance form instead of immediate approval
    setShowAcceptanceForm(true);
  };

  const handleAcceptanceSubmit = async (formData) => {
    setAcceptanceLoading(true);
    
    // Submit acceptance with signature
    const result = await post(`/diagnostics/${diagnosisId}/accept`, {
      ...formData,
      signature_type: formData.signature?.type,
      signature_data: formData.signature?.dataUrl || formData.signature?.text,
      accepted_at: new Date().toISOString()
    });
    
    if (result) {
      setApproved(true);
      setShowAcceptanceForm(false);
    }
    setAcceptanceLoading(false);
  };

  const handleModify = () => {
    alert('Modify functionality coming soon - will allow editing timeline, budget, and agent assignments');
  };

  const handleDecline = () => {
    navigate(`/diagnostics/${diagnosisId}`);
  };

  const handleShare = () => {
    const shareUrl = `${window.location.origin}/diagnostics/${diagnosisId}/strategy`;
    navigator.clipboard.writeText(shareUrl);
    alert('Strategy link copied to clipboard! Share with prefill: ?prefill_business_name=Acme');
  };

  if (loading || !strategy) {
    return (
      <div className="max-w-4xl mx-auto p-6 text-center">
        <div className="animate-spin w-8 h-8 border-2 border-cyan-400 border-t-transparent rounded-full mx-auto mb-4" />
        <p className="text-white/50">Generating strategy recommendations...</p>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto p-6 space-y-6">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-white mb-2">Strategy Recommendation</h1>
        <p className="text-white/50">
          {approved 
            ? 'Strategy approved and ready for execution'
            : 'Review this proposal and approve to activate agents'
          }
        </p>
        {hasPrefill && (
          <p className="text-sm text-green-400 mt-2">
            ✓ Form prefilled from shared link
          </p>
        )}
      </div>

      {/* Error */}
      {error && (
        <div className="mb-6 p-4 bg-red-500/10 border border-red-500/30 rounded-lg text-red-300">
          {error}
        </div>
      )}

      {/* Acceptance Form Modal */}
      {showAcceptanceForm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80">
          <div className="bg-gray-900 border border-white/10 rounded-2xl max-w-lg w-full max-h-[90vh] overflow-auto">
            <StrategyAcceptanceForm
              strategy={strategy}
              business={business}
              onSubmit={handleAcceptanceSubmit}
              onCancel={() => setShowAcceptanceForm(false)}
              loading={acceptanceLoading}
              prefillData={prefillData}
            />
          </div>
        </div>
      )}

      {/* Approved State */}
      {approved ? (
        <div className="space-y-6">
          <div className="p-6 bg-green-500/10 border border-green-500/30 rounded-2xl text-center">
            <div className="text-4xl mb-4">✅</div>
            <h2 className="text-xl font-bold text-white mb-2">Strategy Approved!</h2>
            <p className="text-white/60 mb-6">
              {strategy.primary_strategy?.name} is now active. Agents will begin execution.
            </p>
            
            {/* Execution Timeline */}
            <div className="mb-6 text-left">
              <StrategyTimeline strategy={strategy} currentWeek={1} />
            </div>
            
            <div className="flex gap-3 justify-center">
              <Button 
                onClick={() => navigate('/channels')}
                className="bg-green-500 hover:bg-green-600"
              >
                → Go to Channels
              </Button>
              <Button 
                variant="secondary"
                onClick={() => navigate('/hq')}
              >
                View Dashboard
              </Button>
            </div>
          </div>

          {/* Show the approved proposal (read-only) */}
          <div className="opacity-60">
            <ProposalCardComposed 
              strategy={strategy}
              diagnosis={diagnosis}
              organization={business}
              onApprove={() => {}}
              onModify={() => {}}
              onDecline={() => {}}
            />
          </div>
        </div>
      ) : (
        /* Proposal Card - Interactive */
        <ProposalCardComposed 
          strategy={strategy}
          diagnosis={diagnosis}
          organization={business}
          onApprove={handleApprove}
          onModify={handleModify}
          onDecline={handleDecline}
          loading={loading}
          shareBaseUrl={`${window.location.origin}/diagnostics/${diagnosisId}/strategy`}
        />
      )}

      {/* Visual Timeline Preview (shown before approval) */}
      {!approved && (
        <div className="mt-8">
          <h2 className="text-xl font-bold text-white mb-4">Execution Preview</h2>
          <StrategyTimeline strategy={strategy} currentWeek={0} />
        </div>
      )}

      {/* Supporting Strategies */}
      {!approved && strategy.supporting_strategies?.length > 0 && (
        <div className="mt-8">
          <h2 className="text-xl font-bold text-white mb-4">Alternative Approaches</h2>
          <div className="space-y-3">
            {strategy.supporting_strategies.map((strat, i) => (
              <div 
                key={i} 
                className="p-4 bg-white/5 rounded-xl border border-white/10 hover:border-white/20 transition-colors cursor-pointer"
                onClick={() => alert('Switch to this strategy coming soon')}
              >
                <div className="flex items-center justify-between mb-2">
                  <span className="font-medium text-white">{strat.name}</span>
                  <span className="text-sm text-white/50">
                    {strat.effort_hours}h • {strat.budget_required === 0 ? 'Free' : `$${strat.budget_required}`}
                  </span>
                </div>
                <p className="text-sm text-white/70">{strat.description}</p>
                <p className="text-sm text-cyan-400 mt-1">{strat.expected_impact}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
