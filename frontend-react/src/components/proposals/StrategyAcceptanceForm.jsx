import React, { useState, useRef, useCallback } from 'react';
import { Button } from '../shared/Button';
import { FormInput, FormCheckbox } from '../shared/FormComponents';

/**
 * SignaturePad - Canvas-based signature drawing
 * AgencyOS pattern: type/draw/upload options
 */
export function SignaturePad({ onChange, value }) {
  const canvasRef = useRef(null);
  const [isDrawing, setIsDrawing] = useState(false);
  const [hasSignature, setHasSignature] = useState(false);

  const startDrawing = useCallback((e) => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    
    const ctx = canvas.getContext('2d');
    const rect = canvas.getBoundingClientRect();
    const x = (e.clientX || e.touches?.[0]?.clientX) - rect.left;
    const y = (e.clientY || e.touches?.[0]?.clientY) - rect.top;
    
    ctx.beginPath();
    ctx.moveTo(x, y);
    setIsDrawing(true);
    setHasSignature(true);
  }, []);

  const draw = useCallback((e) => {
    if (!isDrawing) return;
    
    const canvas = canvasRef.current;
    if (!canvas) return;
    
    const ctx = canvas.getContext('2d');
    const rect = canvas.getBoundingClientRect();
    const x = (e.clientX || e.touches?.[0]?.clientX) - rect.left;
    const y = (e.clientY || e.touches?.[0]?.clientY) - rect.top;
    
    ctx.lineTo(x, y);
    ctx.strokeStyle = '#22d3ee';
    ctx.lineWidth = 2;
    ctx.lineCap = 'round';
    ctx.stroke();
  }, [isDrawing]);

  const stopDrawing = useCallback(() => {
    if (!isDrawing) return;
    setIsDrawing(false);
    
    const canvas = canvasRef.current;
    if (canvas && onChange) {
      onChange({
        type: 'draw',
        dataUrl: canvas.toDataURL('image/png')
      });
    }
  }, [isDrawing, onChange]);

  const clear = () => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    
    const ctx = canvas.getContext('2d');
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    setHasSignature(false);
    onChange(null);
  };

  return (
    <div className="space-y-2">
      <div className="relative">
        <canvas
          ref={canvasRef}
          width={400}
          height={150}
          className="w-full h-[150px] bg-white/5 border border-white/10 rounded-lg cursor-crosshair touch-none"
          onMouseDown={startDrawing}
          onMouseMove={draw}
          onMouseUp={stopDrawing}
          onMouseLeave={stopDrawing}
          onTouchStart={startDrawing}
          onTouchMove={draw}
          onTouchEnd={stopDrawing}
        />
        
        {!hasSignature && (
          <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
            <span className="text-white/20 text-sm">Draw your signature here</span>
          </div>
        )}
      </div>
      
      <div className="flex justify-end">
        <button 
          onClick={clear}
          className="text-xs text-white/50 hover:text-white transition-colors"
        >
          Clear
        </button>
      </div>
    </div>
  );
}

/**
 * SignatureType - Text-based signature input
 */
export function SignatureType({ onChange, value }) {
  const [text, setText] = useState(value?.text || '');
  const [font, setFont] = useState('cursive');

  const fonts = [
    { id: 'cursive', name: 'Cursive', style: 'font-family: cursive' },
    { id: 'serif', name: 'Serif', style: 'font-family: serif' },
    { id: 'sans-serif', name: 'Sans-serif', style: 'font-family: sans-serif' }
  ];

  const handleChange = (newText) => {
    setText(newText);
    onChange({
      type: 'type',
      text: newText,
      font
    });
  };

  return (
    <div className="space-y-4">
      <div className="p-6 bg-white/5 border border-white/10 rounded-lg min-h-[100px] flex items-center justify-center">
        <span 
          className="text-2xl text-cyan-400"
          style={{ fontFamily: font }}
        >
          {text || 'Your signature will appear here'}
        </span>
      </div>
      
      <FormInput
        label="Type your full name"
        value={text}
        onChange={handleChange}
        placeholder="John Doe"
      />
      
      <div className="flex gap-2">
        {fonts.map((f) => (
          <button
            key={f.id}
            onClick={() => setFont(f.id)}
            className={`px-3 py-1 rounded text-sm transition-colors ${
              font === f.id 
                ? 'bg-cyan-500/20 text-cyan-400 border border-cyan-500/50' 
                : 'bg-white/5 text-white/60 hover:bg-white/10'
            }`}
            style={{ fontFamily: f.id }}
          >
            {f.name}
          </button>
        ))}
      </div>
    </div>
  );
}

