import React, { createContext, useContext, useState, useCallback } from 'react';
import { useLedger } from './LedgerProvider';

const ApprovalContext = createContext({
  // Queue
  queue: [],
  unreadCount: 0,
  
  // Actions
  approve: async () => {},
  deny: async () => {},
  defer: async () => {},
  markRead: () => {},
  
  // Filters
  filterByType: () => [],
  filterByUrgency: () => [],
});

export const useApprovals = () => useContext(ApprovalContext);

export function ApprovalProvider({ children }) {
  const { pendingApprovals, resolveApproval, sendCommand } = useLedger();
  const [readIds, setReadIds] = useState(new Set());
  
  // === COMPUTED ===
  const unreadCount = pendingApprovals.filter(a => !readIds.has(a.id)).length;
  
  // === ACTIONS ===
  const approve = useCallback(async (approvalId) => {
    const approval = pendingApprovals.find(a => a.id === approvalId);
    if (!approval) return;
    
    // Log approval through Ledger
    await sendCommand(`Approve action: ${approval.action}`, {
      approval_id: approvalId,
      decision: 'approved'
    });
    
    resolveApproval(approvalId, true);
  }, [pendingApprovals, resolveApproval, sendCommand]);
  
  const deny = useCallback(async (approvalId) => {
    const approval = pendingApprovals.find(a => a.id === approvalId);
    if (!approval) return;
    
    await sendCommand(`Deny action: ${approval.action}`, {
      approval_id: approvalId,
      decision: 'denied'
    });
    
    resolveApproval(approvalId, false);
  }, [pendingApprovals, resolveApproval, sendCommand]);
  
  const defer = useCallback(async (approvalId, duration = '1h') => {
    // Mark as deferred, will re-appear later
    resolveApproval(approvalId, false);
    // Could schedule a reminder
  }, [resolveApproval]);
  
  const markRead = useCallback((approvalId) => {
    setReadIds(prev => new Set([...prev, approvalId]));
  }, []);
  
  const markAllRead = useCallback(() => {
    const allIds = pendingApprovals.map(a => a.id);
    setReadIds(new Set(allIds));
  }, [pendingApprovals]);
  
  // === FILTERS ===
  const filterByType = useCallback((type) => {
    return pendingApprovals.filter(a => a.type === type);
  }, [pendingApprovals]);
  
  const filterByUrgency = useCallback((level) => {
    return pendingApprovals.filter(a => (a.urgency || 'normal') === level);
  }, [pendingApprovals]);
  
  const value = {
    queue: pendingApprovals,
    unreadCount,
    approve,
    deny,
    defer,
    markRead,
    markAllRead,
    filterByType,
    filterByUrgency,
  };
  
  return (
    <ApprovalContext.Provider value={value}>
      {children}
    </ApprovalContext.Provider>
  );
}
