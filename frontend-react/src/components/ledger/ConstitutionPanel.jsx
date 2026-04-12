import React from 'react';
import { Shield, Check, AlertTriangle, X } from 'lucide-react';

export function ConstitutionPanel({ constitution }) {
  if (!constitution) return (
    <div className="p-6 bg-gray-900 rounded-lg border border-gray-800">
      <p className="text-gray-500">Loading constitution...</p>
    </div>
  );

  const rules = constitution.rules || {};
  
  return (
    <div className="bg-gray-900 rounded-lg border border-gray-800 overflow-hidden">
      <div className="px-6 py-4 border-b border-gray-800 flex items-center gap-3">
        <Shield className="w-5 h-5 text-cyan-400" />
        <h2 className="text-lg font-semibold text-white">Constitution</h2>
        <span className="ml-auto text-xs text-gray-500">
          {constitution.source_size?.toLocaleString()} chars
        </span>
      </div>
      
      <div className="p-6 space-y-4">
        {Object.entries(rules).map(([key, active]) => (
          <div key={key} className="flex items-center justify-between">
            <span className="text-sm text-gray-300 capitalize">
              {key.replace(/_/g, ' ')}
            </span>
            {active ? (
              <span className="flex items-center gap-1 text-xs text-green-400">
                <Check className="w-3 h-3" /> Active
              </span>
            ) : (
              <span className="flex items-center gap-1 text-xs text-gray-500">
                <X className="w-3 h-3" /> Inactive
              </span>
            )}
          </div>
        ))}
      </div>
      
      <div className="px-6 py-4 bg-gray-800/50 border-t border-gray-800">
        <h3 className="text-xs font-medium text-gray-400 uppercase mb-2">Key Principles</h3>
        <ul className="space-y-1">
          {constitution.key_principles?.map((principle, i) => (
            <li key={i} className="text-sm text-gray-300 flex items-start gap-2">
              <span className="text-cyan-400 mt-1">•</span>
              {principle}
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