/**
 * SignatureUpload - File upload for signature image
 */
export function SignatureUpload({ onChange, value }) {
  const [preview, setPreview] = useState(value?.preview || null);
  const inputRef = useRef(null);

  const handleFileChange = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (event) => {
      setPreview(event.target.result);
      onChange({
        type: 'upload',
        file,
        preview: event.target.result
      });
    };
    reader.readAsDataURL(file);
  };

  const clear = () => {
    setPreview(null);
    onChange(null);
    if (inputRef.current) {
      inputRef.current.value = '';
    }
  };

  return (
    <div className="space-y-4">
      {preview ? (
        <div className="relative">
          <img 
            src={preview} 
            alt="Signature preview" 
            className="w-full h-[150px] object-contain bg-white/5 border border-white/10 rounded-lg p-4"
          />
          <button
            onClick={clear}
            className="absolute top-2 right-2 p-1 bg-red-500/20 text-red-400 rounded hover:bg-red-500/30 transition-colors"
          >
            ✕
          </button>
        </div>
      ) : (
        <div 
          onClick={() => inputRef.current?.click()}
          className="h-[150px] border-2 border-dashed border-white/20 rounded-lg flex flex-col items-center justify-center cursor-pointer hover:border-cyan-500/30 transition-colors"
        >
          <span className="text-3xl mb-2">📤</span>
          <span className="text-sm text-white/50">Click to upload signature image</span>
          <span className="text-xs text-white/30">PNG, JPG up to 2MB</span>
        </div>
      )}
      
      <input
        ref={inputRef}
        type="file"
        accept="image/png,image/jpeg"
        onChange={handleFileChange}
        className="hidden"
      />
    </div>
  );
}

/**
 * StrategyAcceptanceForm - Full e-signature form
 * AgencyOS pattern: Form validation + e-signature + acknowledgment
 */
