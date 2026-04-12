import React, { useState, useEffect, createContext, useContext } from 'react';
import { Shield, Clock, AlertCircle, CheckCircle, XCircle } from 'lucide-react';

// Context for governance state
const GovernanceContext = createContext(null);

export function GovernanceProvider({ children, ledgerClient }) {
  const [capabilities, setCapabilities] = useState({});
  const [pendingApprovals, setPendingApprovals] = useState([]);
  const [featureFlags, setFeatureFlags] = useState({});

  const checkPermission = async (action, resource) => {
    try {
      const response = await ledgerClient.post('/governance/check', {
        action,
        resource
      });
      return response.data;
    } catch (error) {
      return { permitted: false, reason: 'Check failed' };
    }
  };

  const requestToken = async (action, resource, context) => {
    try {
      const response = await ledgerClient.post('/governance/token', {
        action,
        resource,
        context
      });
      return response.data.token;
    } catch (error) {
      return null;
    }
  };

  return (
    <GovernanceContext.Provider value={{
      checkPermission,
      requestToken,
      capabilities,
      pendingApprovals,
      featureFlags
    }}>
      {children}
    </GovernanceContext.Provider>
  );
}

export function useGovernance() {
  const context = useContext(GovernanceContext);
  if (!context) {
    throw new Error('useGovernance must be used within GovernanceProvider');
  }
  return context;
}

// Gate status indicator
function GateIndicator({ name, status, latency }) {
  const icons = {
    checking: <Clock className="w-4 h-4 text-yellow-400 animate-pulse" />,
    pass: <CheckCircle className="w-4 h-4 text-green-400" />,
    fail: <XCircle className="w-4 h-4 text-red-400" />,
    pending: <Clock className="w-4 h-4 text-blue-400" />
  };

  return (
    <div className="flex items-center justify-between py-1 px-2 bg-slate-800 rounded">
      <div className="flex items-center gap-2">
        {icons[status]}
        <span className="text-sm text-slate-300">{name}</span>
      </div>
      {latency && (
        <span className="text-xs text-slate-500">{latency}ms</span>
      )}
    </div>
  );
}

