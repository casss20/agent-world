import { useState } from 'react';
import { Button } from '../shared/Button';
import { useApi } from '../../hooks/useApi';

const PROVIDER_INFO = {
  dalle_3: {
    name: 'DALL-E 3',
    description: 'Best quality, understands prompts well, decent text rendering',
    cost: '$0.06',
    time: '10s',
    bestFor: ['Premium products', 'Illustrations', 'Text-heavy designs'],
    color: 'from-green-500 to-emerald-600'
  },
  nano_banana: {
    name: 'Nano Banana',
    description: 'Fast, cheap, good for rapid prototyping and volume',
    cost: '$0.01',
    time: '3s',
    bestFor: ['Thumbnails', 'Bulk generation', 'Rapid testing'],
    color: 'from-yellow-500 to-orange-500'
  },
  stable_diffusion: {
    name: 'Stable Diffusion',
    description: 'Self-hosted, cheapest option for high volume',
    cost: '$0.001',
    time: '5s',
    bestFor: ['High volume', 'Custom models', 'Privacy-sensitive'],
    color: 'from-blue-500 to-cyan-500'
  },
  canva_api: {
    name: 'Canva API',
    description: 'Templates + PDF export. Perfect for planners & workbooks',
    cost: 'FREE',
    time: '8s',
    bestFor: ['PDF planners', 'Workbooks', 'Structured layouts'],
    color: 'from-purple-500 to-pink-500'
  },
  manual_upload: {
    name: 'Manual Upload',
    description: 'You create in your preferred tool, upload to system',
    cost: 'FREE',
    time: 'Variable',
    bestFor: ['Maximum control', 'Complex designs', 'Existing assets'],
    color: 'from-gray-500 to-slate-600'
  }
};