export function StrategyAcceptanceForm({ 
  strategy, 
  business,
  onSubmit,
  onCancel,
  loading = false,
  prefillData = {}
}) {
  const [formData, setFormData] = useState({
    first_name: prefillData.first_name || '',
    last_name: prefillData.last_name || '',
    email: prefillData.email || '',
    organization: prefillData.organization || business?.name || '',
    signature: null,
    acknowledgment: false,
    signature_method: 'draw' // 'draw' | 'type' | 'upload'
  });

  const [errors, setErrors] = useState({});

  const validate = () => {
    const newErrors = {};
    
    if (!formData.first_name?.trim()) {
      newErrors.first_name = 'First name is required';
    }
    if (!formData.last_name?.trim()) {
      newErrors.last_name = 'Last name is required';
    }
    if (!formData.email?.trim()) {
      newErrors.email = 'Email is required';
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email)) {
      newErrors.email = 'Please enter a valid email';
    }
    if (!formData.signature) {
      newErrors.signature = 'Signature is required';
    }
    if (!formData.acknowledgment) {
      newErrors.acknowledgment = 'You must agree to the electronic signature terms';
    }
    
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (validate()) {
      onSubmit(formData);
    }
  };

  const updateField = (field, value) => {
    setFormData(prev => ({ ...prev, [field]: value }));
    if (errors[field]) {
      setErrors(prev => ({ ...prev, [field]: null }));
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      {/* Header */}
      <div className="text-center space-y-2">
        <div className="inline-flex items-center justify-center w-12 h-12 rounded-full bg-cyan-500/20 mb-2">
          <span className="text-2xl">✓</span>
        </div>
        <h2 className="text-xl font-bold text-white">Accept Strategy</h2>
        <p className="text-white/60 text-sm">
          To accept <strong>{strategy?.primary_strategy?.name}</strong>, fill out the form below.
        </p>
      </div>

      {/* Name Fields */}
      <div className="grid grid-cols-2 gap-4">
        <FormInput
          label="First Name"
          value={formData.first_name}
          onChange={(v) => updateField('first_name', v)}
          placeholder="John"
          required
          error={errors.first_name}
        />
        <FormInput
          label="Last Name"
          value={formData.last_name}
          onChange={(v) => updateField('last_name', v)}
          placeholder="Doe"
          required
          error={errors.last_name}
        />
      </div>

      {/* Email */}
      <FormInput
        label="Email"
        type="email"
        value={formData.email}
        onChange={(v) => updateField('email', v)}
        placeholder="john@example.com"
        required
        error={errors.email}
      />

      {/* Organization */}
      <FormInput
        label="Company / Organization"
        value={formData.organization}
        onChange={(v) => updateField('organization', v)}
        placeholder="Acme Inc"
      />

      {/* Signature Method Tabs */}
      <div>
        <label className="text-sm font-medium text-white/70 mb-2 block">
          Signature <span className="text-red-400">*</span>
        </label>
        
        <div className="flex gap-2 mb-4">
          {[
            { id: 'draw', label: 'Draw', icon: '✍️' },
            { id: 'type', label: 'Type', icon: '⌨️' },
            { id: 'upload', label: 'Upload', icon: '📤' }
          ].map((method) => (
            <button
              key={method.id}
              type="button"
              onClick={() => updateField('signature_method', method.id)}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm transition-colors ${
                formData.signature_method === method.id
                  ? 'bg-cyan-500/20 text-cyan-400 border border-cyan-500/50'
                  : 'bg-white/5 text-white/60 hover:bg-white/10'
              }`}
            >
              <span>{method.icon}</span>
              {method.label}
            </button>
          ))}
        </div>

        {/* Signature Input Based on Method */}
        <div className="p-4 bg-white/5 border border-white/10 rounded-xl">
          {formData.signature_method === 'draw' && (
            <SignaturePad 
              value={formData.signature}
              onChange={(sig) => updateField('signature', sig)}
            />
          )}
          {formData.signature_method === 'type' && (
            <SignatureType 
              value={formData.signature}
              onChange={(sig) => updateField('signature', sig)}
            />
          )}
          {formData.signature_method === 'upload' && (
            <SignatureUpload 
              value={formData.signature}
              onChange={(sig) => updateField('signature', sig)}
            />
          )}
        </div>
        
        {errors.signature && (
          <p className="text-red-400 text-sm mt-2">{errors.signature}</p>
        )}
      </div>

      {/* Acknowledgment */}
      <FormCheckbox
        label="I agree that my electronic signature is as valid and legally binding as a handwritten signature."
        checked={formData.acknowledgment}
        onChange={(v) => updateField('acknowledgment', v)}
        required
        error={errors.acknowledgment}
      />

      {/* Actions */}
      <div className="flex gap-3 pt-4 border-t border-white/10">
        <Button 
          type="submit"
          loading={loading}
          className="flex-1"
        >
          ✓ Accept Strategy
        </Button>
        <Button 
          type="button"
          variant="ghost"
          onClick={onCancel}
          disabled={loading}
        >
          Cancel
        </Button>
      </div>
    </form>
  );
}

/**
 * FormCheckbox - Checkbox with label and error state
 */
function FormCheckbox({ label, checked, onChange, required, error }) {
  return (
    <div className="space-y-2">
      <label className="flex items-start gap-3 cursor-pointer">
        <input
          type="checkbox"
          checked={checked}
          onChange={(e) => onChange(e.target.checked)}
          required={required}
          className="mt-1 w-4 h-4 rounded border-white/20 bg-white/5 text-cyan-500 focus:ring-cyan-500/50"
        />
        <span className="text-sm text-white/70">
          {label}
          {required && <span className="text-red-400 ml-1">*</span>}
        </span>
      </label>
      {error && (
        <p className="text-red-400 text-sm ml-7">{error}</p>
      )}
    </div>
  );
}
