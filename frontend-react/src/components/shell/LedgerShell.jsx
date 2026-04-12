import React from 'react';
import { useLedger } from '../../providers/LedgerProvider';
import { CommandBar } from './CommandBar';
import { ApprovalQueue } from './ApprovalQueue';
import { Crown, Activity, Building2, ChevronDown } from 'lucide-react';

export function LedgerShell({ children }) {
  const { 
    ledgerIdentity, 
    currentBusiness, 
    constitution, 
    connected,
    pendingApprovals,
    switchBusiness 
  } = useLedger();

  // Mock businesses for dropdown
  const businesses = [
    { id: 'global', name: 'Global HQ' },
    { id: '1', name: 'Business 1: Content Arbitrage' },
    { id: '2', name: 'Business 2: SaaS Tools' },
    { id: '3', name: 'Business 3: Affiliate Sites' },
    { id: '4', name: 'Business 4: AI Products' },
    { id: '5', name: 'Business 5: Courses' },
    { id: '6', name: 'Business 6: Consulting' },
    { id: '7', name: 'Business 7: Newsletter' },
    { id: '8', name: 'Business 8: Community' },
  ];

  return (
    <div className="min-h-screen bg-gray-950 text-white flex flex-col">
      {/* Top Navigation Bar */}
      <header className="bg-gray-900 border-b border-gray-800">
        <div className="max-w-7xl mx-auto px-6">
          <div className="flex items-center justify-between h-16">
            {/* Logo */}
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-full bg-gradient-to-br from-cyan-500 to-purple-600 flex items-center justify-center">
                <Crown className="w-5 h-5 text-white" />
              </div>
              <div>
                <h1 className="font-bold text-lg">Ledger</h1>
                <p className="text-xs text-gray-500">Sovereign Governance</p>
              </div>
            </div>

            {/* Business Switcher */}
            <div className="flex items-center gap-4">
              <div className="relative">
                <select
                  value={currentBusiness?.id || 'global'}
                  onChange={(e) => {
                    const biz = businesses.find(b => b.id === e.target.value);
                    switchBusiness(biz);
                  }}
                  className="appearance-none bg-gray-800 border border-gray-700 rounded-lg pl-3 pr-10 py-2 text-sm focus:outline-none focus:border-cyan-500"
                >
                  {businesses.map(b => (
                    <option key={b.id} value={b.id}>{ b.name }</option>
                  ))}
                </select>
                <Building2 className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500 pointer-events-none" />
              </div>

              {/* Connection Status */}
              <div className="flex items-center gap-2">
                <Activity className={`w-4 h-4 ${connected ? 'text-green-400' : 'text-red-400'}`} />
                <span className={`text-sm ${connected ? 'text-green-400' : 'text-red-400'}`}>
                  {connected ? 'Connected' : 'Offline'}
                </span>
              </div>

              {/* Approval Bell */}
              <ApprovalQueue compact />
            </div>
          </div>
        </div>
      </header>

      {/* Command Bar */}
      <CommandBar />

      {/* Main Content Area */}
      <div className="flex-1 flex">
        {/* Sidebar Navigation */}
        <aside className="w-64 bg-gray-900 border-r border-gray-800">
          <nav className="p-4 space-y-1">
            <NavItem icon="📊" label="Global HQ" active={currentBusiness?.id === 'global'} />
            <div className="pt-4 pb-2">
              <p className="text-xs font-medium text-gray-500 uppercase px-3">Businesses</p>
            </div>
            <NavItem icon="1️⃣" label="Content Arbitrage" />
            <NavItem icon="2️⃣" label="SaaS Tools" />
            <NavItem icon="3️⃣" label="Affiliate Sites" />
            <NavItem icon="4️⃣" label="AI Products" />
            <NavItem icon="5️⃣" label="Courses" />
            <NavItem icon="6️⃣" label="Consulting" />
            <NavItem icon="7️⃣" label="Newsletter" />
            <NavItem icon="8️⃣" label="Community" />
            
            <div className="pt-4 pb-2">
              <p className="text-xs font-medium text-gray-500 uppercase px-3">System</p>
            </div>
            <NavItem icon="⚙️" label="Constitution" />
            <NavItem icon="🧠" label="Memory" />
            <NavItem icon="📋" label="Audit" />
          </nav>

          {/* Mini Approval Queue */}
          <div className="p-4 border-t border-gray-800">
            <ApprovalQueue />
          </div>
        </aside>

        {/* Content */}
        <main className="flex-1 overflow-auto">
          {children}
        </main>
      </div>
    </div>
  );
}

function NavItem({ icon, label, active }) {
  return (
    <a
      href="#"
      className={`flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors ${
        active 
          ? 'bg-cyan-500/10 text-cyan-400 border border-cyan-500/20' 
          : 'text-gray-400 hover:text-white hover:bg-gray-800'
      }`}
    >
      <span>{icon}</span>
      <span>{label}</span>
    </a>
  );
}
