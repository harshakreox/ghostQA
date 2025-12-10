import axios from 'axios';

const API_BASE_URL = '/api';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add auth interceptor to include token in requests
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('auth_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Handle 401 responses
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('auth_token');
      localStorage.removeItem('auth_user');
      localStorage.removeItem('auth_expiry');
      if (window.location.pathname !== '/login') {
        window.location.href = '/login';
      }
    }
    return Promise.reject(error);
  }
);

// Projects
export const getProjects = async () => {
  const response = await api.get('/projects');
  return response.data;
};

export const getProject = async (projectId) => {
  const response = await api.get(`/projects/${projectId}`);
  return response.data;
};

export const createProject = async (data) => {
  const response = await api.post('/projects', data);
  return response.data;
};

export const updateProject = async (projectId, data) => {
  const response = await api.put(`/projects/${projectId}`, data);
  return response.data;
};

export const deleteProject = async (projectId) => {
  const response = await api.delete(`/projects/${projectId}`);
  return response.data;
};

// Test Cases
export const getTestCase = async (projectId, testCaseId) => {
  const response = await api.get(`/projects/${projectId}/test-cases/${testCaseId}`);
  return response.data;
};

export const addTestCase = async (projectId, data) => {
  const response = await api.post(`/projects/${projectId}/test-cases`, data);
  return response.data;
};

export const updateTestCase = async (projectId, testCaseId, data) => {
  const response = await api.put(`/projects/${projectId}/test-cases/${testCaseId}`, data);
  return response.data;
};

export const deleteTestCase = async (projectId, testCaseId) => {
  const response = await api.delete(`/projects/${projectId}/test-cases/${testCaseId}`);
  return response.data;
};

// Test Execution
export const runTests = async (data) => {
  const response = await api.post('/run-tests', data);
  return response.data;
};

// Reports
export const getReports = async () => {
  const response = await api.get('/reports');
  return response.data;
};

export const getReport = async (reportId) => {
  const response = await api.get(`/reports/${reportId}`);
  return response.data;
};

export const getProjectReports = async (projectId) => {
  const response = await api.get(`/projects/${projectId}/reports`);
  return response.data;
};

export default api;