// Main ApprovalGate component
export function ApprovalGate({ 
  children, 
  action,
  resource,
  context = {},
  fallback = null,
  onApproved,
  onDenied,
  showStatus = false
}) {
  const { checkPermission, requestToken } = useGovernance();
  const [state, setState] = useState({
    status: 'checking', // checking | approved | denied | pending
    gates: [
      { name: 'Constitution', status: 'checking', latency: null },
      { name: 'Context', status: 'checking', latency: null },
      { name: 'Lock', status: 'checking', latency: null }
    ],
    reasoning: null,
    token: null
  });

  useEffect(() => {
    async function validate() {
      const startTime = Date.now();
      
      // Gate 1: Constitution check (instant)
      setState(s => ({
        ...s,
        gates: s.gates.map(g => 
          g.name === 'Constitution' ? { ...g, status: 'checking' } : g
        )
      }));
      
      const gate1Start = Date.now();
      const constitutionCheck = await checkPermission(action, resource);
      const gate1Latency = Date.now() - gate1Start;
      
      if (!constitutionCheck.permitted) {
        setState(s => ({
          ...s,
          status: 'denied',
          gates: s.gates.map(g => 
            g.name === 'Constitution' ? { ...g, status: 'fail', latency: gate1Latency } : g
          ),
          reasoning: constitutionCheck.reason
        }));
        onDenied?.(constitutionCheck.reason);
        return;
      }
      
      setState(s => ({
        ...s,
        gates: s.gates.map(g => 
          g.name === 'Constitution' ? { ...g, status: 'pass', latency: gate1Latency } : g
        )
      }));
      
      // Gate 2: Context check (may require approval)
      setState(s => ({
        ...s,
        gates: s.gates.map(g => 
          g.name === 'Context' ? { ...g, status: 'checking' } : g
        )
      }));
      
      const gate2Start = Date.now();
      const token = await requestToken(action, resource, context);
      const gate2Latency = Date.now() - gate2Start;
      
      if (!token) {
        // Requires approval
        setState(s => ({
          ...s,
          status: 'pending',
          gates: s.gates.map(g => 
            g.name === 'Context' ? { ...g, status: 'pending', latency: gate2Latency } : g
          ),
          reasoning: 'Human approval required'
        }));
        return;
      }
      
      setState(s => ({
        ...s,
        gates: s.gates.map(g => 
          g.name === 'Context' ? { ...g, status: 'pass', latency: gate2Latency } : g
        ),
        token
      }));
      
      // Gate 3: Lock acquisition
      setState(s => ({
        ...s,
        gates: s.gates.map(g => 
          g.name === 'Lock' ? { ...g, status: 'checking' } : g
        )
      }));
      
      const gate3Start = Date.now();
      // Simulate lock acquisition (would be real in production)
      await new Promise(r => setTimeout(r, 10));
      const gate3Latency = Date.now() - gate3Start;
      
      setState(s => ({
        ...s,
        status: 'approved',
        gates: s.gates.map(g => 
          g.name === 'Lock' ? { ...g, status: 'pass', latency: gate3Latency } : g
        )
      }));
      
      onApproved?.(token);
    }
    
    validate();
  }, [action, resource]);

  // Render based on status
  if (state.status === 'checking') {
    return (
      <div className="opacity-50 pointer-events-none">
        {showStatus && (
          <div className="mb-2 space-y-1">
            {state.gates.map(gate => (
              <GateIndicator key={gate.name} {...gate} />
            ))}
          </div>
        )}
        <div className="animate-pulse">{children}</div>
      </div>
    );
  }
  
  if (state.status === 'denied') {
    return fallback || (
      <div className="p-4 bg-red-900/20 border border-red-700 rounded-lg">
        <div className="flex items-center gap-2 text-red-400">
          <Shield className="w-5 h-5" />
          <span className="font-medium">Action Blocked</span>
        </div>
        <p className="mt-2 text-sm text-red-300">{state.reasoning}</p>
        {showStatus && (
          <div className="mt-3 space-y-1">
            {state.gates.map(gate => (
              <GateIndicator key={gate.name} {...gate} />
            ))}
          </div>
        )}
      </div>
    );
  }
  
  if (state.status === 'pending') {
    return fallback || (
      <div className="p-4 bg-blue-900/20 border border-blue-700 rounded-lg">
        <div className="flex items-center gap-2 text-blue-400">
          <Clock className="w-5 h-5" />
          <span className="font-medium">Pending Approval</span>
        </div>
        <p className="mt-2 text-sm text-blue-300">{state.reasoning}</p>
        {showStatus && (
          <div className="mt-3 space-y-1">
            {state.gates.map(gate => (
              <GateIndicator key={gate.name} {...gate} />
            ))}
          </div>
        )}
      </div>
    );
  }
  
  // Approved - render children with gate status if requested
  return (
    <>
      {showStatus && (
        <div className="mb-2 space-y-1">
          {state.gates.map(gate => (
            <GateIndicator key={gate.name} {...gate} />
          ))}
        </div>
      )}
      {children}
    </>
  );
}

// Feature flag hook
export function useFeatureFlag(capability) {
  const [enabled, setEnabled] = useState(false);
  const [loading, setLoading] = useState(true);
  
  useEffect(() => {
    async function checkFlag() {
      try {
        // This would call the backend
        const response = await fetch(`/api/governance/flags/${capability}`);
        const data = await response.json();
        setEnabled(data.enabled);
      } catch (error) {
        setEnabled(false);
      } finally {
        setLoading(false);
      }
    }
    
    checkFlag();
  }, [capability]);
  
  return { enabled, loading };
}

// FeatureFlagGate - only renders children if feature is enabled
export function FeatureFlagGate({ 
  capability, 
  children, 
  fallback = null,
  businessId 
}) {
  const { enabled, loading } = useFeatureFlag(capability);
  
  if (loading) {
    return <div className="animate-pulse opacity-50">{children}</div>;
  }
  
  if (!enabled) {
    return fallback || (
      <div className="p-4 bg-slate-800 rounded-lg text-slate-400 text-sm">
        <AlertCircle className="w-4 h-4 inline mr-2" />
        This feature is not enabled for your business.
      </div>
    );
  }
  
  return children;
}

// RiskBadge - shows risk level for an action
export function RiskBadge({ level }) {
  const styles = {
    safe: 'bg-green-900/30 text-green-400 border-green-700',
    medium: 'bg-yellow-900/30 text-yellow-400 border-yellow-700',
    critical: 'bg-red-900/30 text-red-400 border-red-700'
  };
  
  const icons = {
    safe: CheckCircle,
    medium: AlertCircle,
    critical: Shield
  };
  
  const Icon = icons[level] || AlertCircle;
  
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-1 rounded text-xs font-medium border ${styles[level]}`}>
      <Icon className="w-3 h-3" />
      {level.toUpperCase()}
    </span>
  );
}

// Export all components
export {
  GateIndicator,
  GovernanceContext,
  GovernanceProvider,
  useGovernance
};

export default ApprovalGate;
