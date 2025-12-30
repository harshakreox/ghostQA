/**
 * Organization Context
 * Manages current user's organization and permissions
 */
import { createContext, useContext, useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import { useAuth } from './AuthContext';

const OrganizationContext = createContext(null);

// Helper to get auth headers
const getAuthHeaders = () => {
  const token = localStorage.getItem('auth_token');
  return token ? { Authorization: `Bearer ${token}` } : {};
};

export function OrganizationProvider({ children }) {
  const { user, isAuthenticated } = useAuth();
  const [organization, setOrganization] = useState(null);
  const [orgRole, setOrgRole] = useState(null);
  const [loading, setLoading] = useState(true);
  const [accessibleProjects, setAccessibleProjects] = useState([]);
  const [error, setError] = useState(null);

  const loadOrganizationData = useCallback(async () => {
    if (!isAuthenticated) {
      setOrganization(null);
      setOrgRole(null);
      setAccessibleProjects([]);
      setLoading(false);
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const [orgRes, projectsRes] = await Promise.all([
        axios.get('/api/organizations/me/organization', { headers: getAuthHeaders() })
          .catch(() => ({ data: null })),
        axios.get('/api/organizations/me/projects', { headers: getAuthHeaders() })
          .catch(() => ({ data: [] }))
      ]);

      if (orgRes.data) {
        setOrganization(orgRes.data);
        setOrgRole(orgRes.data.my_role);
      }

      setAccessibleProjects(projectsRes.data || []);
    } catch (err) {
      console.error('Failed to load organization data:', err);
      setError('Failed to load organization data');
    } finally {
      setLoading(false);
    }
  }, [isAuthenticated]);

  useEffect(() => {
    loadOrganizationData();
  }, [loadOrganizationData]);

  // Permission helpers
  const isOrgAdmin = orgRole === 'org_admin';
  const isManager = orgRole === 'manager' || isOrgAdmin;
  const isMember = orgRole === 'member' || isManager;
  const canManageUsers = isOrgAdmin;
  const canManageProjects = isManager;
  const canCreateProjects = isManager;

  const canAccessProject = useCallback((projectId) => {
    if (isOrgAdmin) return true;
    return accessibleProjects.some(p => p.id === projectId);
  }, [isOrgAdmin, accessibleProjects]);

  const getProjectRole = useCallback((projectId) => {
    if (isOrgAdmin) return 'owner'; // Org admins have full access
    const project = accessibleProjects.find(p => p.id === projectId);
    return project?.my_role || null;
  }, [isOrgAdmin, accessibleProjects]);

  const canEditProject = useCallback((projectId) => {
    if (isOrgAdmin) return true;
    const role = getProjectRole(projectId);
    return role === 'owner' || role === 'editor';
  }, [isOrgAdmin, getProjectRole]);

  const canDeleteProject = useCallback((projectId) => {
    if (isOrgAdmin) return true;
    const role = getProjectRole(projectId);
    return role === 'owner';
  }, [isOrgAdmin, getProjectRole]);

  const canManageProjectMembers = useCallback((projectId) => {
    if (isOrgAdmin || isManager) return true;
    const role = getProjectRole(projectId);
    return role === 'owner';
  }, [isOrgAdmin, isManager, getProjectRole]);

  const value = {
    // Data
    organization,
    orgRole,
    loading,
    error,
    accessibleProjects,

    // Role checks
    isOrgAdmin,
    isManager,
    isMember,
    canManageUsers,
    canManageProjects,
    canCreateProjects,

    // Project permission checks
    canAccessProject,
    getProjectRole,
    canEditProject,
    canDeleteProject,
    canManageProjectMembers,

    // Actions
    refresh: loadOrganizationData
  };

  return (
    <OrganizationContext.Provider value={value}>
      {children}
    </OrganizationContext.Provider>
  );
}

export function useOrganization() {
  const context = useContext(OrganizationContext);
  if (!context) {
    throw new Error('useOrganization must be used within an OrganizationProvider');
  }
  return context;
}

export default OrganizationContext;
