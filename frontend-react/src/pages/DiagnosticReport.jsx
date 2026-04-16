import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Button } from '../shared/Button';
import { useApi } from '../../hooks/useApi';

const SEVERITY_COLORS = {
  critical: 'bg-red-500/20 border-red-500/30 text-red-300',
  high: 'bg-orange-500/20 border-orange-500/30 text-orange-300',
  medium: 'bg-yellow-500/20 border-yellow-500/30 text-yellow-300',
  low: 'bg-blue-500/20 border-blue-500/30 text-blue-300',
  healthy: 'bg-green-500/20 border-green-500/30 text-green-300'
};

const CATEGORY_ICONS = {
  acquisition: '🎯',
  conversion: '💰',
  retention: '🔄',
  monetization: '💵',
  operations: '⚙️'
};

export function DiagnosticReport() {
  const { diagnosisId } = useParams();
  const navigate = useNavigate();
  const { get, loading, error } = useApi();
  const [diagnosis, setDiagnosis] = useState(null);

  useEffect(() => {
    if (diagnosisId) {
      loadDiagnosis();
    }
  }, [diagnosisId]);

  const loadDiagnosis = async () => {
    const data = await get(`/diagnostics/${diagnosisId}`);
    if (data) {
      setDiagnosis(data);
    }
  };

  const getHealthColor = (score) => {
    if (score >= 0.8) return 'text-green-400';
    if (score >= 0.6) return 'text-yellow-400';
    if (score >= 0.4) return 'text-orange-400';
    return 'text-red-400';
  };

  const getHealthLabel = (score) => {
    if (score >= 0.8) return 'Healthy';
    if (score >= 0.6) return 'Needs Attention';
    if (score >= 0.4) return 'At Risk';
    return 'Critical';
  };

  if (loading) {
    return (
      <div className="max-w-4xl mx-auto p-6 text-center">
        <div className="animate-spin w-8 h-8 border-2 border-cyan-400 border-t-transparent rounded-full mx-auto mb-4" />
        <p className="text-white/50">Analyzing your business...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-4xl mx-auto p-6">
        <div className="p-4 bg-red-500/10 border border-red-500/30 rounded-lg text-red-300">
          {error}
        </div>
      </div>
    );
  }

  if (!diagnosis) {
    return null;
  }

  return (
    <div className="max-w-4xl mx-auto p-6">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-white mb-2">Business Diagnosis</h1>
        <p className="text-white/50">
          Completed {new Date(diagnosis.created_at).toLocaleString()}
        </p>
      </div>

      {/* Health Score */}
      <div className="mb-8 p-6 bg-white/5 rounded-xl border border-white/10">
        <div className="flex items-center justify-between mb-4">
          <span className="text-white/70">Overall Health Score</span>
          <span className={`text-2xl font-bold ${getHealthColor(diagnosis.health_score)}`}>
            {getHealthLabel(diagnosis.health_score)}
          </span>
        </div>
        <div className="h-3 bg-white/10 rounded-full overflow-hidden">
          <div 
            className={`h-full rounded-full transition-all duration-1000 ${
              diagnosis.health_score >= 0.8 ? 'bg-green-400' :
              diagnosis.health_score >= 0.6 ? 'bg-yellow-400' :
              diagnosis.health_score >= 0.4 ? 'bg-orange-400' :
              'bg-red-400'
            }`}
            style={{ width: `${diagnosis.health_score * 100}%` }}
          />
        </div>
        <p className="mt-2 text-white/50 text-sm">
          {Math.round(diagnosis.health_score * 100)}% — Based on 4 diagnostic checks
        </p>
      </div>

      {/* Primary Bottleneck */}
      {diagnosis.primary_bottleneck && (
        <div className="mb-8">
          <h2 className="text-xl font-bold text-white mb-4 flex items-center gap-2">
            <span>🔴</span> Primary Bottleneck
          </h2>
          <BottleneckCard bottleneck={diagnosis.primary_bottleneck} isPrimary />
        </div>
      )}

      {/* Secondary Bottlenecks */}
      {diagnosis.secondary_bottlenecks?.length > 0 && (
        <div className="mb-8">
          <h2 className="text-xl font-bold text-white mb-4">Secondary Issues</h2>
          <div className="space-y-3">
            {diagnosis.secondary_bottlenecks.map((b, i) => (
              <BottleneckCard key={i} bottleneck={b} />
            ))}
          </div>
        </div>
      )}

      {/* No Issues */}
      {!diagnosis.primary_bottleneck && (
        <div className="mb-8 p-6 bg-green-500/10 border border-green-500/30 rounded-xl text-center">
          <span className="text-4xl mb-4 block">🎉</span>
          <h2 className="text-xl font-bold text-green-300 mb-2">All Systems Green!</h2>
          <p className="text-green-200/70">No significant bottlenecks detected. Focus on optimization and scaling.</p>
        </div>
      )}

      {/* Action Buttons */}
      <div className="flex gap-3">
        <Button 
          variant="secondary" 
          onClick={() => navigate('/intake')}
        >
          ← New Diagnosis
        </Button>
        
        {diagnosis.primary_bottleneck && (
          <Button 
            onClick={() => navigate(`/diagnostics/${diagnosisId}/strategy`)}
            className="flex-1"
          >
            Generate Strategy →
          </Button>
        )}
      </div>
    </div>
  );
}

