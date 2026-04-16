import { useState, useCallback } from 'react';

const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:8000';

export function useApi() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const request = useCallback(async (method, endpoint, body = null, customHeaders = {}) => {
    setLoading(true);
    setError(null);

    try {
      const url = endpoint.startsWith('http') ? endpoint : `${API_BASE}${endpoint}`;
      const headers = {
        'Content-Type': 'application/json',
        ...customHeaders
      };

      const config = {
        method,
        headers,
      };

      if (body && method !== 'GET') {
        config.body = JSON.stringify(body);
      }

      const response = await fetch(url, config);

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ message: 'Request failed' }));
        throw new Error(errorData.message || `HTTP ${response.status}`);
      }

      const data = await response.json();
      setLoading(false);
      return data;
    } catch (err) {
      setError(err.message);
      setLoading(false);
      return null;
    }
  }, []);

  const get = useCallback((endpoint, customHeaders) => 
    request('GET', endpoint, null, customHeaders), [request]);

  const post = useCallback((endpoint, body, customHeaders) => 
    request('POST', endpoint, body, customHeaders), [request]);

  const put = useCallback((endpoint, body, customHeaders) => 
    request('PUT', endpoint, body, customHeaders), [request]);

  const del = useCallback((endpoint, customHeaders) => 
    request('DELETE', endpoint, null, customHeaders), [request]);

  return {
    loading,
    error,
    get,
    post,
    put,
    delete: del,
    request
  };
}
