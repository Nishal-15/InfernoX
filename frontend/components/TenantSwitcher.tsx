'use client';

import React, { useState } from 'react';
import { useAuth } from '../lib/authContext';
import { Building2, ChevronDown, Check, Plus } from 'lucide-react';
import { createOrganization, SaasOrganization } from '../lib/api';

interface TenantSwitcherProps {
  onOpenOrgSettings?: () => void;
}

export const TenantSwitcher: React.FC<TenantSwitcherProps> = ({ onOpenOrgSettings }) => {
  const { activeOrg, organizations, switchOrganization, refreshTenantState, isAuthenticated } = useAuth();
  const [isOpen, setIsOpen] = useState(false);
  const [isCreating, setIsCreating] = useState(false);
  const [newOrgName, setNewOrgName] = useState('');
  const [errorMsg, setErrorMsg] = useState('');

  if (!isAuthenticated || !activeOrg) {
    return null;
  }

  const handleSelect = async (orgId: string) => {
    setIsOpen(false);
    await switchOrganization(orgId);
  };

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newOrgName.trim()) return;
    try {
      const created = await createOrganization({ name: newOrgName });
      setIsCreating(false);
      setNewOrgName('');
      await refreshTenantState();
      const targetId = created.id || created.organization_id;
      if (targetId) {
        await switchOrganization(targetId);
      }
    } catch (err: unknown) {
      const apiErr = err as { response?: { data?: { detail?: string } } };
      setErrorMsg(apiErr?.response?.data?.detail || 'Failed to create organization');
    }
  };

  const getPlanBadge = (plan: string = 'free') => {
    const p = plan.toLowerCase();
    if (p === 'enterprise') {
      return <span className="text-[10px] uppercase font-bold tracking-wider px-1.5 py-0.5 rounded bg-purple-500/20 text-purple-300 border border-purple-500/30">Enterprise</span>;
    }
    if (p === 'pro') {
      return <span className="text-[10px] uppercase font-bold tracking-wider px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-300 border border-amber-500/30">Pro</span>;
    }
    return <span className="text-[10px] uppercase font-bold tracking-wider px-1.5 py-0.5 rounded bg-slate-700 text-slate-300 border border-slate-600">Free</span>;
  };

  return (
    <div className="relative inline-block text-left">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-900/80 hover:bg-slate-800 border border-slate-700/70 hover:border-slate-600 transition-all text-sm font-medium text-slate-200 shadow-sm"
        title="Switch Organization / Workspace"
      >
        <div className="p-1 rounded bg-amber-500/10 text-amber-400">
          <Building2 size={15} />
        </div>
        <span className="max-w-[140px] truncate font-semibold">
          {activeOrg.name || 'Workspace'}
        </span>
        {getPlanBadge(activeOrg.plan)}
        <ChevronDown size={14} className={`text-slate-400 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
      </button>

      {isOpen && (
        <div className="absolute left-0 mt-2 w-72 rounded-xl bg-slate-900 border border-slate-700 shadow-2xl z-50 overflow-hidden backdrop-blur-md">
          <div className="px-3.5 py-2.5 bg-slate-800/60 border-b border-slate-800 flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">Switch Workspace</span>
            <span className="text-[11px] text-slate-500">{organizations.length} available</span>
          </div>

          <div className="max-h-60 overflow-y-auto py-1 divide-y divide-slate-800/40">
            {organizations.map((org: SaasOrganization & { organization_id?: string }) => {
              const orgId = org.organization_id || org.id;
              if (!orgId) return null;
              const isSelected = orgId === ((activeOrg as SaasOrganization & { organization_id?: string }).organization_id || activeOrg.id);
              return (
                <button
                  key={orgId}
                  onClick={() => handleSelect(orgId)}
                  className={`w-full text-left px-3.5 py-2.5 flex items-center justify-between hover:bg-slate-800/70 transition-colors ${
                    isSelected ? 'bg-amber-500/10' : ''
                  }`}
                >
                  <div className="min-w-0 pr-2">
                    <p className={`text-sm truncate font-medium ${isSelected ? 'text-amber-300' : 'text-slate-200'}`}>
                      {org.name}
                    </p>
                    <div className="flex items-center gap-2 mt-0.5">
                      <span className="text-[11px] text-slate-400 capitalize">
                        {org.role ? org.role.replace('_', ' ') : 'Member'}
                      </span>
                      {getPlanBadge(org.plan)}
                    </div>
                  </div>
                  {isSelected && <Check size={16} className="text-amber-400 shrink-0" />}
                </button>
              );
            })}
          </div>

          <div className="p-2 border-t border-slate-800 bg-slate-900/90 space-y-1">
            {!isCreating ? (
              <button
                onClick={() => setIsCreating(true)}
                className="w-full flex items-center justify-center gap-1.5 py-1.5 px-3 rounded-lg text-xs font-medium text-slate-300 hover:text-white hover:bg-slate-800 transition-colors"
              >
                <Plus size={14} className="text-amber-400" />
                <span>Create New Organization</span>
              </button>
            ) : (
              <form onSubmit={handleCreate} className="space-y-2 p-1">
                <input
                  type="text"
                  placeholder="Organization Name"
                  value={newOrgName}
                  onChange={(e) => setNewOrgName(e.target.value)}
                  className="w-full px-2.5 py-1.5 bg-slate-950 border border-slate-700 rounded-md text-xs text-slate-200 focus:outline-none focus:border-amber-500"
                  autoFocus
                />
                {errorMsg && <p className="text-[10px] text-rose-400">{errorMsg}</p>}
                <div className="flex items-center gap-1.5 justify-end">
                  <button
                    type="button"
                    onClick={() => { setIsCreating(false); setErrorMsg(''); }}
                    className="px-2 py-1 text-xs text-slate-400 hover:text-slate-200"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    className="px-2.5 py-1 rounded bg-amber-500 hover:bg-amber-600 text-slate-950 font-semibold text-xs transition-colors"
                  >
                    Create
                  </button>
                </div>
              </form>
            )}

            {onOpenOrgSettings && (
              <button
                onClick={() => {
                  setIsOpen(false);
                  onOpenOrgSettings();
                }}
                className="w-full text-center py-1.5 text-xs text-amber-400 hover:text-amber-300 font-medium transition-colors"
              >
                Manage Organization & RBAC →
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
