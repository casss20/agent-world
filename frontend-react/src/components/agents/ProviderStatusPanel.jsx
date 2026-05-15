import React, { useState, useEffect } from 'react';
import { Plug, CheckCircle, XCircle, AlertTriangle, RefreshCw } from 'lucide-react';

/**
 * ProviderStatusPanel — Monitor external provider health
 * Shows DALL-E, Runway, Slack, SendGrid status
 */
export default function ProviderStatusPanel() {
  const [providers, setProviders] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchProviders();
  }, []);

  const fetchProviders = async () => {
    try {
      const res = await fetch('/api/plugins/registry');
      const data = await res.json();
      setProviders(data.providers || []);
    } catch (err) {
      console.error('Failed to fetch providers:', err);
    } finally {
      setLoading(false);
    }
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'active':
        return <CheckCircle className="w-5 h-5 text-green-500" />;
      case 'inactive':
        return <XCircle className="w-5 h-5 text-gray-400" />;
      case 'error':
        return <AlertTriangle className="w-5 h-5 text-red-500" />;
      default:
        return <Plug className="w-5 h-5 text-gray-400" />;
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-32">
        <RefreshCw className="w-5 h-5 animate-spin text-blue-600" />
      </div>
    );
  }

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">External Providers</h2>
          <p className="text-sm text-gray-500 mt-1">
            Third-party integrations and API health
          </p>
        </div>
        <button
          onClick={fetchProviders}
          className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
        >
          <RefreshCw className="w-4 h-4 text-gray-600" />
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {providers.map((provider) => (
          <div
            key={provider.name}
            className="bg-white rounded-lg border border-gray-200 p-4"
          >
            <div className="flex items-start justify-between">
              <div className="flex items-center gap-3">
                {getStatusIcon(provider.status)}
                <div>
                  <h3 className="font-semibold text-gray-900">
                    {provider.name}
                  </h3>
                  <p className="text-xs text-gray-500">
                    {provider.provider_type} • v{provider.version}
                  </p>
                </div>
              </div>
              <span
                className={`px-2 py-0.5 text-xs rounded-full ${
                  provider.status === 'active'
                    ? 'bg-green-100 text-green-700'
                    : provider.status === 'error'
                    ? 'bg-red-100 text-red-700'
                    : 'bg-gray-100 text-gray-600'
                }`}
              >
                {provider.status}
              </span>
            </div>

            {provider.error_message && (
              <p className="mt-2 text-xs text-red-600 bg-red-50 rounded px-2 py-1">
                {provider.error_message}
              </p>
            )}

            <div className="mt-3 text-xs text-gray-500">
              <p>Required credentials: {provider.required_credentials?.join(', ') || 'None'}</p>
            </div>
          </div>
        ))}

        {providers.length === 0 && (
          <div className="col-span-2 text-center py-8 text-gray-500">
            <Plug className="w-8 h-8 mx-auto mb-2 text-gray-300" />
            <p>No providers registered yet</p>
          </div>
        )}
      </div>
    </div>
  );
}
