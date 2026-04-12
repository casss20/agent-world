import React from 'react';
import { useBusiness } from '../../providers/BusinessProvider';
import { useLedger } from '../../providers/LedgerProvider';
import { Target, Users, Zap, BarChart3 } from 'lucide-react';

export function BusinessWorkspace() {
  const { business, goals, agents, workflows, tasks, loading } = useBusiness();
  const { sendCommand } = useLedger();

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-500">Loading business workspace...</div>
      </div>
    );
  }

  return (
    <div className="p-8 space-y-8">
      {/* Business Header */}
      <header className="flex items-start justify-between">
        <div>
          <h1 className="text-3xl font-bold">{business?.name || 'Business Workspace'}</h1>
          <p className="text-gray-500 mt-1">
            Revenue: <span className="text-green-400 font-mono">${business?.revenue?.toLocaleString()}</span>
            {' '}• Content: <span className="text-cyan-400">{business?.contentPublished} published</span>
          </p>
        </div>
        
        <button 
          onClick={() => sendCommand(`Optimize ${business?.name} revenue`)}
          className="px-4 py-2 bg-cyan-600 hover:bg-cyan-500 rounded-lg text-sm font-medium transition-colors"
        >
          Optimize Business
        </button>
      </header>

      {/* Goals Section */}
      <section>
        <div className="flex items-center gap-2 mb-4">
          <Target className="w-5 h-5 text-cyan-400" />
          <h2 className="text-lg font-semibold">Goals</h2>
        </div>
        
        <div className="grid grid-cols-3 gap-4">
          {goals.map(goal => (
            <div key={goal.id} className="bg-gray-900 border border-gray-800 rounded-lg p-4">
              <div className="flex items-center justify-between mb-2">
                <span className="font-medium">{goal.title}</span>
                <span className={`text-xs px-2 py-0.5 rounded ${
                  goal.priority === 'high' ? 'bg-red-500/20 text-red-400' : 'bg-gray-700 text-gray-400'
                }`}>
                  {goal.priority}
                </span>
              </div>
              
              <div className="w-full bg-gray-800 rounded-full h-2">
                <div 
                  className="bg-cyan-500 h-2 rounded-full transition-all"
                  style={{ width: `${goal.progress}%` }}
                />
              </div>
              
              <span className="text-xs text-gray-500 mt-2 block">{goal.progress}% complete</span>
            </div>
          ))}
        </div>
      </section>

      {/* Agents Section */}
      <section>
        <div className="flex items-center gap-2 mb-4">
          <Users className="w-5 h-5 text-purple-400" />
          <h2 className="text-lg font-semibold">Agents</h2>
        </div>
        
        <div className="grid grid-cols-3 gap-4">
          {agents.map(agent => (
            <div key={agent.id} className="bg-gray-900 border border-gray-800 rounded-lg p-4">
              <div className="flex items-center gap-3">
                <div className={`w-3 h-3 rounded-full ${
                  agent.status === 'working' ? 'bg-yellow-400 animate-pulse' :
                  agent.status === 'idle' ? 'bg-green-400' :
                  'bg-gray-500'
                }`} />
                
                <div>
                  <p className="font-medium">{agent.name}</p>
                  <p className="text-sm text-gray-500">{agent.role}</p>
                </div>
              </div>
              
              <p className="text-xs text-gray-500 mt-3 capitalize">Status: {agent.status}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Workflows & Tasks Grid */}
      <div className="grid grid-cols-2 gap-8">
        {/* Workflows */}
        <section>
          <div className="flex items-center gap-2 mb-4">
            <Zap className="w-5 h-5 text-yellow-400" />
            <h2 className="text-lg font-semibold">Workflows</h2>
          </div>
          
          <div className="space-y-3">
            {workflows.map(workflow => (
              <div key={workflow.id} className="bg-gray-900 border border-gray-800 rounded-lg p-4">
                <div className="flex items-center justify-between">
                  <span className="font-medium">{workflow.name}</span>
                  <span className={`text-xs px-2 py-0.5 rounded ${
                    workflow.status === 'active' ? 'bg-green-500/20 text-green-400' : 'bg-gray-700'
                  }`}>
                    {workflow.status}
                  </span>
                </div>
                
                <p className="text-sm text-gray-500 mt-1">{workflow.runs} runs</p>
              </div>
            ))}
          </div>
        </section>

        {/* Tasks */}
        <section>
          <div className="flex items-center gap-2 mb-4">
            <BarChart3 className="w-5 h-5 text-pink-400" />
            <h2 className="text-lg font-semibold">Tasks</h2>
          </div>
          
          <div className="space-y-3">
            {tasks.map(task => (
              <div key={task.id} className="bg-gray-900 border border-gray-800 rounded-lg p-4">
                <div className="flex items-center justify-between">
                  <span className="font-medium">{task.title}</span>
                  <span className={`text-xs px-2 py-0.5 rounded ${
                    task.status === 'active' ? 'bg-yellow-500/20 text-yellow-400' :
                    task.status === 'pending' ? 'bg-gray-700' :
                    'bg-green-500/20 text-green-400'
                  }`}>
                    {task.status}
                  </span>
                </div>
                
                <p className="text-sm text-gray-500 mt-1">Assigned to: {task.agent}</p>
              </div>
            ))}
          </div>
        </section>
      </div>
    </div>
  );
}
