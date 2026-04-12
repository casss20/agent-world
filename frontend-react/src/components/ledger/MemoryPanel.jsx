import React from 'react';
import { Brain, User, Globe, Scroll } from 'lucide-react';

export function MemoryPanel({ memory }) {
  if (!memory) return (
    <div className="p-6 bg-gray-900 rounded-lg border border-gray-800">
      <p className="text-gray-500">Loading memory...</p>
    </div>
  );

  return (
    <div className="bg-gray-900 rounded-lg border border-gray-800 overflow-hidden">
      <div className="px-6 py-4 border-b border-gray-800 flex items-center gap-3">
        <Brain className="w-5 h-5 text-purple-400" />
        <h2 className="text-lg font-semibold text-white">Memory Context</h2>
      </div>
      
      <div className="divide-y divide-gray-800">
        {/* User Profile */}
        <div className="p-6">
          <div className="flex items-center gap-2 mb-3">
            <User className="w-4 h-4 text-cyan-400" />
            <h3 className="text-sm font-medium text-gray-300">User Profile</h3>
          </div>
          <div className="bg-gray-800/50 rounded-lg p-4">
            <p className="text-sm text-gray-400 font-mono line-clamp-4">
              {memory.user_profile || 'No user profile loaded'}
            </p>
          </div>
        </div>
        
        {/* World Context */}
        <div className="p-6">
          <div className="flex items-center gap-2 mb-3">
            <Globe className="w-4 h-4 text-green-400" />
            <h3 className="text-sm font-medium text-gray-300">World Context</h3>
          </div>
          <div className="bg-gray-800/50 rounded-lg p-4">
            <p className="text-sm text-gray-400 font-mono line-clamp-6">
              {memory.current_world || 'No world context loaded'}
            </p>
          </div>
        </div>
        
        {/* Key Decisions */}
        <div className="p-6">
          <div className="flex items-center gap-2 mb-3">
            <Scroll className="w-4 h-4 text-yellow-400" />
            <h3 className="text-sm font-medium text-gray-300">Key Decisions</h3>
          </div>
          <div className="bg-gray-800/50 rounded-lg p-4">
            <p className="text-sm text-gray-400 font-mono line-clamp-4">
              {memory.key_decisions || 'No key decisions recorded'}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
