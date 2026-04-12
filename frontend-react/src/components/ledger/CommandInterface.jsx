import React, { useState } from 'react';
import { Send, AlertCircle, CheckCircle, XCircle, HelpCircle } from 'lucide-react';

export function CommandInterface({ onSendCommand, disabled }) {
  const [command, setCommand] = useState('');
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!command.trim() || loading) return;
    
    setLoading(true);
    setResult(null);
    
    try {
      const response = await onSendCommand(command);
      setResult(response);
    } catch (err) {
      setResult({ status: 'error', reason: err.message });
    } finally {
      setLoading(false);
      setCommand('');
    }
  };

  const getStatusIcon = () => {
    if (!result) return null;
    switch (result.status) {
      case 'approved': return <CheckCircle className="w-5 h-5 text-green-400" />;
      case 'refused': return <XCircle className="w-5 h-5 text-red-400" />;
      case 'challenged': return <HelpCircle className="w-5 h-5 text-yellow-400" />;
      case 'escalated': return <AlertCircle className="w-5 h-5 text-orange-400" />;
      default: return null;
    }
  };

  const getStatusColor = () => {
    switch (result?.status) {
      case 'approved': return 'border-green-500/50 bg-green-500/10';
      case 'refused': return 'border-red-500/50 bg-red-500/10';
      case 'challenged': return 'border-yellow-500/50 bg-yellow-500/10';
      case 'escalated': return 'border-orange-500/50 bg-orange-500/10';
      default: return 'border-gray-700';
    }
  };

  return (
    <div className="bg-gray-900 rounded-lg border border-gray-800 overflow-hidden">
      <div className="px-6 py-4 border-b border-gray-800">
        <h2 className="text-lg font-semibold text-white">Ledger Command</h2>
        <p className="text-sm text-gray-500 mt-1">
          Commands are validated against constitution, alignment, and focus rules.
        </p>
      </div>
      
      <form onSubmit={handleSubmit} className="p-6">
        <div className="flex gap-3">
          <input
            type="text"
            value={command}
            onChange={(e) => setCommand(e.target.value)}
            placeholder="Enter command (e.g., 'Optimize Business 1 revenue')"
            disabled={disabled || loading}
            className="flex-1 bg-gray-800 border border-gray-700 rounded-lg px-4 py-3 text-white placeholder-gray-500 focus:outline-none focus:border-cyan-500"
          />
          <button
            type="submit"
            disabled={disabled || loading || !command.trim()}
            className="px-6 py-3 bg-cyan-600 hover:bg-cyan-500 disabled:bg-gray-700 disabled:cursor-not-allowed text-white rounded-lg font-medium flex items-center gap-2 transition-colors"
          >
            {loading ? (
              <>Validating...</>
            ) : (
              <>
                <Send className="w-4 h-4" />
                Send
              </>
            )}
          </button>
        </div>
      </form>
      
      {result && (
        <div className={`mx-6 mb-6 p-4 rounded-lg border ${getStatusColor()}`}>
          <div className="flex items-start gap-3">
            {getStatusIcon()}
            <div className="flex-1">
              <div className="flex items-center gap-2">
                <span className="font-medium text-white capitalize">
                  {result.status}
                </span>
                {result.approved ? (
                  <span className="text-xs bg-green-500/20 text-green-400 px-2 py-0.5 rounded">Approved</span>
                ) : (
                  <span className="text-xs bg-red-500/20 text-red-400 px-2 py-0.5 rounded">Blocked</span>
                )}
              </div>
              
              {result.reason && (
                <p className="text-sm text-gray-300 mt-1">{result.reason}</p>
              )}
              
              {result.governance_checks && (
                <div className="mt-3 pt-3 border-t border-gray-700/50">
                  <p className="text-xs text-gray-500 uppercase mb-2">Governance Checks</p>
                  <div className="grid grid-cols-2 gap-2">
                    {Object.entries(result.governance_checks).map(([check, data]) => (
                      <div key={check} className="flex items-center justify-between text-sm">
                        <span className="text-gray-400 capitalize">{check}</span>
                        <span className={data.approved !== false ? 'text-green-400' : 'text-red-400'}>
                          {data.approved !== false ? '✓' : '✗'}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
              
              {result.opportunity_note?.leverage_type && (
                <div className="mt-3 p-3 bg-cyan-500/10 rounded border border-cyan-500/20">
                  <p className="text-xs text-cyan-400 font-medium">💡 Opportunity Detected</p>
                  <p className="text-sm text-gray-300 mt-1">{result.opportunity_note.note}</p>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
