import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '../components/shared/Button';
import { FormInput, FormSelect, FormTextarea } from '../components/shared/FormComponents';
import { useApi } from '../hooks/useApi';

const BUSINESS_MODELS = [
  { id: 'etsy_pod', name: 'Etsy Print-on-Demand', icon: '🏪' },
  { id: 'shopify_brand', name: 'Shopify Brand', icon: '🛍️' },
  { id: 'tiktok_account', name: 'TikTok Creator', icon: '📱' },
  { id: 'service_business', name: 'Service Business', icon: '💼' },
  { id: 'personal_brand', name: 'Personal Brand', icon: '⭐' },
];

const STAGES = [
  { id: 'ideation', name: 'Ideation', description: 'Validating idea' },
  { id: 'traction', name: 'Traction', description: 'Some sales, finding product-market fit' },
  { id: 'growth', name: 'Growth', description: 'Working model, scaling up' },
  { id: 'optimization', name: 'Optimization', description: 'Mature, improving efficiency' },
];

const SKILL_OPTIONS = [
  'design', 'copywriting', 'video_editing', 'ads', 'seo', 
  'social_media', 'email_marketing', 'sales', 'development'
];

export function BusinessIntakeWizard() {
  const navigate = useNavigate();
  const { post, loading, error } = useApi();
  const [step, setStep] = useState(1);
  const [formData, setFormData] = useState({
    business_model: '',
    stage: '',
    goals: { revenue_target: '', audience_target: '', timeline: '' },
    available_hours: 10,
    available_budget: 500,
    team_size: 1,
    skills: [],
    current_metrics: {},
    channels: [],
    notes: ''
  });

  const updateField = (field, value) => {
    setFormData(prev => ({ ...prev, [field]: value }));
  };

  const updateGoal = (goal, value) => {
    setFormData(prev => ({
      ...prev,
      goals: { ...prev.goals, [goal]: value }
    }));
  };

  const updateMetrics = (metric, value) => {
    setFormData(prev => ({
      ...prev,
      current_metrics: { ...prev.current_metrics, [metric]: value }
    }));
  };

  const toggleSkill = (skill) => {
    setFormData(prev => ({
      ...prev,
      skills: prev.skills.includes(skill)
        ? prev.skills.filter(s => s !== skill)
        : [...prev.skills, skill]
    }));
  };

  const handleSubmit = async () => {
    const response = await post('/diagnostics/intake', formData);
    if (response?.business_id) {
      navigate(`/diagnosis/run/${response.business_id}`);
    }
  };

  const canProceed = () => {
    switch (step) {
      case 1: return formData.business_model && formData.stage;
      case 2: return formData.goals.revenue_target;
      case 3: return true; // Resources always have defaults
      case 4: return true; // Metrics optional
      case 5: return true; // Review step
      default: return false;
    }
  };

  return (
    <div className="max-w-2xl mx-auto p-6">
      {/* Progress */}
      <div className="mb-8">
        <div className="flex items-center gap-2 mb-4">
          {[1, 2, 3, 4, 5].map(s => (
            <div
              key={s}
              className={`h-2 flex-1 rounded-full transition-colors ${
                s <= step ? 'bg-cyan-400' : 'bg-white/10'
              }`}
            />
          ))}
        </div>
        <p className="text-white/50 text-sm">
          Step {step} of 5: {
            step === 1 ? 'Business Type' :
            step === 2 ? 'Goals' :
            step === 3 ? 'Resources' :
            step === 4 ? 'Current Metrics' :
            'Review'
          }
        </p>
      </div>

      {/* Error */}
      {error && (
        <div className="mb-4 p-4 bg-red-500/10 border border-red-500/30 rounded-lg text-red-300">
          {error}
        </div>
      )}

      {/* Step 1: Business Model & Stage */}
      {step === 1 && (
        <div className="space-y-6">
          <h2 className="text-2xl font-bold text-white mb-6">What type of business?</h2>
          
          <div className="grid grid-cols-2 gap-3">
            {BUSINESS_MODELS.map(model => (
              <button
                key={model.id}
                onClick={() => updateField('business_model', model.id)}
                className={`p-4 rounded-xl border transition-all text-left ${
                  formData.business_model === model.id
                    ? 'border-cyan-400 bg-cyan-500/10'
                    : 'border-white/10 hover:border-white/30'
                }`}
              >
                <span className="text-2xl mb-2 block">{model.icon}</span>
                <span className="text-white font-medium">{model.name}</span>
              </button>
            ))}
          </div>

          <div className="mt-8">
            <h3 className="text-lg font-medium text-white mb-4">What stage are you in?</h3>
            <div className="space-y-3">
              {STAGES.map(stage => (
                <button
                  key={stage.id}
                  onClick={() => updateField('stage', stage.id)}
                  className={`w-full p-4 rounded-xl border transition-all text-left ${
                    formData.stage === stage.id
                      ? 'border-cyan-400 bg-cyan-500/10'
                      : 'border-white/10 hover:border-white/30'
                  }`}
                >
                  <span className="text-white font-medium block">{stage.name}</span>
                  <span className="text-white/50 text-sm">{stage.description}</span>
                </button>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Step 2: Goals */}
      {step === 2 && (
        <div className="space-y-6">
          <h2 className="text-2xl font-bold text-white mb-6">What are you trying to achieve?</h2>
          
          <FormInput
            label="Revenue Target (monthly)"
            type="text"
            placeholder="e.g., $5,000"
            value={formData.goals.revenue_target}
            onChange={e => updateGoal('revenue_target', e.target.value)}
          />

          <FormInput
            label="Audience/Target Size"
            type="text"
            placeholder="e.g., 10,000 followers, 500 customers"
            value={formData.goals.audience_target}
            onChange={e => updateGoal('audience_target', e.target.value)}
          />

          <FormSelect
            label="Timeline"
            value={formData.goals.timeline}
            onChange={e => updateGoal('timeline', e.target.value)}
            options={[
              { value: '', label: 'Select timeline...' },
              { value: '30_days', label: '30 days' },
              { value: '90_days', label: '90 days' },
              { value: '6_months', label: '6 months' },
              { value: '1_year', label: '1 year' },
            ]}
          />
        </div>
      )}

      {/* Step 3: Resources */}
      {step === 3 && (
        <div className="space-y-6">
          <h2 className="text-2xl font-bold text-white mb-6">What resources do you have?</h2>
          
          <div className="grid grid-cols-2 gap-4">
            <FormInput
              label="Hours per week"
              type="number"
              value={formData.available_hours}
              onChange={e => updateField('available_hours', parseInt(e.target.value))}
            />
            <FormInput
              label="Monthly budget ($)"
              type="number"
              value={formData.available_budget}
              onChange={e => updateField('available_budget', parseInt(e.target.value))}
            />
          </div>

          <FormInput
            label="Team size (including you)"
            type="number"
            value={formData.team_size}
            onChange={e => updateField('team_size', parseInt(e.target.value))}
          />

          <div>
            <label className="block text-sm font-medium text-white/70 mb-3">Skills available</label>
            <div className="flex flex-wrap gap-2">
              {SKILL_OPTIONS.map(skill => (
                <button
                  key={skill}
                  onClick={() => toggleSkill(skill)}
                  className={`px-3 py-1.5 rounded-full text-sm transition-colors ${
                    formData.skills.includes(skill)
                      ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/30'
                      : 'bg-white/5 text-white/50 border border-white/10 hover:border-white/30'
                  }`}
                >
                  {skill.replace('_', ' ')}
                </button>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Step 4: Current Metrics (Etsy POD) */}
      {step === 4 && formData.business_model === 'etsy_pod' && (
        <div className="space-y-6">
          <h2 className="text-2xl font-bold text-white mb-6">Current Etsy metrics (optional)</h2>
          
          <div className="grid grid-cols-2 gap-4">
            <FormInput
              label="Active listings"
              type="number"
              placeholder="0"
              onChange={e => updateMetrics('listing_count', parseInt(e.target.value) || 0)}
            />
            <FormInput
              label="Monthly revenue ($)"
              type="number"
              placeholder="0"
              onChange={e => updateMetrics('revenue', parseInt(e.target.value) || 0)}
            />
            <FormInput
              label="Click-through rate (%)"
              type="number"
              step="0.1"
              placeholder="e.g., 2.5"
              onChange={e => updateMetrics('click_through_rate', parseFloat(e.target.value) / 100 || 0)}
            />
            <FormInput
              label="Conversion rate (%)"
              type="number"
              step="0.1"
              placeholder="e.g., 1.5"
              onChange={e => updateMetrics('conversion_rate', parseFloat(e.target.value) / 100 || 0)}
            />
          </div>

          <FormInput
            label="Primary niche"
            type="text"
            placeholder="e.g., pet memorial gifts"
            onChange={e => updateMetrics('primary_niche', e.target.value)}
          />

          <FormTextarea
            label="Any specific challenges or notes?"
            placeholder="What's your biggest frustration right now?"
            value={formData.notes}
            onChange={e => updateField('notes', e.target.value)}
          />
        </div>
      )}

      {/* Step 4: Generic (non-Etsy) */}
      {step === 4 && formData.business_model !== 'etsy_pod' && (
        <div className="space-y-6">
          <h2 className="text-2xl font-bold text-white mb-6">Current metrics (optional)</h2>
          
          <FormTextarea
            label="Describe your current situation"
            placeholder="What's working? What's not? What have you tried?"
            value={formData.notes}
            onChange={e => updateField('notes', e.target.value)}
          />
        </div>
      )}

      {/* Step 5: Review */}
      {step === 5 && (
        <div className="space-y-6">
          <h2 className="text-2xl font-bold text-white mb-6">Review your business profile</h2>
          
          <div className="space-y-4 p-4 bg-white/5 rounded-xl border border-white/10">
            <ReviewItem label="Business Model" value={BUSINESS_MODELS.find(m => m.id === formData.business_model)?.name} />
            <ReviewItem label="Stage" value={STAGES.find(s => s.id === formData.stage)?.name} />
            <ReviewItem label="Revenue Goal" value={formData.goals.revenue_target} />
            <ReviewItem label="Hours/Week" value={`${formData.available_hours} hours`} />
            <ReviewItem label="Budget" value={`$${formData.available_budget}/month`} />
            <ReviewItem label="Skills" value={formData.skills.join(', ') || 'None selected'} />
          </div>

          <p className="text-white/50 text-sm">
            We'll analyze your business to identify the main bottleneck and recommend the highest-leverage next steps.
          </p>
        </div>
      )}

      {/* Navigation */}
      <div className="flex gap-3 mt-8">
        {step > 1 && (
          <Button variant="secondary" onClick={() => setStep(s => s - 1)}>
            Back
          </Button>
        )}
        
        {step < 5 ? (
          <Button 
            onClick={() => setStep(s => s + 1)} 
            disabled={!canProceed()}
            className="flex-1"
          >
            Continue
          </Button>
        ) : (
          <Button 
            onClick={handleSubmit} 
            loading={loading}
            className="flex-1"
          >
            Start Diagnosis →
          </Button>
        )}
      </div>
    </div>
  );
}

function ReviewItem({ label, value }) {
  return (
    <div className="flex justify-between">
      <span className="text-white/50">{label}</span>
      <span className="text-white font-medium">{value || '—'}</span>
    </div>
  );
}