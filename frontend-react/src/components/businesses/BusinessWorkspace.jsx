import React, { useState } from 'react';
import { useBusiness } from '../../providers/BusinessProvider';
import { useLedger } from '../../providers/LedgerProvider';
import { AssetLibrary } from '../assets/AssetLibrary';
import { HumanTaskQueue } from '../tasks/HumanTaskQueue';
import { RevenueWidget } from '../revenue/RevenueWidget';

const TABS = [
  { id: 'overview', label: 'Overview', icon: '📊' },
  { id: 'assets', label: 'Asset Library', icon: '📁' },
  { id: 'tasks', label: 'Human Tasks', icon: '✅' },
  { id: 'revenue', label: 'Revenue', icon: '💰' }
];

export function BusinessWorkspace() {
  const { business, goals, agents, workflows, tasks, loading } = useBusiness();
  const { sendCommand } = useLedger();
  const [activeTab, setActiveTab] = useState('overview');

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-white/50">Loading business workspace...</div>
      </div>
    );
  }

  const renderTabContent = () => {
    switch (activeTab) {
      case 'assets':
        return <AssetLibrary businessId={business?.id} />;
      case 'tasks':
        return <HumanTaskQueue businessId={business?.id} />;
      case 'revenue':
        return <RevenueWidget businessId={business?.id} />;
      case 'overview':
      default:
        return <OverviewTab business={business} goals={goals} agents={agents} workflows={workflows} tasks={tasks} sendCommand={sendCommand} />;
    }
  };

  return (
    <div className="p-6 space-y-6">
      {/* Business Header */}
      <header className="flex items-start justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white">{business?.name || 'Business Workspace'}</h1>
          <p className="text-white/50 mt-1">
            {business?.model_type && (
              <span className="capitalize">{business.model_type.replace('_', ' ')}</span>
            )}
            {business?.stage && (
              <span className="ml-2 px-2 py-0.5 bg-white/10 rounded text-xs">
                {business.stage}
              </span>
            )}
          </p>
        </div>
        
        <button 
          onClick={() => sendCommand(`Optimize ${business?.name} revenue`)}
          className="px-4 py-2 bg-cyan-500 hover:bg-cyan-600 rounded-lg text-sm font-medium text-white transition-colors"
        >
          Optimize Business
        </button>
      </header>

      {/* Tab Navigation */}
      <div className="flex gap-2 border-b border-white/10 pb-4">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors flex items-center gap-2 ${
              activeTab === tab.id
                ? 'bg-cyan-500/20 text-cyan-400 border border-cyan-500/50'
                : 'bg-white/5 text-white/60 hover:bg-white/10'
            }`}
          >
            <span>{tab.icon}</span>
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      <div className="min-h-[400px]">
        {renderTabContent()}
      </div>
    </div>
  );
}

function OverviewTab({ business, goals, agents, workflows, tasks, sendCommand }) {
  return (
    <div className="space-y-8">
      {/* Quick Stats */}
      <div className="grid grid-cols-4 gap-4">
        <StatCard 
          label="Revenue"
          value={`$${business?.revenue?.toLocaleString() || '0'}`}
          trend="+12%"
          icon="💰"
        />
        <StatCard 
          label="Content Published"
          value={business?.contentPublished || 0}
          icon="📝"
        />
        <StatCard 
          label="Active Agents"
          value={agents?.length || 0}
          icon="🤖"
        />
        <StatCard 
          label="Pending Tasks"
          value={tasks?.filter(t => t.status === 'pending').length || 0}
          icon="📋"
        />
      </div>

      {/* Goals Section */}
      <section>
        <div className="flex items-center gap-2 mb-4">
          <span className="text-xl">🎯</span>
          <h2 className="text-lg font-semibold text-white">Goals</h2>
        </div>
        
        <div className="grid grid-cols-3 gap-4">
          {goals?.map(goal => (
            <div key={goal.id} className="bg-white/5 border border-white/10 rounded-xl p-4">
              <div className="flex items-center justify-between mb-2">
                <span className="font-medium text-white">{goal.title}</span>
                <span className={`text-xs px-2 py-0.5 rounded ${
                  goal.priority === 'high' ? 'bg-red-500/20 text-red-400' : 'bg-white/10 text-white/60'
                }`}>
                  {goal.priority}
                </span>
              </div>
              
              <div className="w-full bg-white/10 rounded-full h-2">
                <div 
                  className="bg-cyan-500 h-2 rounded-full transition-all"
                  style={{ width: `${goal.progress}%` }}
                />
              </div>
              
              <span className="text-xs text-white/50 mt-2 block">{goal.progress}% complete</span>
            </div>
          ))}
        </div>
      </section>

      {/* Agents Section */}
      <section>
        <div className="flex items-center gap-2 mb-4">
          <span className="text-xl">🤖</span>
          <h2 className="text-lg font-semibold text-white">Agents</h2>
        </div>
        
        <div className="grid grid-cols-4 gap-4">
          {agents?.map(agent => (
            <div key={agent.id} className="bg-white/5 border border-white/10 rounded-xl p-4">
              <div className="flex items-center gap-3">
                <div className={`w-3 h-3 rounded-full ${
                  agent.status === 'working' ? 'bg-yellow-400 animate-pulse' :
                  agent.status === 'idle' ? 'bg-green-400' :
                  'bg-white/30'
                }`} />
                
                <div>
                  <p className="font-medium text-white">{agent.name}</p>
                  <p className="text-sm text-white/50">{agent.role}</p>
                </div>
              </div>
              
              <p className="text-xs text-white/40 mt-3 capitalize">Status: {agent.status}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Workflows & Tasks Grid */}
      <div className="grid grid-cols-2 gap-8">
        {/* Workflows */}
        <section>
          <div className="flex items-center gap-2 mb-4">
            <span className="text-xl">⚡</span>
            <h2 className="text-lg font-semibold text-white">Workflows</h2>
          </div>
          
          <div className="space-y-3">
            {workflows?.map(workflow => (
              <div key={workflow.id} className="bg-white/5 border border-white/10 rounded-xl p-4">
                <div className="flex items-center justify-between">
                  <span className="font-medium text-white">{workflow.name}</span>
                  <span className={`text-xs px-2 py-0.5 rounded ${
                    workflow.status === 'active' ? 'bg-green-500/20 text-green-400' : 'bg-white/10 text-white/60'
                  }`}>
                    {workflow.status}
                  </span>
                </div>
                
                <p className="text-sm text-white/50 mt-1">{workflow.runs} runs</p>
              </div>
            ))}
          </div>
        </section>

        {/* Tasks */}
        <section>
          <div className="flex items-center gap-2 mb-4">
            <span className="text-xl">📋</span>
            <h2 className="text-lg font-semibold text-white">Recent Tasks</h2>
          </div>
          
          <div className="space-y-3">
            {tasks?.slice(0, 5).map(task => (
              <div key={task.id} className="bg-white/5 border border-white/10 rounded-xl p-4">
                <div className="flex items-center justify-between">
                  <span className="font-medium text-white">{task.title}</span>
                  <span className={`text-xs px-2 py-0.5 rounded ${
                    task.status === 'active' ? 'bg-yellow-500/20 text-yellow-400' :
                    task.status === 'pending' ? 'bg-white/10 text-white/60' :
                    'bg-green-500/20 text-green-400'
                  }`}>
                    {task.status}
                  </span>
                </div>
                
                <p className="text-sm text-white/50 mt-1">Assigned to: {task.agent}</p>
              </div>
            ))}
          </div>
        </section>
      </div>
    </div>
  );
}

function StatCard({ label, value, trend, icon }) {
  return (
    <div className="bg-white/5 rounded-xl p-4 border border-white/10">
      <div className="flex items-center justify-between mb-2">
        <span className="text-white/50 text-sm">{label}</span>
        <span className="text-xl">{icon}</span>
      </div>
      <div className="flex items-baseline gap-2">
        <span className="text-2xl font-bold text-white">{value}</span>
        {trend && (
          <span className="text-sm text-green-400">{trend}</span>
        )}
      </div>
    </div>
  );
}
