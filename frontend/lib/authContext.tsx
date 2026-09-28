'use client';

import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import {
  SaasUser,
  SaasOrganization,
  TokenResponse,
  getMe,
  logoutUser as apiLogoutUser,
  getUserOrganizations
} from './api';

interface AuthContextType {
  user: SaasUser | null;
  activeOrg: SaasOrganization | null;
  organizations: SaasOrganization[];
  role: string | null;
  permissions: string[];
  isAuthenticated: boolean;
  isLoading: boolean;
  isSuperAdmin: boolean;
  hasPermission: (perm: string) => boolean;
  login: (tokenData: TokenResponse) => void;
  logout: () => Promise<void>;
  switchOrganization: (orgId: string) => Promise<void>;
  refreshTenantState: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<SaasUser | null>(null);
  const [activeOrg, setActiveOrg] = useState<SaasOrganization | null>(null);
  const [organizations, setOrganizations] = useState<SaasOrganization[]>([]);
  const [role, setRole] = useState<string | null>(null);
  const [permissions, setPermissions] = useState<string[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  // Initialize from localStorage and fetch current profile
  useEffect(() => {
    const initAuth = async () => {
      const token = typeof window !== 'undefined' ? localStorage.getItem('infernox_token') : null;
      if (!token) {
        setIsLoading(false);
        return;
      }

      try {
        const meData = await getMe();
        setUser(meData.user);
        setOrganizations(meData.organizations);

        const storedOrgId = localStorage.getItem('infernox_active_org_id');
        let selectedOrg = meData.organizations.find(o => (o.organization_id || o.id) === storedOrgId);
        if (!selectedOrg && meData.organizations.length > 0) {
          selectedOrg = meData.organizations[0];
          const primaryId = selectedOrg.organization_id || selectedOrg.id;
          if (primaryId) {
            localStorage.setItem('infernox_active_org_id', primaryId);
          }
        }

        if (selectedOrg) {
          setActiveOrg(selectedOrg);
          setRole(selectedOrg.role || 'VIEWER');
          setPermissions(selectedOrg.permissions || []);
        }
      } catch (err) {
        console.warn('Session expired or invalid, resetting auth state:', err);
        localStorage.removeItem('infernox_token');
        localStorage.removeItem('infernox_active_org_id');
        setUser(null);
        setActiveOrg(null);
        setOrganizations([]);
      } finally {
        setIsLoading(false);
      }
    };

    initAuth();
  }, []);

  const login = (tokenData: TokenResponse) => {
    localStorage.setItem('infernox_token', tokenData.access_token);
    if (tokenData.active_organization_id) {
      localStorage.setItem('infernox_active_org_id', tokenData.active_organization_id);
    }
    setUser(tokenData.user);
    setRole(tokenData.role || null);
    setPermissions(tokenData.permissions || []);

    // Refresh organizations list
    getUserOrganizations().then(orgs => {
      setOrganizations(orgs);
      const active = orgs.find(o => o.id === tokenData.active_organization_id) || orgs[0] || null;
      setActiveOrg(active);
    }).catch(console.error);
  };

  const logout = async () => {
    try {
      await apiLogoutUser();
    } catch {
      // Ignore network errors on logout
    }
    localStorage.removeItem('infernox_token');
    localStorage.removeItem('infernox_active_org_id');
    setUser(null);
    setActiveOrg(null);
    setOrganizations([]);
    setRole(null);
    setPermissions([]);
  };

  const switchOrganization = async (orgId: string) => {
    localStorage.setItem('infernox_active_org_id', orgId);
    try {
      const meData = await getMe();
      setOrganizations(meData.organizations);
      const chosen = meData.organizations.find(o =>
        (o as SaasOrganization & { organization_id?: string }).organization_id === orgId || o.id === orgId
      );
      if (chosen) {
        setActiveOrg(chosen);
        setRole(chosen.role || 'VIEWER');
        setPermissions(chosen.permissions || []);
      }
      // Re-trigger window storage event or dispatch custom event for components
      window.dispatchEvent(new CustomEvent('infernox_tenant_switched', { detail: { organization_id: orgId } }));
    } catch (err) {
      console.error('Failed to switch tenant:', err);
    }
  };

  const refreshTenantState = async () => {
    try {
      const meData = await getMe();
      setUser(meData.user);
      setOrganizations(meData.organizations);
      const storedOrgId = localStorage.getItem('infernox_active_org_id');
      const chosen = meData.organizations.find(o =>
        (o as SaasOrganization & { organization_id?: string }).organization_id === storedOrgId
      );
      if (chosen) {
        setActiveOrg(chosen);
        setRole(chosen.role || 'VIEWER');
        setPermissions(chosen.permissions || []);
      }
    } catch (err) {
      console.error('Failed to refresh tenant state:', err);
    }
  };

  const hasPermission = (perm: string): boolean => {
    if (user?.is_superadmin) return true;
    if (role === 'SUPER_ADMIN') return true;
    return permissions.includes(perm);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        activeOrg,
        organizations,
        role,
        permissions,
        isAuthenticated: !!user,
        isLoading,
        isSuperAdmin: user?.is_superadmin || role === 'SUPER_ADMIN',
        hasPermission,
        login,
        logout,
        switchOrganization,
        refreshTenantState,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
