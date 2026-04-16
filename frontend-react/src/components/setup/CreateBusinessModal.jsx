import React, { useState } from 'react';
import { Button } from '../shared/Button';

export function CreateBusinessModal({ onClose, onCreate }) {
  const [step, setStep] = useState('input'); // input, creating, success
  const [businessInput, setBusinessInput] = useState('');
  const [parsedBusiness, setParsedBusiness] = useState(null);

  const handleParse = async () => {
    setStep('creating');
    
    // In real implementation, this would call an API to parse/validate
    // For now, simulate parsing
    await new Promise(r => setTimeout(r, 1500));
    
    const parsed = {
      name: businessInput.slice(0, 30) || "New Business",
      source: businessInput.startsWith('http') ? 'link' : 'text',
      raw_input: businessInput
    };
    
    setParsedBusiness(parsed);
    setStep('success');
  };

  const handleCreate = () => {
    onCreate(parsedBusiness);
    onClose();
  };

  if (step === 'creating') {
    return (
      <div className="p-8 text-center">
        <div className="animate-spin w-12 h-12 border-4 border-cyan-400 border-t-transparent rounded-full mx-auto mb-4" />
        <p className="text-white/70">Analyzing your business idea...</p>
        <p className="text-sm text-white/50 mt-2">This may take a moment</p>
      </div>
    );
  }

  if (step === 'success') {
    return (
      <div className="p-6">
        <div className="text-center mb-6">
          <div className="text-5xl mb-3">✨</div>
          <h3 className="text-xl font-bold text-white mb-2">Business Idea Detected!</h3>
          <p className="text-white/60">We found potential in your input. Ready to set it up?</p>
        </div>

        <div className="bg-white/5 rounded-xl p-4 mb-6 border border-white/10">
          <div className="text-sm text-white/50 mb-1">Business Name</div>
          <div className="font-medium text-white">{parsedBusiness.name}</div>
          
          {parsedBusiness.source === 'link' && (
            <>
              <div className="text-sm text-white/50 mt-3 mb-1">Source</div>
              <div className="font-mono text-xs text-cyan-400 truncate">{parsedBusiness.raw_input}</div>
            </>
          )}
        </div>

        <div className="space-y-3">
          <Button onClick={handleCreate} className="w-full">
            Start Setup Wizard →
          </Button>
          <Button onClick={onClose} variant="secondary" className="w-full">
            Cancel
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6">
      <h3 className="text-xl font-bold text-white mb-2">Create New Business</h3>
      <p className="text-white/60 mb-6">
        Paste a link, describe your idea, or just give it a name.
      </p>

      <textarea
        value={businessInput}
        onChange={(e) => setBusinessInput(e.target.value)}
        placeholder="Examples:
• https://example.com/my-product
• Children's book about space exploration
• Digital planner for ADHD adults"
        rows={5}
        className="w-full px-4 py-3 bg-white/5 border border-white/20 rounded-xl text-white placeholder-white/30 focus:border-cyan-500/50 focus:outline-none resize-none"
      />

      <div className="flex gap-3 mt-6">
        <Button onClick={onClose} variant="secondary">
          Cancel
        </Button>
        <Button 
          onClick={handleParse} 
          disabled={!businessInput.trim()}
          className="flex-1"
        >
          Analyze & Continue →
        </Button>
      </div>
    </div>
  );
}
