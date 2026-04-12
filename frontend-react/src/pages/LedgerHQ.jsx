import React from 'react';
import { Crown, Activity } from 'lucide-react';
import { useLedger } from '../hooks/useLedger';
import { ConstitutionPanel } from '../components/ledger/ConstitutionPanel';
import { CommandInterface } from '../components/ledger/CommandInterface';
import { MemoryPanel } from '../components/ledger/MemoryPanel';
import { DecisionHistory } from '../components/ledger/DecisionHistory';

export function LedgerHQ() {
  const {
    status,
    constitution,
    memory,
    decisions,
    connected,
    sendCommand
  } = useLedger();

  return (
    <div className="min-h-screen bg-gray-950 text-white">
      {/* Header */}
      <header className="border-b border-gray-800 bg-gray-900/50 backdrop-blur">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 rounded-full bg-gradient-to-br from-cyan-500 to-purple-600 flex items-center justify-center">
                <Crown className="w-6 h-6 text-white" />
              </div>
              <div>
                <h1 className="text-2xl font-bold">Ledger HQ</h1>
                <p className="text-sm text-gray-400">Sovereign Governance Layer</p>
              </div>
            </div>
            
            <div className="flex items-center gap-6">
              <div className="flex items-center gap-2">
                <Activity className={`w-4 h-4 ${connected ? 'text-green-400' : 'text-red-400'}`} />
                <span className={`text-sm ${connected ? 'text-green-400' : 'text-red-400'}`}>
                  {connected ? 'Connected' : 'Disconnected'}
                </span>
              </div>
              
              {status && (
                <div className="text-right">
                  <p className="text-xs text-gray-500">Version {status.version}</p>
                  <p className="text-xs text-gray-500">{status.decision_count} decisions</p>
                </div>
              )}
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-6 py-8">
        <div className="grid grid-cols-12 gap-6">
          {/* Left Column - Command & Constitution */}
          <div className="col-span-12 lg:col-span-7 space-y-6">
            <CommandInterface 
              onSendCommand={sendCommand} 
              disabled={!connected}
            />
            
            <ConstitutionPanel constitution={constitution} />
            
            <DecisionHistory decisions={decisions} />
          </div>

          {/* Right Column - Memory */}
          <div className="col-span-12 lg:col-span-5">
            <MemoryPanel memory={memory} />
          </div>
        </div>
      </main>
    </div>
  );
}

export default LedgerHQ;
