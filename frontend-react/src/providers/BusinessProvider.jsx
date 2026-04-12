import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { useLedger } from './LedgerProvider';

const BusinessContext = createContext({
  // Business Identity
  business: null,
  businessId: null,
  
  // Business State
  goals: [],
  assets: [],
  accounts: [],
  tasks: [],
  workflows: [],
  agents: [],
  campaigns: [],
  
  // Business Memory
  businessMemory: null,
  performanceData: null,
  
  // Actions
  loadBusiness: async () => {},
  updateGoal: async () => {},
  assignTask: async () => {},
  startWorkflow: async () => {},
});

export const useBusiness = () => useContext(BusinessContext);

export function BusinessProvider({ children, businessId }) {
  const { currentBusiness, checkPermission } = useLedger();
  
  // === BUSINESS STATE ===
  const [business, setBusiness] = useState(null);
  const [goals, setGoals] = useState([]);
  const [assets, setAssets] = useState([]);
  const [accounts, setAccounts] = useState([]);
  const [tasks, setTasks] = useState([]);
  const [workflows, setWorkflows] = useState([]);
  const [agents, setAgents] = useState([]);
  const [campaigns, setCampaigns] = useState([]);
  const [businessMemory, setBusinessMemory] = useState(null);
  const [performanceData, setPerformanceData] = useState(null);
  const [loading, setLoading] = useState(true);

  const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:8000';

  // === LOAD BUSINESS DATA ===
  useEffect(() => {
    if (!businessId) return;
    
    const loadBusiness = async () => {
      setLoading(true);
      try {
        // This would call your business API
        // Mock data for now
        setBusiness({
          id: businessId,
          name: `Business ${businessId}`,
          status: 'active',
          revenue: 2847.50,
          contentPublished: 47
        });
        
        setGoals([
          { id: 1, title: 'Reach $10K/month', progress: 28, priority: 'high' },
          { id: 2, title: 'Scale to 8 businesses', progress: 100, priority: 'high' },
          { id: 3, title: 'Automate scout workflow', progress: 75, priority: 'medium' }
        ]);
        
        setAgents([
          { id: 'scout', name: 'Scout', role: 'Trend Discovery', status: 'idle' },
          { id: 'maker', name: 'Maker', role: 'Content Creation', status: 'working' },
          { id: 'merchant', name: 'Merchant', role: 'Publishing', status: 'idle' }
        ]);
        
        setWorkflows([
          { id: 'content_arbitrage', name: 'Content Arbitrage', status: 'active', runs: 47 },
          { id: 'affiliate_insert', name: 'Affiliate Insert', status: 'draft', runs: 0 }
        ]);
        
        setTasks([
          { id: 1, title: 'Monitor Reddit trends', status: 'pending', agent: 'scout' },
          { id: 2, title: 'Create blog post', status: 'active', agent: 'maker' },
          { id: 3, title: 'Publish to Ghost', status: 'pending', agent: 'merchant' }
        ]);
        
      } catch (err) {
        console.error('Failed to load business:', err);
      } finally {
        setLoading(false);
      }
    };
    
    loadBusiness();
  }, [businessId]);

  // === ACTIONS (with Ledger permission checks) ===
  const updateGoal = useCallback(async (goalId, updates) => {
    // Check permission through Ledger
    const allowed = checkPermission('modify', 'goals');
    if (!allowed) {
      throw new Error('Permission denied: requires Ledger approval');
    }
    
    setGoals(prev => prev.map(g => g.id === goalId ? { ...g, ...updates } : g));
  }, [checkPermission]);

  const assignTask = useCallback(async (taskId, agentId) => {
    const allowed = checkPermission('assign', 'tasks');
    if (!allowed) {
      throw new Error('Permission denied');
    }
    
    setTasks(prev => prev.map(t => t.id === taskId ? { ...t, agent: agentId, status: 'assigned' } : t));
  }, [checkPermission]);

  const startWorkflow = useCallback(async (workflowId, inputs = {}) => {
    const allowed = checkPermission('execute', 'workflows');
    if (!allowed) {
      throw new Error('Permission denied: workflow execution requires approval');
    }
    
    // Call workflow API
    const response = await fetch(`${API_BASE}/api/workflow/execute`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        yaml_file: `${workflowId}.yaml`,
        inputs
      })
    });
    
    return response.json();
  }, [checkPermission]);

  const value = {
    business,
    businessId,
    goals,
    assets,
    accounts,
    tasks,
    workflows,
    agents,
    campaigns,
    businessMemory,
    performanceData,
    loading,
    updateGoal,
    assignTask,
    startWorkflow,
  };

  return (
    <BusinessContext.Provider value={value}>
      {children}
    </BusinessContext.Provider>
  );
}
