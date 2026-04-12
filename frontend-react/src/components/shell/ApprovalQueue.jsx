import React from 'react';
import { useApprovals } from '../../providers/ApprovalProvider';
import { Check, X, Clock, Bell } from 'lucide-react';

export function ApprovalQueue({ compact = false }) {
  const { queue, unreadCount, approve, deny, markRead, markAllRead } = useApprovals();
  
  if (compact) {
    return (
      <button className="relative p-2 text-gray-400 hover:text-white transition-colors">
        <Bell className="w-5 h-5" />
        {unreadCount > 0 && (
          <span className="absolute top-0 right-0 w-4 h-4 bg-red-500 text-white text-xs rounded-full flex items-center justify-center">
            {unreadCount}
          </span>
        )}
      </button>
    );
  }
  
  return (
    <div className="bg-gray-900 rounded-lg border border-gray-800 overflow-hidden">
      <div className="px-4 py-3 border-b border-gray-800 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Bell className="w-4 h-4 text-yellow-400" />
          <span className="font-medium">Approvals</span>
          {unreadCount > 0 && (
            <span className="bg-red-500 text-white text-xs px-2 py-0.5 rounded-full">
              {unreadCount}
            </span>
          )}
        </div>
        
        {queue.length > 0 && (
          <button 
            onClick={markAllRead}
            className="text-xs text-gray-500 hover:text-gray-300"
          >
            Mark all read
          </button>
        )}
      </div>
      
      <div className="max-h-64 overflow-y-auto">
        {queue.length === 0 ? (
          <div className="p-8 text-center text-gray-500">
            <Clock className="w-8 h-8 mx-auto mb-2 opacity-50" />
            <p className="text-sm">No pending approvals</p>
          </div>
        ) : (
          <div className="divide-y divide-gray-800">
            {queue.map((item) => (
              <div key={item.id} className="p-4 hover:bg-gray-800/50">
                <div className="flex items-start justify-between gap-3">
                  <div className="flex-1">
                    <p className="text-sm font-medium">{item.action}</p>
                    <p className="text-xs text-gray-500 mt-1">{item.reason}</p>
                    <span className="text-xs text-gray-600 mt-2 block">
                      {new Date(item.requestedAt).toLocaleTimeString()}
                    </span>
                  </div>
                  
                  {item.status === 'pending' ? (
                    <div className="flex gap-1">
                      <button
                        onClick={() => approve(item.id)}
                        className="p-2 text-green-400 hover:bg-green-500/10 rounded"
                      >
                        <Check className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => deny(item.id)}
                        className="p-2 text-red-400 hover:bg-red-500/10 rounded"
                      >
                        <X className="w-4 h-4" />
                      </button>
                    </div>
                  ) : (
                    <span className={`text-xs px-2 py-1 rounded ${
                      item.status === 'approved' 
                        ? 'bg-green-500/20 text-green-400' 
                        : 'bg-red-500/20 text-red-400'
                    }`}>
                      {item.status}
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
