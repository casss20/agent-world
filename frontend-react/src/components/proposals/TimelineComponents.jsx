import React from 'react';

/**
 * MilestoneTimeline - Visual horizontal timeline
 * AgencyOS pattern: ProjectMilestones with steps and progress
 */
export function MilestoneTimeline({ phases = [], currentPhase = 0, className = '' }) {
  if (!phases?.length) return null;

  return (
    <nav aria-label="Progress" className={className}>
      <ol className="flex items-start w-full">
        {phases.map((phase, index) => (
          <li key={index} className="flex flex-1 relative">
            {/* Step */}
            <MilestoneStep
              name={phase.name}
              icon={phase.icon}
              description={phase.description}
              isComplete={index < currentPhase}
              isCurrent={index === currentPhase}
              date={phase.date}
              status={phase.status}
            />
            
            {/* Connector Line */}
            {index !== phases.length - 1 && (
              <div className="flex-1 mt-6 md:mt-8 px-2">
                <div 
                  className={`h-0.5 w-full rounded ${
                    index < currentPhase 
                      ? 'bg-cyan-500' 
                      : 'bg-white/10'
                  }`}
                />
              </div>
            )}
          </li>
        ))}
      </ol>
    </nav>
  );
}

function MilestoneStep({ name, icon, description, isComplete, isCurrent, date, status }) {
  const getStatusColor = () => {
    if (isComplete) return 'bg-green-500 text-white border-green-500';
    if (isCurrent) return 'bg-cyan-500 text-white border-cyan-500';
    return 'bg-white/10 text-white/40 border-white/20';
  };

  const getStatusGlow = () => {
    if (isComplete) return 'shadow-[0_0_20px_rgba(34,197,94,0.3)]';
    if (isCurrent) return 'shadow-[0_0_20px_rgba(34,211,238,0.3)] animate-pulse';
    return '';
  };

  return (
    <div className="flex flex-col items-center text-center min-w-[80px] flex-1">
      {/* Icon Circle */}
      <div 
        className={`
          w-12 h-12 md:w-14 md:h-14 rounded-full 
          flex items-center justify-center 
          border-2 transition-all duration-300
          ${getStatusColor()}
          ${getStatusGlow()}
        `}
      >
        {isComplete ? (
          <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
          </svg>
        ) : (
          <span className="text-xl md:text-2xl">{icon}</span>
        )}
      </div>
      
      {/* Label */}
      <div className="mt-3 space-y-1">
        <p className={`text-sm font-medium ${
          isCurrent ? 'text-cyan-400' : isComplete ? 'text-white' : 'text-white/40'
        }`}>
          {name}
        </p>
        
        {description && (
          <p className="text-xs text-white/30 hidden md:block max-w-[100px]">
            {description}
          </p>
        )}
        
        {date && (
          <p className={`text-xs ${
            isCurrent ? 'text-cyan-400/70' : 'text-white/30'
          }`}>
            {date}
          </p>
        )}
        
        {status && (
          <span className={`text-xs px-2 py-0.5 rounded-full ${
            isComplete ? 'bg-green-500/20 text-green-400' :
            isCurrent ? 'bg-cyan-500/20 text-cyan-400' :
            'bg-white/10 text-white/40'
          }`}>
            {status}
          </span>
        )}
      </div>
    </div>
  );
}

/**
 * StrategyTimeline - Specific implementation for strategy phases
 */
export function StrategyTimeline({ strategy, currentWeek = 1 }) {
  const defaultPhases = [
    { name: 'Setup', icon: '🚀', description: 'Tools & accounts', status: 'Setup' },
    { name: 'Create', icon: '✍️', description: 'Content production', status: 'Content' },
    { name: 'Publish', icon: '📢', description: 'Go live', status: 'Launch' },
    { name: 'Optimize', icon: '📈', description: 'Improve & scale', status: 'Growth' }
  ];

  const phases = strategy?.timeline?.weekly_breakdown?.map((week, i) => ({
    name: `Week ${week.week}`,
    icon: ['🚀', '✍️', '📢', '📈'][i] || '📋',
    description: week.focus,
    date: week.week <= currentWeek ? 'Complete' : `Week ${week.week}`,
    status: week.week <= currentWeek ? 'Done' : 'Pending'
  })) || defaultPhases;

  return (
    <div className="p-6 bg-white/5 rounded-xl border border-white/10">
      <h3 className="text-sm font-medium text-white/50 uppercase tracking-wide mb-6">
        Execution Timeline
      </h3>
      <MilestoneTimeline 
        phases={phases} 
        currentPhase={currentWeek - 1}
      />
    </div>
  );
}

