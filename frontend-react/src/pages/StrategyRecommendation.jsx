import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Button } from '../shared/Button';
import { useApi } from '../../hooks/useApi';

export function StrategyRecommendation() {
  const { diagnosisId } = useParams();
  const navigate = useNavigate();
  const { post, get, loading, error } = useApi();
  const [strategy, setStrategy] = useState(null);
  const [diagnosis, setDiagnosis] = useState(null);
  const [approved, setApproved] = useState(false);

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

  const handleApprove = async () => {
    const result = await post(`/diagnostics/${diagnosisId}/approve`, {});
    if (result) {
      setApproved(true);
    }
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
    <div className="max-w-4xl mx-auto p-6">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-white mb-2">Strategy Recommendation</h1>
        <p className="text-white/50">
          Based on {diagnosis?.primary_bottleneck?.category} bottleneck
        </p>
      </div>

      {/* Error */}
      {error && (
        <div className="mb-6 p-4 bg-red-500/10 border border-red-500/30 rounded-lg text-red-300">
          {error}
        </div>
      )}

      {/* Primary Strategy */}
      {strategy.primary_strategy && (
        <div className="mb-8">
          <div className="flex items-center gap-2 mb-4">
            <span className="bg-cyan-500/20 text-cyan-300 px-3 py-1 rounded-full text-sm font-medium">
              Recommended
            </span>
          </div>
          
          <div className="p-6 bg-white/5 rounded-xl border border-cyan-500/30">
            <h2 className="text-2xl font-bold text-white mb-2">
              {strategy.primary_strategy.name}
            </h2>
            <p className="text-white/70 mb-6">
              {strategy.primary_strategy.description}
            </p>

            {/* Stats */}
            <div className="grid grid-cols-3 gap-4 mb-6">
              <StatBox 
                label="Time Required" 
                value={`${strategy.primary_strategy.effort_hours}h`}
                sub="over 4 weeks"
              />
              <StatBox 
                label="Budget" 
                value={`$${strategy.primary_strategy.budget_required}`}
                sub="estimated"
              />
              <StatBox 
                label="Expected Impact" 
                value={strategy.primary_strategy.expected_impact}
                sub=""
                isText
              />
            </div>

            {/* Steps */}
            <div className="mb-6">
              <h3 className="text-sm font-medium text-white/50 uppercase tracking-wide mb-3">
                Implementation Steps
              </h3>
              <ol className="space-y-2">
                {strategy.primary_strategy.steps?.map((step, i) => (
                  <li key={i} className="flex items-start gap-3">
                    <span className="w-6 h-6 rounded-full bg-cyan-500/20 text-cyan-300 flex items-center justify-center text-sm font-medium shrink-0">
                      {i + 1}
                    </span>
                    <span className="text-white/80">{step}</span>
                  </li>
                ))}
              </ol>
            </div>

            {/* Measurement */}
            {strategy.measurement_plan && (
              <div className="p-4 bg-white/5 rounded-lg">
                <h3 className="text-sm font-medium text-white/50 uppercase tracking-wide mb-2">
                  How to Measure Success
                </h3>
                <ul className="space-y-1 text-sm text-white/70">
                  {strategy.measurement_plan.primary_metrics?.map((metric, i) => (
                    <li key={i}>• Track: {metric.replace(/_/g, ' ')}</li>
                  ))}
                  <li>• Review frequency: {strategy.measurement_plan.review_frequency}</li>
                  <li>• Success criteria: {strategy.measurement_plan.success_criteria}</li>
                </ul>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Supporting Strategies */}
      {strategy.supporting_strategies?.length > 0 && (
        <div className="mb-8">
          <h2 className="text-xl font-bold text-white mb-4">Supporting Initiatives</h2>
          <div className="space-y-3">
            {strategy.supporting_strategies.map((strat, i) => (
              <div key={i} className="p-4 bg-white/5 rounded-lg border border-white/10">
                <div className="flex items-center justify-between mb-2">
                  <span className="font-medium text-white">{strat.name}</span>
                  <span className="text-sm text-white/50">{strat.effort_hours}h • ${strat.budget_required}</span>
                </div>
                <p className="text-sm text-white/70">{strat.description}</p>
                <p className="text-sm text-cyan-400 mt-1">{strat.expected_impact}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Timeline */}
      {strategy.timeline?.weekly_breakdown && (
        <div className="mb-8">
          <h2 className="text-xl font-bold text-white mb-4">4-Week Timeline</h2>
          <div className="grid grid-cols-4 gap-3">
            {strategy.timeline.weekly_breakdown.map((week, i) => (
              <div key={i} className="p-4 bg-white/5 rounded-lg border border-white/10">
                <span className="text-cyan-400 text-sm font-medium">Week {week.week}</span>
                <p className="text-white/70 text-sm mt-1">{week.focus}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Risks */}
      {strategy.risks?.length > 0 && (
        <div className="mb-8">
          <h2 className="text-xl font-bold text-white mb-4">⚠️ Risks to Watch</h2>
          <ul className="space-y-2">
            {strategy.risks.map((risk, i) => (
              <li key={i} className="flex items-start gap-2 text-white/70">
                <span className="text-yellow-500">•</span>
                {risk}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Expected Outcome */}
      <div className="mb-8 p-4 bg-green-500/10 border border-green-500/30 rounded-lg">
        <h3 className="text-sm font-medium text-green-400 uppercase tracking-wide mb-2">
          Expected Outcome
        </h3>
        <p className="text-white/80">{strategy.expected_outcome}</p>
      </div>

      {/* Action Buttons */}
      <div className="flex gap-3">
        <Button 
          variant="secondary" 
          onClick={() => navigate(`/diagnostics/${diagnosisId}`)}
        >
          ← Back to Diagnosis
        </Button>
        
        {!approved ? (
          <Button 
            onClick={handleApprove}
            loading={loading}
            className="flex-1"
          >
            ✅ Approve Strategy
          </Button>
        ) : (
          <Button 
            onClick={() => navigate('/channels')}
            className="flex-1 bg-green-500 hover:bg-green-600"
          >
            → Execute via Channels
          </Button>
        )}
      </div>

      {/* Approval Note */}
      {approved && (
        <p className="mt-4 text-sm text-green-400 text-center">
          ✓ Strategy approved. Ready for execution.
        </p>
      )}
    </div>
  );
}

function StatBox({ label, value, sub, isText = false }) {
  return (
    <div className="p-3 bg-white/5 rounded-lg text-center">
      <div className={`text-lg font-bold text-white ${isText ? 'text-sm leading-tight' : ''}`}>
        {value}
      </div>
      <div className="text-xs text-white/50 mt-1">{label}</div>
      {sub && <div className="text-xs text-white/30">{sub}</div>}
    </div>
  );
}