import React from 'react';
import { History, Check, X, HelpCircle, AlertTriangle, ArrowRight } from 'lucide-react';

export function DecisionHistory({ decisions }) {
  const entries = decisions?.decisions || [];
  
  const getStatusIcon = (status) => {
    switch (status) {
      case 'approved': return <Check className="w-4 h-4 text-green-400" />;
      case 'refused': return <X className="w-4 h-4 text-red-400" />;
      case 'challenged': return <HelpCircle className="w-4 h-4 text-yellow-400" />;
      case 'escalated': return <AlertTriangle className="w-4 h-4 text-orange-400" />;
      case 'redirected': return <ArrowRight className="w-4 h-4 text-blue-400" />;
      default: return null;
    }
  };

  return (
    <div className="bg-gray-900 rounded-lg border border-gray-800 overflow-hidden">
      <div className="px-6 py-4 border-b border-gray-800 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <History className="w-5 h-5 text-pink-400" />
          <h2 className="text-lg font-semibold text-white">Decision History</h2>
        </div>
        <span className="text-xs text-gray-500">
          {decisions?.count || 0} total
        </span>
      </div>
      
      <div className="max-h-96 overflow-y-auto">
        {entries.length === 0 ? (
          <div className="p-8 text-center">
            <p className="text-gray-500">No decisions recorded yet</p>
          </div>
        ) : (
          <div className="divide-y divide-gray-800">
            {entries.map((decision, i) => (
              <div key={i} className="p-4 hover:bg-gray-800/50 transition-colors">
                <div className="flex items-start gap-3">
                  <div className="mt-0.5">{getStatusIcon(decision.type)}</div>
                  
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-gray-500">
                        {new Date(decision.timestamp).toLocaleTimeString()}
                      </span>
                      <span className={`text-xs px-2 py-0.5 rounded ${
                        decision.approved 
                          ? 'bg-green-500/20 text-green-400' 
                          : 'bg-red-500/20 text-red-400'
                      }`}>
                        {decision.approved ? 'Approved' : 'Blocked'}
                      </span>
                    </div>
                    
                    <p className="text-sm text-gray-300 mt-1 truncate">
                      {decision.reasoning}
                    </p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
