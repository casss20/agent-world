import React, { useState, useEffect } from 'react';
import { Button } from '../shared/Button';
import { useApi } from '../../hooks/useApi';
import { useTaskWebSocket } from '../../hooks/useWebSocket';

const PRIORITY_COLORS = {
  urgent: 'bg-red-500/20 text-red-400 border-red-500/30',
  high: 'bg-orange-500/20 text-orange-400 border-orange-500/30',
  medium: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
  low: 'bg-white/10 text-white/60 border-white/20'
};

const STATUS_ICONS = {
  pending: '⏳',
  in_progress: '🔄',
  completed: '✅',
  blocked: '⛔'
};

export function HumanTaskQueue({ businessId }) {
  const { get, post, loading } = useApi();
  const [tasks, setTasks] = useState([]);
  const [filter, setFilter] = useState('pending');
  const [selectedTask, setSelectedTask] = useState(null);
  
  // Real-time WebSocket updates
  const { tasks: wsTasks, updates, connected, subscribeTask } = useTaskWebSocket(businessId);

  // Load initial tasks
  useEffect(() => {
    loadTasks();
  }, [businessId]);

  // Merge WebSocket updates
  useEffect(() => {
    if (wsTasks.length > 0) {
      setTasks(prev => {
        const merged = [...prev];
        wsTasks.forEach(wsTask => {
          const idx = merged.findIndex(t => t.id === wsTask.id);
          if (idx >= 0) {
            merged[idx] = { ...merged[idx], ...wsTask };
          } else {
            merged.unshift(wsTask);
          }
        });
        return merged;
      });
    }
  }, [wsTasks]);

  // Process real-time updates
  useEffect(() => {
    if (updates.length > 0) {
      const latest = updates[updates.length - 1];
      
      if (latest.data?.event === 'status_changed') {
        setTasks(prev => prev.map(t => 
          t.id === latest.data.task_id 
            ? { ...t, status: latest.data.new_status }
            : t
        ));
      }
      
      // Could trigger notifications here
      if (latest.type === 'human_intervention_required') {
        // playNotificationSound();
        // showToast(latest.data.message);
      }
    }
  }, [updates]);

  const loadTasks = async () => {
    if (!businessId) return;
    
    const response = await get(`/businesses/${businessId}/tasks`, {
      params: { 
        is_visible_to_user: true,
        limit: 50
      }
    });
    
    if (response?.tasks) {
      setTasks(response.tasks);
    }
  };

  const handleAction = async (taskId, action, data = {}) => {
    try {
      await post(`/tasks/${taskId}/${action}`, data);
      
      // Optimistic update
      setTasks(prev => prev.map(t => 
        t.id === taskId 
          ? { ...t, status: action === 'complete' ? 'completed' : 'in_progress' }
          : t
      ));
      
      setSelectedTask(null);
    } catch (err) {
      console.error('Action failed:', err);
    }
  };

  const filteredTasks = tasks.filter(t => {
    if (filter === 'all') return true;
    return t.status === filter;
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-xl font-bold text-white">Human Task Queue</h3>
          <p className="text-white/50 text-sm">
            {tasks.filter(t => t.status === 'pending').length} pending • {tasks.filter(t => t.status === 'in_progress').length} in progress
            <span className="ml-2 text-xs">
              {connected ? (
                <span className="text-green-400">● Live</span>
              ) : (
                <span className="text-white/30">○ Offline</span>
              )}
            </span>
          </p>
        </div>
        <div className="flex gap-2">
          {['pending', 'in_progress', 'completed', 'all'].map((status) => (
            <button
              key={status}
              onClick={() => setFilter(status)}
              className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                filter === status
                  ? 'bg-cyan-500/20 text-cyan-400 border border-cyan-500/50'
                  : 'bg-white/5 text-white/60 hover:bg-white/10'
              }`}
            >
              {status === 'in_progress' ? 'In Progress' : status.charAt(0).toUpperCase() + status.slice(1)}
            </button>
          ))}
        </div>
      </div>

      {/* Task List */}
      <div className="space-y-3">
        {filteredTasks.map((task) => (
          <TaskCard
            key={task.id}
            task={task}
            isSelected={selectedTask?.id === task.id}
            onClick={() => {
              setSelectedTask(task);
              subscribeTask(task.id);
            }}
            onAction={handleAction}
          />
        ))}
      </div>

      {/* Empty State */}
      {filteredTasks.length === 0 && !loading && (
        <div className="text-center py-12 bg-white/5 rounded-2xl">
          <div className="text-4xl mb-2">🎯</div>
          <p className="text-white/50">No tasks requiring attention</p>
          <p className="text-sm text-white/30 mt-1">
            Agents are handling everything automatically
          </p>
        </div>
      )}

      {loading && (
        <div className="text-center py-12">
          <div className="animate-spin w-8 h-8 border-2 border-cyan-400 border-t-transparent rounded-full mx-auto mb-4" />
          <p className="text-white/50">Loading tasks...</p>
        </div>
      )}

      {/* Task Detail Modal */}
      {selectedTask && (
        <TaskDetailModal
          task={selectedTask}
          onClose={() => setSelectedTask(null)}
          onAction={handleAction}
        />
      )}
    </div>
  );
}

function TaskCard({ task, isSelected, onClick, onAction }) {
  const priority = task.priority || 'medium';
  const status = task.status || 'pending';
  
  return (
    <div
      onClick={onClick}
      className={`p-4 bg-white/5 rounded-xl border cursor-pointer transition-all hover:bg-white/[0.07] ${
        isSelected 
          ? 'border-cyan-500/50 bg-cyan-500/5' 
          : 'border-white/10'
      }`}
    >
      <div className="flex items-start gap-4">
        <div className="text-2xl shrink-0">{STATUS_ICONS[status]}</div>
        
        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between gap-2">
            <h4 className="font-medium text-white truncate">{task.title}</h4>
            <span className={`text-xs px-2 py-0.5 rounded border shrink-0 ${PRIORITY_COLORS[priority]}`}>
              {priority}
            </span>
          </div>
          
          <p className="text-sm text-white/60 mt-1 line-clamp-2">
            {task.description}
          </p>
          
          <div className="flex items-center gap-4 mt-3 text-xs text-white/40">
            <span>🤖 {task.assigned_by || 'Agent'}</span>
            <span>📅 {new Date(task.created_at).toLocaleDateString()}</span>
            {task.due_at && (
              <span className={new Date(task.due_at) < new Date() ? 'text-red-400' : ''}>
                ⏰ Due {new Date(task.due_at).toLocaleDateString()}
              </span>
            )}
          </div>
        </div>
        
        {status === 'pending' && (
          <Button 
            variant="secondary"
            onClick={(e) => {
              e.stopPropagation();
              onAction(task.id, 'start');
            }}
          >
            Start
          </Button>
        )}
      </div>
    </div>
  );
}

function TaskDetailModal({ task, onClose, onAction }) {
  const [response, setResponse] = useState('');
  const [actionLoading, setActionLoading] = useState(false);

  const handleAction = async (action) => {
    setActionLoading(true);
    await onAction(task.id, action, { response });
    setActionLoading(false);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80">
      <div className="bg-gray-900 border border-white/10 rounded-2xl max-w-2xl w-full max-h-[90vh] overflow-auto">
        {/* Header */}
        <div className="p-6 border-b border-white/10">
          <div className="flex items-start justify-between">
            <div>
              <h2 className="text-xl font-bold text-white">{task.title}</h2>
              <p className="text-white/50 mt-1">
                From {task.assigned_by || 'Agent'} • {new Date(task.created_at).toLocaleString()}
              </p>
            </div>
            <button 
              onClick={onClose}
              className="text-white/40 hover:text-white"
            >
              ✕
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="p-6 space-y-6">
          {/* Description */}
          <div>
            <h3 className="text-sm font-medium text-white/50 uppercase tracking-wide mb-2">
              Description
            </h3>
            <p className="text-white/70">{task.description}</p>
          </div>

          {/* Context */}
          {task.context && (
            <div>
              <h3 className="text-sm font-medium text-white/50 uppercase tracking-wide mb-2">
                Context
              </h3>
              <div className="p-4 bg-white/5 rounded-xl border border-white/10">
                {task.context.conversation_history && (
                  <div className="space-y-2">
                    {task.context.conversation_history.map((msg, i) => (
                      <div key={i} className="flex gap-2 text-sm">
                        <span className="text-cyan-400 shrink-0">
                          {msg.role === 'agent' ? '🤖' : '👤'}
                        </span>
                        <span className="text-white/60">{msg.content}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Response */}
          <div>
            <h3 className="text-sm font-medium text-white/50 uppercase tracking-wide mb-2">
              Your Response
            </h3>
            <textarea
              value={response}
              onChange={(e) => setResponse(e.target.value)}
              placeholder="Enter your feedback, approval, or questions..."
              rows={4}
              className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-xl text-white placeholder-white/30 focus:outline-none focus:border-cyan-500/50 resize-none"
            />
          </div>
        </div>

        {/* Actions */}
        <div className="p-6 border-t border-white/10 flex gap-3">
          <Button 
            onClick={() => handleAction('complete')}
            loading={actionLoading}
            className="flex-1"
          >
            ✅ Approve & Complete
          </Button>
          <Button 
            variant="secondary"
            onClick={() => handleAction('request_changes')}
            disabled={actionLoading}
          >
            ✏️ Request Changes
          </Button>
          <Button 
            variant="ghost"
            onClick={onClose}
            disabled={actionLoading}
          >
            Cancel
          </Button>
        </div>
      </div>
    </div>
  );
}
