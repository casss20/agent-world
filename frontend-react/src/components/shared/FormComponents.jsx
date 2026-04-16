import React from 'react';

export function FormInput({ label, value, onChange, type = 'text', placeholder, required }) {
  return (
    <div className="space-y-2">
      {label && (
        <label className="text-sm font-medium text-white/70">
          {label}
          {required && <span className="text-red-400 ml-1">*</span>}
        </label>
      )}
      <input
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        required={required}
        className="w-full px-4 py-2 bg-white/5 border border-white/10 rounded-lg text-white placeholder-white/30 focus:outline-none focus:border-cyan-500/50 transition-colors"
      />
    </div>
  );
}

export function FormSelect({ label, value, onChange, options, placeholder, required }) {
  return (
    <div className="space-y-2">
      {label && (
        <label className="text-sm font-medium text-white/70">
          {label}
          {required && <span className="text-red-400 ml-1">*</span>}
        </label>
      )}
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        required={required}
        className="w-full px-4 py-2 bg-white/5 border border-white/10 rounded-lg text-white focus:outline-none focus:border-cyan-500/50 transition-colors appearance-none cursor-pointer"
      >
        {placeholder && (
          <option value="" className="bg-gray-900">{placeholder}</option>
        )}
        {options.map((opt) => (
          <option key={opt.id || opt.value} value={opt.id || opt.value} className="bg-gray-900">
            {opt.name || opt.label}
          </option>
        ))}
      </select>
    </div>
  );
}

export function FormTextarea({ label, value, onChange, placeholder, rows = 4, required }) {
  return (
    <div className="space-y-2">
      {label && (
        <label className="text-sm font-medium text-white/70">
          {label}
          {required && <span className="text-red-400 ml-1">*</span>}
        </label>
      )}
      <textarea
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        rows={rows}
        required={required}
        className="w-full px-4 py-2 bg-white/5 border border-white/10 rounded-lg text-white placeholder-white/30 focus:outline-none focus:border-cyan-500/50 transition-colors resize-none"
      />
    </div>
  );
}
