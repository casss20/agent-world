import { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';

/**
 * Extract prefill data from URL query params
 * AgencyOS pattern: ?prefill_first_name=John&prefill_budget=500
 * 
 * @param prefix - The prefix to look for (default: 'prefill_')
 * @returns Object with prefill data (key names have prefix removed)
 * 
 * @example
 * URL: ?prefill_business_name=Acme&prefill_budget=1000
 * Returns: { business_name: 'Acme', budget: '1000' }
 */
export function usePrefillData(prefix = 'prefill_') {
  const [searchParams] = useSearchParams();
  const [prefillData, setPrefillData] = useState({});

  useEffect(() => {
    const data = {};
    searchParams.forEach((value, key) => {
      if (key.startsWith(prefix)) {
        const fieldName = key.slice(prefix.length);
        data[fieldName] = value;
      }
    });
    setPrefillData(data);
  }, [searchParams, prefix]);

  return prefillData;
}

/**
 * Generate a prefill URL for sharing strategies
 * 
 * @param baseUrl - The base URL (e.g., '/diagnostics/123/strategy')
 * @param data - Object with data to prefill
 * @param prefix - Prefix for query params (default: 'prefill_')
 * @returns Full URL with prefill params
 * 
 * @example
 * generatePrefillUrl('/strategy/123', { business_name: 'Acme', budget: 1000 })
 * Returns: '/strategy/123?prefill_business_name=Acme&prefill_budget=1000'
 */
export function generatePrefillUrl(baseUrl, data, prefix = 'prefill_') {
  const params = new URLSearchParams();
  
  Object.entries(data).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') {
      params.append(`${prefix}${key}`, String(value));
    }
  });
  
  const queryString = params.toString();
  return queryString ? `${baseUrl}?${queryString}` : baseUrl;
}

/**
 * Apply prefill data to form state
 * Only overwrites empty/null/undefined values
 * 
 * @param prefillData - Data from usePrefillData
 * @param currentState - Current form state
 * @returns Merged state
 */
export function applyPrefill(prefillData, currentState) {
  const merged = { ...currentState };
  
  Object.entries(prefillData).forEach(([key, value]) => {
    // Only apply if current value is empty/null/undefined
    if (merged[key] === undefined || merged[key] === null || merged[key] === '') {
      merged[key] = value;
    }
  });
  
  return merged;
}

/**
 * Hook that manages form state with prefill support
 * 
 * @param initialState - Initial form state
 * @param prefix - Prefill param prefix
 * @returns { formState, setFormState, prefillData, hasPrefill }
 */
export function usePrefilledForm(initialState, prefix = 'prefill_') {
  const prefillData = usePrefillData(prefix);
  const [formState, setFormState] = useState(initialState);
  const [hasPrefill, setHasPrefill] = useState(false);

  useEffect(() => {
    if (Object.keys(prefillData).length > 0) {
      setFormState(prev => applyPrefill(prefillData, prev));
      setHasPrefill(true);
    }
  }, [prefillData]);

  return {
    formState,
    setFormState,
    prefillData,
    hasPrefill,
    clearPrefill: () => setHasPrefill(false)
  };
}
