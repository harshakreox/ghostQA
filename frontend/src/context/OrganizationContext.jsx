/**
 * Organization Context - SIMPLIFIED
 * Organizations removed - all users can access all projects
 */
import { createContext, useContext } from 'react';

const OrganizationContext = createContext(null);

export function OrganizationProvider({ children }) {
  const value = {
    organization: null,
    orgRole: null,
    loading: false,
    error: null,
    accessibleProjects: [],
    isOrgAdmin: true,
    isManager: true,
    isMember: true,
    canManageUsers: true,
    canManageProjects: true,
    canCreateProjects: true,
    canAccessProject: () => true,
    getProjectRole: () => 'owner',
    canEditProject: () => true,
    canDeleteProject: () => true,
    canManageProjectMembers: () => true,
    refresh: () => Promise.resolve()
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
    return {
      organization: null,
      orgRole: null,
      loading: false,
      error: null,
      accessibleProjects: [],
      isOrgAdmin: true,
      isManager: true,
      isMember: true,
      canManageUsers: true,
      canManageProjects: true,
      canCreateProjects: true,
      canAccessProject: () => true,
      getProjectRole: () => 'owner',
      canEditProject: () => true,
      canDeleteProject: () => true,
      canManageProjectMembers: () => true,
      refresh: () => Promise.resolve()
    };
  }
  return context;
}

export default OrganizationContext;
