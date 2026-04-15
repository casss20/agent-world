import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';

// Vite exposes env vars via import.meta.env (not process.env)
const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';


// Ledger Context Shape
const LedgerContext = createContext({
  // Identity
  ledgerIdentity: null,
  currentBusiness: null,
  userRole: null,
  
  // Authority
  constitution: null,
  activePolicies: [],
  permissions: {},
  
  // State
  pendingApprovals: [],
  escalationState: null,
  globalPriorities: [],
  
  // Memory
  memorySummaries: null,
  recentDecisions: [],
  
  // Actions
  sendCommand: async () => {},
  checkPermission: () => false,
  requestApproval: async () => {},
  switchBusiness: () => {},
  
  // Connection
  connected: false,
  loading: true,
});

export const useLedger = () => useContext(LedgerContext);

export function LedgerProvider({ children }) {
  // === IDENTITY STATE ===
  const [ledgerIdentity, setLedgerIdentity] = useState(null);
  const [currentBusiness, setCurrentBusiness] = useState(null);
  const [userRole, setUserRole] = useState('operator'); // operator, admin, observer
  
  // === AUTHORITY STATE ===
  const [constitution, setConstitution] = useState(null);
  const [activePolicies, setActivePolicies] = useState([]);
  const [permissions, setPermissions] = useState({});
  
  // === OPERATIONAL STATE ===
  const [pendingApprovals, setPendingApprovals] = useState([]);
  const [escalationState, setEscalationState] = useState(null);
  const [globalPriorities, setGlobalPriorities] = useState([]);
  
  // === MEMORY STATE ===
  const [memorySummaries, setMemorySummaries] = useState(null);
  const [recentDecisions, setRecentDecisions] = useState([]);
  
  // === CONNECTION STATE ===
  const [connected, setConnected] = useState(false);
  const [loading, setLoading] = useState(true);
  const [ws, setWs] = useState(null);

  // === INITIAL LOAD ===
  useEffect(() => {
    const loadLedger = async () => {
      try {
        // Load constitution
        const constRes = await fetch(`${API_BASE}/ledger/constitution`);
        if (constRes.ok) setConstitution(await constRes.json());
        
        // Load status
        const statusRes = await fetch(`${API_BASE}/ledger/status`);
        if (statusRes.ok) setLedgerIdentity(await statusRes.json());
        
        // Load memory
        const memRes = await fetch(`${API_BASE}/ledger/memory`);
        if (memRes.ok) setMemorySummaries(await memRes.json());
        
        // Load decisions
        const decRes = await fetch(`${API_BASE}/ledger/decisions`);
        if (decRes.ok) {
          const decData = await decRes.json();
          setRecentDecisions(decData.decisions || []);
        }
        
        // Set default business
        setCurrentBusiness({ id: 'global', name: 'Global HQ' });
        
      } catch (err) {
        console.error('Ledger load failed:', err);
      } finally {
        setLoading(false);
      }
    };
    
    loadLedger();
  }, []);

  // === WEBSOCKET CONNECTION ===
  useEffect(() => {
    const wsUrl = API_BASE.replace('http://', 'ws://').replace('https://', 'wss://');
    const websocket = new WebSocket(`${wsUrl}/ledger/ws`);
    
    websocket.onopen = () => setConnected(true);
    websocket.onclose = () => setConnected(false);
    websocket.onmessage = (event) => {
      const data = JSON.parse(event.data);
      
      if (data.type === 'command_result') {
        // Add to recent decisions
        setRecentDecisions(prev => [data.result, ...prev].slice(0, 50));
      }
      
      if (data.type === 'approval_required') {
        setPendingApprovals(prev => [...prev, data]);
      }
      
      if (data.type === 'escalation') {
        setEscalationState(data);
      }
    };
    
    setWs(websocket);
    return () => websocket.close();
  }, []);

  // === ACTIONS ===
  const sendCommand = useCallback(async (command, context = {}) => {
    const response = await fetch(`${API_BASE}/ledger/command`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ 
        command, 
        context: {
          ...context,
          business_id: currentBusiness?.id,
          user_role: userRole
        }
      })
    });
    
    const result = await response.json();
    
    // Add to decisions if it was a real command
    if (result.status) {
      setRecentDecisions(prev => [{
        timestamp: new Date().toISOString(),
        type: result.status,
        approved: result.approved,
        reasoning: result.reason
      }, ...prev].slice(0, 50));
    }
    
    return result;
  }, [currentBusiness, userRole]);

  const checkPermission = useCallback((action, resource) => {
    // Check against constitution and policies
    if (!constitution?.rules) return false;
    
    // External actions blocked by default
    if (action === 'external' && constitution.rules.external_action_guardrail) {
      return userRole === 'admin'; // Only admins can override
    }
    
    // Irreversible actions need approval
    if (action === 'irreversible' && constitution.rules.irreversibility_guardrail) {
      return false; // Always requires explicit approval
    }
    
    return true;
  }, [constitution, userRole]);

  const requestApproval = useCallback(async (action, reason) => {
    const approval = {
      id: `app_${Date.now()}`,
      action,
      reason,
      requestedAt: new Date().toISOString(),
      status: 'pending'
    };
    
    setPendingApprovals(prev => [...prev, approval]);
    return approval.id;
  }, []);

  const switchBusiness = useCallback((business) => {
    setCurrentBusiness(business);
    // Could trigger business context load here
  }, []);

  const resolveApproval = useCallback((approvalId, approved) => {
    setPendingApprovals(prev => 
      prev.map(a => a.id === approvalId ? { ...a, status: approved ? 'approved' : 'denied' } : a)
    );
  }, []);

  const value = {
    // Identity
    ledgerIdentity,
    currentBusiness,
    userRole,
    setUserRole,
    
    // Authority
    constitution,
    activePolicies,
    permissions,
    
    // Operational
    pendingApprovals,
    escalationState,
    globalPriorities,
    
    // Memory
    memorySummaries,
    recentDecisions,
    
    // Actions
    sendCommand,
    checkPermission,
    requestApproval,
    resolveApproval,
    switchBusiness,
    
    // Connection
    connected,
    loading,
  };

  return (
    <LedgerContext.Provider value={value}>
      {children}
    </LedgerContext.Provider>
  );
}
