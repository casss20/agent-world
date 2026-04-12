import React, { useState } from 'react';
import { useLedger } from '../../providers/LedgerProvider';
import { Send, Shield, AlertCircle } from 'lucide-react';

export function CommandBar() {
  const { sendCommand, checkPermission, currentBusiness, connected } = useLedger();
  const [command, setCommand] = useState('');
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  
  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!command.trim() || loading) return;
    
    setLoading(true);
    setResult(null);
    
    try {
      const response = await sendCommand(command);
      setResult(response);
    } catch (err) {
      setResult({ status: 'error', reason: err.message });
    } finally {
      setLoading(false);
      setCommand('');
    }
  };
  
  const getStatusColor = () => {
    if (!result) return 'border-gray-700';
    switch (result.status) {
      case 'approved': return 'border-green-500/50 bg-green-500/10';
      case 'refused': return 'border-red-500/50 bg-red-500/10';
      case 'challenged': return 'border-yellow-500/50 bg-yellow-500/10';
      case 'escalated': return 'border-orange-500/50 bg-orange-500/10';
      default: return 'border-gray-700';
    }
  };
  
  return (
    <div className="bg-gray-900 border-b border-gray-800">
      <div className="max-w-7xl mx-auto px-6 py-4">
        <form onSubmit={handleSubmit} className="flex gap-3">
          <div className="flex-1 relative">
            <input
              type="text"
              value={command}
              onChange={(e) => setCommand(e.target.value)}
              placeholder={`Command Ledger${currentBusiness?.name ? ` (${currentBusiness.name})` : ''}...`}
              disabled={!connected || loading}
              className="w-full bg-gray-800 border border-gray-700 rounded-lg pl-4 pr-12 py-3 text-white placeholder-gray-500 focus:outline-none focus:border-cyan-500 disabled:opacity-50"
            />
            <div className="absolute right-3 top-1/2 -translate-y-1/2">
              {!connected ? (
                <AlertCircle className="w-5 h-5 text-red-400" />
              ) : (
                <Shield className="w-5 h-5 text-green-400" />
              )}
            </div>
          </div>
          
          <button
            type="submit"
            disabled={!connected || loading || !command.trim()}
            className="px-6 py-3 bg-cyan-600 hover:bg-cyan-500 disabled:bg-gray-700 disabled:cursor-not-allowed text-white rounded-lg font-medium flex items-center gap-2 transition-colors"
          >
            <Send className="w-4 h-4" />
            {loading ? 'Validating...' : 'Send'}
          </button>
        </form>
        
        {result && (
          <div className={`mt-3 p-3 rounded-lg border ${getStatusColor()}`}>
            <div className="flex items-center gap-2">
              <span className="font-medium capitalize">{result.status}</span>
              {result.approved ? (
                <span className="text-xs bg-green-500/20 text-green-400 px-2 py-0.5 rounded">Approved</span>
              ) : (
                <span className="text-xs bg-red-500/20 text-red-400 px-2 py-0.5 rounded">Blocked</span>
              )}
            </div>            
            {result.reason && (
              <p className="text-sm text-gray-400 mt-1">{result.reason}</p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
