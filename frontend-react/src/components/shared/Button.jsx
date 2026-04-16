import React from 'react';

export function Button({ 
  children, 
  onClick, 
  variant = 'primary', 
  loading = false,
  disabled = false,
  className = '',
  type = 'button'
}) {
  const baseStyles = 'px-4 py-2 rounded-lg font-medium transition-all duration-200 flex items-center justify-center gap-2';
  
  const variants = {
    primary: 'bg-cyan-500 hover:bg-cyan-600 text-white disabled:bg-cyan-500/50',
    secondary: 'bg-white/10 hover:bg-white/20 text-white border border-white/20 disabled:bg-white/5',
    ghost: 'bg-transparent hover:bg-white/5 text-white/70 hover:text-white disabled:text-white/30',
    success: 'bg-green-500 hover:bg-green-600 text-white disabled:bg-green-500/50',
    danger: 'bg-red-500 hover:bg-red-600 text-white disabled:bg-red-500/50'
  };

  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled || loading}
      className={`${baseStyles} ${variants[variant]} ${className}`}
    >
      {loading && (
        <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
      )}
      {children}
    </button>
  );
}