export function DesignProviderSelector({ 
  designRequest, 
  onProviderSelected, 
  onGenerate 
}) {
  const { get, post, loading } = useApi();
  const [providers, setProviders] = useState([]);
  const [selectedProvider, setSelectedProvider] = useState(null);
  const [previewMode, setPreviewMode] = useState(true);
  const [step, setStep] = useState('select'); // select → preview → confirm → generating → done

  // Load providers on mount
  useState(() => {
    loadProviders();
  }, []);

  const loadProviders = async () => {
    const data = await get(`/design/providers?design_type=${designRequest.design_type}`);
    if (data) {
      setProviders(data);
    }
  };

  const handleSelectProvider = (providerType) => {
    setSelectedProvider(providerType);
    setStep('preview');
  };

  const handleGeneratePreview = async () => {
    setStep('generating');
    
    const result = await post('/design/generate', {
      ...designRequest,
      preferred_provider: selectedProvider,
      num_variants: 1 // Preview = 1 image
    });

    if (result) {
      if (result.status === 'preview_generated') {
        setStep('confirm');
        // Show preview, wait for approval
      } else {
        setStep('done');
        onGenerate(result);
      }
    }
  };

  const handleConfirmFullGeneration = async () => {
    setStep('generating');
    
    const result = await post('/design/generate/approve', {
      preview_token: 'placeholder',
      approve: true,
      selected_provider: selectedProvider
    });

    if (result) {
      setStep('done');
      onGenerate(result);
    }
  };

  // Step 1: Select Provider
  if (step === 'select') {
    return (
      <div className="max-w-4xl mx-auto p-6">
        <h2 className="text-2xl font-bold text-white mb-2">
          Choose Design Provider
        </h2>
        <p className="text-white/50 mb-6">
          Select how to generate your {designRequest.design_type}
        </p>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {providers.map((provider) => {
            const info = PROVIDER_INFO[provider.type] || {};
            const isRecommended = provider.recommended;
            
            return (
              <button
                key={provider.type}
                onClick={() => handleSelectProvider(provider.type)}
                className={`p-5 rounded-xl border text-left transition-all relative ${
                  isRecommended 
                    ? 'border-cyan-400 bg-cyan-500/10' 
                    : 'border-white/10 hover:border-white/30'
                }`}
              >
                {isRecommended && (
                  <span className="absolute -top-2 left-4 bg-cyan-500 text-white text-xs px-2 py-1 rounded-full">
                    Recommended
                  </span>
                )}
                
                <div className={`w-10 h-10 rounded-lg bg-gradient-to-br ${info.color} mb-3 flex items-center justify-center`}>
                  <span className="text-white font-bold text-sm">
                    {provider.type[0].toUpperCase()}
                  </span>
                </div>
                
                <h3 className="font-bold text-white mb-1">{info.name || provider.display_name}</h3>
                <p className="text-sm text-white/60 mb-3">{info.description || provider.description}</p>
                
                <div className="flex items-center gap-4 text-sm">
                  <span className="text-green-400">{info.cost || `$${provider.cost_per_image}`}</span>
                  <span className="text-white/40">|</span>
                  <span className="text-white/60">{info.time || `${provider.generation_time_seconds}s`}</span>
                </div>
                
                {info.bestFor && (
                  <div className="mt-3 flex flex-wrap gap-1">
                    {info.bestFor.map((use) => (
                      <span key={use} className="text-xs bg-white/10 text-white/70 px-2 py-0.5 rounded">
                        {use}
                      </span>
                    ))}
                  </div>
                )}
              </button>
            );
          })}
        </div>

        <div className="mt-6 p-4 bg-white/5 rounded-lg border border-white/10">
          <h4 className="text-sm font-medium text-white mb-2">Design Request</h4>
          <p className="text-sm text-white/60">{designRequest.prompt}</p>
          <div className="mt-2 flex gap-2 text-xs text-white/40">
            <span>{designRequest.width}×{designRequest.height}px</span>
            <span>•</span>
            <span>{designRequest.num_variants} variant{designRequest.num_variants > 1 ? 's' : ''}</span>
          </div>
        </div>
      </div>
    );
  }

  // Step 2: Preview
  if (step === 'preview') {
    const info = PROVIDER_INFO[selectedProvider];
    
    return (
      <div className="max-w-2xl mx-auto p-6 text-center">
        <h2 className="text-2xl font-bold text-white mb-4">
          Generate Preview with {info?.name}
        </h2>
        
        <div className="p-6 bg-white/5 rounded-xl border border-white/10 mb-6">
          <div className={`w-16 h-16 rounded-xl bg-gradient-to-br ${info?.color} mx-auto mb-4`} />
          
          <p className="text-white/70 mb-4">
            We'll generate a <strong>low-cost preview</strong> (1 variant, lower resolution) 
            so you can approve before spending on full generation.
          </p>
          
          <div className="grid grid-cols-3 gap-4 text-sm mb-4">
            <div className="p-3 bg-white/5 rounded">
              <div className="text-white font-medium">{info?.cost}</div>
              <div className="text-white/50">per image</div>
            </div>
            <div className="p-3 bg-white/5 rounded">
              <div className="text-white font-medium">{info?.time}</div>
              <div className="text-white/50">generation time</div>
            </div>
            <div className="p-3 bg-white/5 rounded">
              <div className="text-white font-medium">~${((designRequest.num_variants || 1) * parseFloat(info?.cost?.replace('$', '') || 0)).toFixed(2)}</div>
              <div className="text-white/50">estimated total</div>
            </div>
          </div>
        </div>

        <div className="flex gap-3">
          <Button variant="secondary" onClick={() => setStep('select')}>
            ← Choose Different Provider
          </Button>
          <Button onClick={handleGeneratePreview} loading={loading} className="flex-1">
            Generate Preview →
          </Button>
        </div>
      </div>
    );
  }

  // Step 3: Generating
  if (step === 'generating') {
    return (
      <div className="max-w-2xl mx-auto p-6 text-center">
        <div className="animate-spin w-12 h-12 border-4 border-cyan-400 border-t-transparent rounded-full mx-auto mb-4" />
        <h2 className="text-xl font-bold text-white mb-2">Generating...</h2>
        <p className="text-white/50">
          Using {PROVIDER_INFO[selectedProvider]?.name}. This takes {PROVIDER_INFO[selectedProvider]?.time}.
        </p>
      </div>
    );
  }

  // Step 4: Done
  if (step === 'done') {
    return (
      <div className="max-w-2xl mx-auto p-6 text-center">
        <div className="w-16 h-16 bg-green-500/20 rounded-full flex items-center justify-center mx-auto mb-4">
          <span className="text-3xl">✅</span>
        </div>
        <h2 className="text-xl font-bold text-white mb-2">Design Generated!</h2>
        <p className="text-white/50 mb-6">
          Your design has been created using {PROVIDER_INFO[selectedProvider]?.name}.
        </p>
        <Button onClick={() => setStep('select')} variant="secondary">
          Generate Another
        </Button>
      </div>
    );
  }

  return null;
}
