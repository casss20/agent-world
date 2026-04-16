import React, { useState } from 'react';
import { Button } from '../shared/Button';
import { useApi } from '../../hooks/useApi';

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

  // Mock data - replace with API
  const mockTasks = [
    {
      id: '1',
      title: 'Review TikTok thumbnail design',
      description: 'Pixel created 3 thumbnail variants for the productivity video. Please select one or request changes.',
      priority: 'high',
      status: 'pending',
      agent: 'Pixel',
      trigger: 'pending_approval',
      context: {
        conversation_history: [
          { role: 'agent', content: 'I\'ve created 3 thumbnail options for your TikTok video' },
          { role: 'agent', content: 'Option A: Bold text, high contrast' },
          { role: 'agent', content: 'Option B: Minimal design, product focus' },
          { role: 'agent', content: 'Option C: Trending style with emoji' }
        ],
        preview_urls: ['thumb_a.png', 'thumb_b.png', 'thumb_c.png'],
        business_context: { niche: 'productivity', target_audience: '25-34 professionals' }
      },
      createdAt: '2025-04-16T10:30:00Z',
      dueAt: '2025-04-17T10:30:00Z'
    },
    {
      id: '2',
      title: 'Approve Meta ad copy',
      description: 'Promoter drafted 2 ad variations for the Etsy campaign. Review and approve to launch.',
      priority: 'medium',
      status: 'pending',
      agent: 'Promoter',
      trigger: 'low_confidence',
      context: {
        conversation_history: [
          { role: 'agent', content: 'I\'ve drafted ad copy for your Etsy campaign' },
          { role: 'agent', content: 'Variation A focuses on price savings' },
          { role: 'agent', content: 'Variation B focuses on quality/materials' },
          { role: 'agent', content: 'Confidence: 65% - recommend human review' }
        ],
        preview_text: 'Ad copy variations...',
        business_context: { campaign_budget: 50, target_cpa: 15 }
      },
      createdAt: '2025-04-16T09:15:00Z',
      dueAt: null
    },
    {
      id: '3',
      title: 'Provide product photos',
      description: 'Merchant needs high-quality product photos for the Etsy listing. Upload at least 5 images.',
      priority: 'urgent',
      status: 'blocked',
      agent: 'Merchant',
      trigger: 'missing_resource',
      context: {
        conversation_history: [
          { role: 'agent', content: 'I\'m ready to publish your Etsy listing' },
          { role: 'agent', content: 'Missing: Product photos (need 5 minimum)' },
          { role: 'agent', content: 'Please upload photos to continue' }
        ],
        required_items: ['product_photo_1', 'product_photo_2', 'product_photo_3', 'product_photo_4', 'product_photo_5'],
        business_context: { listing_draft_ready: true }
      },
      createdAt: '2025-04-15T14:00:00Z',
      dueAt: '2025-04-16T14:00:00Z'
    }
  ];

  React.useEffect(() => {
    setTasks(mockTasks);
  }, [businessId]);

  const filteredTasks = tasks.filter(t => filter === 'all' || t.status === filter);

  const handleComplete = async (taskId, decision, feedback = '') => {
    // TODO: API call
    alert(`Task ${taskId} completed with decision: ${decision}\nFeedback: ${feedback}`);
    setTasks(tasks.filter(t => t.id !== taskId));
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-xl font-bold text-white">Human Tasks</h3>
          <p className="text-white/50 text-sm">
            {tasks.filter(t => t.status === 'pending').length} tasks need your attention
          </p>
        </div>
        <div className="flex gap-2">
          {['pending', 'in_progress', 'all'].map((f) => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                filter === f
                  ? 'bg-cyan-500/20 text-cyan-400 border border-cyan-500/50'
                  : 'bg-white/5 text-white/60 hover:bg-white/10'
              }`}
            >
              {f === 'all' ? 'All' : f.replace('_', ' ')}
            </button>
          ))}
        </div>
      </div>

      {/* Task List */}
      <div className="space-y-4">
        {filteredTasks.map((task) => (
          <TaskCard 
            key={task.id} 
            task={task} 
            onComplete={handleComplete}
          />
        ))}
      </div>

      {/* Empty State */}
      {filteredTasks.length === 0 && (
        <div className="text-center py-12 bg-white/5 rounded-2xl">
          <div className="text-4xl mb-2">🎉</div>
          <p className="text-white/50">No tasks pending</p>
          <p className="text-sm text-white/30 mt-1">
            Agents are handling everything automatically
          </p>
        </div>
      )}
    </div>
  );
}

function TaskCard({ task, onComplete }) {
  const [expanded, setExpanded] = useState(false);
  const [feedback, setFeedback] = useState('');
  const [showFeedbackInput, setShowFeedbackInput] = useState(false);

  return (
    <div className="bg-white/5 rounded-xl border border-white/10 overflow-hidden">
      {/* Header */}
      <div 
        className="p-4 flex items-start gap-4 cursor-pointer hover:bg-white/5 transition-colors"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="text-2xl">{STATUS_ICONS[task.status]}</div>
        
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <h4 className="font-medium text-white">{task.title}</h4>
            <span className={`text-xs px-2 py-0.5 rounded border ${PRIORITY_COLORS[task.priority]}`}>
              {task.priority}
            </span>
            {task.dueAt && new Date(task.dueAt) < new Date() && (
              <span className="text-xs px-2 py-0.5 rounded bg-red-500/20 text-red-400 border border-red-500/30">
                overdue
              </span>
            )}
          </div>
          <p className="text-sm text-white/60 mt-1 line-clamp-2">{task.description}</p>
          
          <div className="flex items-center gap-4 mt-2 text-xs text-white/40">
            <span>🤖 From {task.agent}</span>
            <span>•</span>
            <span>Trigger: {task.trigger.replace('_', ' ')}</span>
            {task.dueAt && (
              <>
                <span>•</span>
                <span>Due: {new Date(task.dueAt).toLocaleDateString()}</span>
              </>
            )}
          </div>
        </div>

        <div className="text-white/30">
          {expanded ? '▼' : '▶'}
        </div>
      </div>

      {/* Expanded Content */}
      {expanded && (
        <div className="px-4 pb-4 border-t border-white/10">
          {/* Context */}
          <div className="py-4 space-y-4">
            <div>
              <h5 className="text-sm font-medium text-white/50 mb-2">Conversation History</h5>
              <div className="bg-black/20 rounded-lg p-3 space-y-2 max-h-40 overflow-y-auto">
                {task.context.conversation_history.map((msg, i) => (
                  <div key={i} className="text-sm">
                    <span className="text-cyan-400 font-medium">
                      {msg.role === 'agent' ? 'Agent' : 'You'}:
                    </span>
                    <span className="text-white/70 ml-2">{msg.content}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Action Required */}
            {task.context.preview_urls && (
              <div>
                <h5 className="text-sm font-medium text-white/50 mb-2">Preview</h5>
                <div className="flex gap-2">
                  {task.context.preview_urls.map((url, i) => (
                    <div 
                      key={i}
                      className="w-20 h-20 bg-white/10 rounded-lg flex items-center justify-center text-2xl"
                    >
                      🖼️
                    </div>
                  ))}
                </div>
              </div>
            )}

            {task.context.required_items && (
              <div>
                <h5 className="text-sm font-medium text-white/50 mb-2">Required Items</h5>
                <ul className="space-y-1">
                  {task.context.required_items.map((item, i) => (
                    <li key={i} className="text-sm text-white/60 flex items-center gap-2">
                      <span className="text-yellow-500">⚠️</span>
                      {item}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>

          {/* Actions */}
          {!showFeedbackInput ? (
            <div className="flex gap-2">
              <Button 
                onClick={() => onComplete(task.id, 'approve')}
                className="flex-1"
              >
                ✅ Approve
              </Button>
              <Button 
                variant="secondary"
                onClick={() => setShowFeedbackInput(true)}
              >
                ✏️ Request Changes
              </Button>
              <Button 
                variant="ghost"
                onClick={() => onComplete(task.id, 'reject')}
              >
                👎 Reject
              </Button>
            </div>
          ) : (
            <div className="space-y-3">
              <textarea
                value={feedback}
                onChange={(e) => setFeedback(e.target.value)}
                placeholder="Describe what changes you need..."
                className="w-full px-3 py-2 bg-white/5 border border-white/10 rounded-lg text-white placeholder-white/30 focus:outline-none focus:border-cyan-500/50 min-h-[80px]"
              />
              <div className="flex gap-2">
                <Button 
                  onClick={() => onComplete(task.id, 'request_changes', feedback)}
                  className="flex-1"
                >
                  Submit Feedback
                </Button>
                <Button 
                  variant="ghost"
                  onClick={() => setShowFeedbackInput(false)}
                >
                  Cancel
                </Button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
