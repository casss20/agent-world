import React, { useState, useEffect } from 'react';
import { useApi } from '../../hooks/useApi';
import { Button } from '../shared/Button';

const STEP_ICONS = {
  welcome: '👋',
  business_info: '🏢',
  channels: '🛒',
  channels_auth: '🔐',
  ads: '📢',
  ads_auth: '🔐',
  preferences: '⚙️',
  review: '✓',
  complete: '🎉'
};

export function SetupWizard({ businessId, onComplete }) {
  const { get, post, loading } = useApi();
  const [currentStep, setCurrentStep] = useState('welcome');
  const [stepData, setStepData] = useState({});
  const [answers, setAnswers] = useState({});
  const [progress, setProgress] = useState({ current: 1, total: 7, percentage: 0 });

  // Load current step data
  useEffect(() => {
    loadStep(currentStep);
  }, [currentStep]);

  const loadStep = async (step) => {
    const data = await get(`/setup/wizard/${businessId}/step/${step}`);
    if (data) {
      setStepData(data);
      setProgress(data.progress);
    }
  };

  const handleAnswer = (questionId, value) => {
    setAnswers(prev => ({
      ...prev,
      [questionId]: value
    }));
  };

  const handleNext = async () => {
    // Submit answers for current step
    const result = await post(`/setup/wizard/${businessId}/answer`, {
      step: currentStep,
      answers: answers
    });

    if (result) {
      setAnswers({}); // Clear for next step
      if (result.next_step === 'complete') {
        onComplete();
      } else {
        setCurrentStep(result.next_step);
      }
    }
  };

  const handleBack = async () => {
    await post(`/setup/wizard/${businessId}/back`);
    // Reload to get new step
    const progress = await get(`/setup/wizard/${businessId}`);
    if (progress) {
      setCurrentStep(progress.current_step);
    }
  };

  const canProceed = Object.keys(answers).length > 0 || stepData.questions?.length === 0;

  return (
    <div className="max-w-2xl mx-auto p-6">
      {/* Progress Bar */}
      <div className="mb-8">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm text-white/50">Setup Progress</span>
          <span className="text-sm text-cyan-400">{progress.percentage}%</span>
        </div>
        <div className="h-2 bg-white/10 rounded-full overflow-hidden">
          <div 
            className="h-full bg-gradient-to-r from-cyan-500 to-blue-500 transition-all duration-500"
            style={{ width: `${progress.percentage}%` }}
          />
        </div>
        <div className="flex justify-between mt-2 text-xs text-white/30">
          <span>Step {progress.current} of {progress.total}</span>
          <span>{STEP_ICONS[currentStep]} {stepData.title}</span>
        </div>
      </div>

      {/* Step Content */}
      <div className="bg-white/5 rounded-2xl border border-white/10 p-8">
        <div className="text-center mb-8">
          <div className="text-6xl mb-4">{STEP_ICONS[currentStep]}</div>
          <h2 className="text-2xl font-bold text-white mb-2">{stepData.title}</h2>
          <p className="text-white/60">{stepData.description}</p>
        </div>

        {/* Questions */}
        <div className="space-y-6">
          {(stepData.questions || []).map((question) => (
            <QuestionField
              key={question.id}
              question={question}
              value={answers[question.id]}
              onChange={(value) => handleAnswer(question.id, value)}
            />
          ))}
        </div>

        {/* Navigation */}
        <div className="flex gap-3 mt-8">
          {currentStep !== 'welcome' && (
            <Button onClick={handleBack} variant="secondary">
              ← Back
            </Button>
          )}
          <Button 
            onClick={handleNext} 
            loading={loading}
            disabled={!canProceed}
            className="flex-1"
          >
            {currentStep === 'review' ? 'Complete Setup →' : 'Continue →'}
          </Button>
        </div>
      </div>
    </div>
  );
}

function QuestionField({ question, value, onChange }) {
  const { id, type, label, placeholder, required, help, options } = question;

  const renderInput = () => {
    switch (type) {
      case 'text':
      case 'email':
        return (
          <input
            type={type}
            value={value || ''}
            onChange={(e) => onChange(e.target.value)}
            placeholder={placeholder}
            className="w-full px-4 py-3 bg-white/5 border border-white/20 rounded-xl text-white placeholder-white/30 focus:border-cyan-500/50 focus:outline-none"
          />
        );
      
      case 'select':
        return (
          <select
            value={value || ''}
            onChange={(e) => onChange(e.target.value)}
            className="w-full px-4 py-3 bg-white/5 border border-white/20 rounded-xl text-white focus:border-cyan-500/50 focus:outline-none"
          >
            <option value="" className="bg-gray-900">Select...</option>
            {options?.map((opt) => (
              <option key={opt.value} value={opt.value} className="bg-gray-900">
                {opt.label}
              </option>
            ))}
          </select>
        );
      
      case 'toggle':
        return (
          <button
            onClick={() => onChange(!value)}
            className={`w-full p-4 rounded-xl border text-left transition-all ${
              value 
                ? 'bg-cyan-500/20 border-cyan-500/50' 
                : 'bg-white/5 border-white/20 hover:border-white/40'
            }`}
          >
            <div className="flex items-center justify-between">
              <div>
                <div className="font-medium text-white">{label}</div>
                <div className="text-sm text-white/50">{question.description}</div>
              </div>
              <div className={`w-12 h-6 rounded-full p-1 transition-colors ${
                value ? 'bg-cyan-500' : 'bg-white/20'
              }`}>
                <div className={`w-4 h-4 rounded-full bg-white transition-transform ${
                  value ? 'translate-x-6' : 'translate-x-0'
                }`} />
              </div>
            </div>
          </button>
        );
      
      case 'number':
        return (
          <input
            type="number"
            value={value || ''}
            onChange={(e) => onChange(parseFloat(e.target.value))}
            placeholder={placeholder}
            className="w-full px-4 py-3 bg-white/5 border border-white/20 rounded-xl text-white placeholder-white/30 focus:border-cyan-500/50 focus:outline-none"
          />
        );
      
      case 'oauth_button':
        return (
          <button
            onClick={() => window.open(question.oauth_url, '_blank')}
            className="w-full py-3 bg-gradient-to-r from-blue-500 to-cyan-500 rounded-xl text-white font-medium hover:opacity-90 transition-opacity"
          >
            {label} →
          </button>
        );
      
      default:
        return null;
    }
  };

  if (type === 'toggle') {
    return renderInput();
  }

  return (
    <div>
      <label className="block text-sm font-medium text-white mb-2">
        {label}
        {required && <span className="text-red-400 ml-1">*</span>}
      </label>
      {renderInput()}
      {help && (
        <p className="mt-2 text-sm text-white/40">{help}</p>
      )}
    </div>
  );
}