function BottleneckCard({ bottleneck, isPrimary = false }) {
  const [expanded, setExpanded] = useState(isPrimary);

  return (
    <div className={`p-5 rounded-xl border transition-all ${
      isPrimary ? SEVERITY_COLORS[bottleneck.severity] || SEVERITY_COLORS.medium : 'bg-white/5 border-white/10'
    }`}>
      <div className="flex items-start gap-4">
        <span className="text-2xl">{CATEGORY_ICONS[bottleneck.category] || '🔍'}</span>
        <div className="flex-1">
          <div className="flex items-center gap-3 mb-2">
            <span className="font-bold capitalize">{bottleneck.category}</span>
            <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
              SEVERITY_COLORS[bottleneck.severity] || SEVERITY_COLORS.medium
            }`}>
              {bottleneck.severity}
            </span>
          </div>
          <p className="text-white/80 mb-2">{bottleneck.description}</p>
          <p className="text-sm text-white/50">{bottleneck.impact}</p>
          
          {/* Evidence */}
          {bottleneck.evidence?.length > 0 && (
            <button
              onClick={() => setExpanded(!expanded)}
              className="mt-3 text-sm text-cyan-400 hover:text-cyan-300 transition-colors"
            >
              {expanded ? 'Hide details' : 'Show supporting data'}
            </button>
          )}
          
          {expanded && bottleneck.evidence?.length > 0 && (
            <div className="mt-3 pt-3 border-t border-white/10 space-y-2">
              {bottleneck.evidence.map((e, i) => (
                <div key={i} className="flex items-center gap-3 text-sm">
                  <span className="text-white/50 capitalize">{e.metric.replace(/_/g, ' ')}</span>
                  <span className="text-white font-medium">{formatValue(e.value, e.metric)}</span>
                  <span className="text-white/30">vs</span>
                  <span className="text-white/50">{formatValue(e.benchmark, e.metric)}</span>
                  {e.gap > 0 && (
                    <span className="text-red-400 text-xs">-{Math.round(e.gap)}%</span>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function formatValue(value, metric) {
  if (typeof value !== 'number') return value;
  
  // Percentages
  if (metric.includes('rate') || metric.includes('ctr') || metric.includes('conversion')) {
    return `${(value * 100).toFixed(1)}%`;
  }
  
  // Currency
  if (metric.includes('revenue') || metric.includes('price')) {
    return `$${value.toLocaleString()}`;
  }
  
  // Default
  return value.toLocaleString();
}