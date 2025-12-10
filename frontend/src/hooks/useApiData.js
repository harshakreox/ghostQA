import { useState, useEffect, useCallback, useRef } from 'react';
import axios from 'axios';

// Helper to get auth headers
const getAuthHeaders = () => {
  const token = localStorage.getItem('auth_token');
  return token ? { Authorization: `Bearer ${token}` } : {};
};

/**
 * useApiData - Custom hook for fetching data from an API endpoint
 *
 * @param {string} endpoint - The API endpoint to fetch from
 * @param {Object} options - Configuration options
 * @param {boolean} options.immediate - Whether to fetch immediately on mount (default: true)
 * @param {any} options.initialData - Initial data value (default: null)
 * @param {function} options.transform - Transform function for the response data
 *
 * @returns {Object} - { data, loading, error, refetch, setData }
 */
export default function useApiData(endpoint, options = {}) {
  const { immediate = true, initialData = null, transform = null } = options;

  const [data, setData] = useState(initialData);
  const [loading, setLoading] = useState(immediate);
  const [error, setError] = useState(null);

  // Use refs to avoid dependency issues
  const transformRef = useRef(transform);
  const isMountedRef = useRef(true);
  const hasFetchedRef = useRef(false);

  // Update transform ref on each render
  transformRef.current = transform;

  const fetchData = useCallback(async () => {
    if (!endpoint) return null;

    setLoading(true);
    setError(null);

    try {
      const response = await axios.get(endpoint, { headers: getAuthHeaders() });
      const responseData = transformRef.current
        ? transformRef.current(response.data)
        : response.data;

      if (isMountedRef.current) {
        setData(responseData);
        setLoading(false);
      }
      return responseData;
    } catch (err) {
      const errorMessage = err.response?.data?.detail || err.message || 'An error occurred';
      if (isMountedRef.current) {
        setError(errorMessage);
        setLoading(false);
      }
      console.error(`Error fetching ${endpoint}:`, err);
      return null;
    }
  }, [endpoint]);

  // Initial fetch - runs only once on mount
  useEffect(() => {
    isMountedRef.current = true;

    if (immediate && !hasFetchedRef.current) {
      hasFetchedRef.current = true;
      fetchData();
    }

    return () => {
      isMountedRef.current = false;
    };
    // Only depend on endpoint and immediate - fetchData is stable due to useCallback
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [endpoint, immediate]);

  const refetch = useCallback(() => {
    return fetchData();
  }, [fetchData]);

  return {
    data,
    loading,
    error,
    refetch,
    setData,
  };
}

/**
 * useApiMutation - Custom hook for POST/PUT/DELETE API operations
 */
export function useApiMutation(endpoint, method = 'post') {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [data, setData] = useState(null);

  const mutate = useCallback(
    async (payload, customEndpoint = null) => {
      setLoading(true);
      setError(null);

      try {
        const url = customEndpoint || endpoint;
        const response = await axios[method](url, payload, { headers: getAuthHeaders() });
        setData(response.data);
        return { success: true, data: response.data };
      } catch (err) {
        const errorMessage = err.response?.data?.detail || err.message || 'An error occurred';
        setError(errorMessage);
        return { success: false, error: errorMessage };
      } finally {
        setLoading(false);
      }
    },
    [endpoint, method]
  );

  return {
    mutate,
    loading,
    error,
    data,
  };
}