/**
 * VerticalTimeline - For detailed phase breakdown
 */
export function VerticalTimeline({ items = [], className = '' }) {
  if (!items?.length) return null;

  return (
    <div className={`space-y-0 ${className}`}>
      {items.map((item, index) => (
        <div key={index} className="flex gap-4">
          {/* Timeline Line */}
          <div className="flex flex-col items-center">
            <div className={`
              w-3 h-3 rounded-full 
              ${item.isComplete ? 'bg-green-500' : 
                item.isCurrent ? 'bg-cyan-500' : 'bg-white/20'}
            `} />
            {index !== items.length - 1 && (
              <div className={`
                w-0.5 flex-1 min-h-[40px] mt-2
                ${item.isComplete ? 'bg-green-500/30' : 'bg-white/10'}
              `} />
            )}
          </div>
          
          {/* Content */}
          <div className={`
            pb-6 flex-1
            ${item.isComplete ? 'opacity-60' : ''}
          `}>
            <div className="flex items-center gap-2 mb-1">
              <span className={`
                text-sm font-medium
                ${item.isCurrent ? 'text-cyan-400' : 'text-white'}
              `}>
                {item.title}
              </span>
              {item.badge && (
                <span className={`
                  text-xs px-2 py-0.5 rounded
                  ${item.badge.variant === 'success' ? 'bg-green-500/20 text-green-400' :
                    item.badge.variant === 'warning' ? 'bg-yellow-500/20 text-yellow-400' :
                    'bg-cyan-500/20 text-cyan-400'}
                `}>
                  {item.badge.text}
                </span>
              )}
            </div>
            
            {item.description && (
              <p className="text-sm text-white/50">{item.description}</p>
            )}
            
            {item.meta && (
              <p className="text-xs text-white/30 mt-1">{item.meta}</p>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}

/**
 * CompactTimeline - For small spaces (cards, sidebars)
 */
export function CompactTimeline({ phases = [], currentPhase = 0 }) {
  return (
    <div className="flex items-center gap-1">
      {phases.map((phase, index) => (
        <React.Fragment key={index}>
          <div 
            className={`
              w-8 h-8 rounded-full flex items-center justify-center text-xs
              ${index <= currentPhase 
                ? 'bg-cyan-500 text-white' 
                : 'bg-white/10 text-white/40'}
            `}
            title={phase.name}
          >
            {index < currentPhase ? '✓' : index + 1}
          </div>
          {index !== phases.length - 1 && (
            <div className={`
              w-4 h-0.5
              ${index < currentPhase ? 'bg-cyan-500' : 'bg-white/10'}
            `} />
          )}
        </React.Fragment>
      ))}
    </div>
  );
}

/**
 * AnimatedProgressBar - Shows overall progress
 */
export function AnimatedProgressBar({ 
  progress = 0, 
  total = 100,
  label,
  showPercentage = true 
}) {
  const percentage = Math.min(100, Math.max(0, (progress / total) * 100));
  
  return (
    <div className="space-y-2">
      {(label || showPercentage) && (
        <div className="flex items-center justify-between text-sm">
          {label && <span className="text-white/70">{label}</span>}
          {showPercentage && (
            <span className="text-cyan-400 font-medium">{Math.round(percentage)}%</span>
          )}
        </div>
      )}
      
      <div className="h-2 bg-white/10 rounded-full overflow-hidden">
        <div 
          className="h-full bg-gradient-to-r from-cyan-500 to-blue-500 rounded-full transition-all duration-500 ease-out"
          style={{ width: `${percentage}%` }}
        >
          <div className="w-full h-full bg-white/20 animate-pulse" />
        </div>
      </div>
    </div>
  );
}
