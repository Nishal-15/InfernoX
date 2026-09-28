'use client';

import React, { useState, useEffect } from 'react';
import { useAuth } from '../lib/authContext';
import {
  getPlatformOverview,
  getAllOrganizations,
  updateOrganizationStatus,
  getPlatformAuditLogs,
  PlatformOverview,
  SaasOrganization,
  PlatformAuditLog
} from '../lib/api';
import {
  X, ShieldCheck, Building2, Flame, History
} from 'lucide-react';

interface AdminHqModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const AdminHqModal: React.FC<AdminHqModalProps> = ({ isOpen, onClose }) => {
  const { isSuperAdmin } = useAuth();
  const [activeTab, setActiveTab] = useState<'overview' | 'organizations' | 'audit'>('overview');
  const [overview, setOverview] = useState<PlatformOverview | null>(null);
  const [organizations, setOrganizations] = useState<SaasOrganization[]>([]);
  const [auditLogs, setAuditLogs] = useState<PlatformAuditLog[]>([]);
  const [actionFilter, setActionFilter] = useState('');

  useEffect(() => {
    if (isOpen && isSuperAdmin) {
      loadData();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isOpen, isSuperAdmin, activeTab]);

  const loadData = async () => {
    try {
      if (activeTab === 'overview') {
        const ov = await getPlatformOverview();
        setOverview(ov);
      } else if (activeTab === 'organizations') {
        const orgs = await getAllOrganizations();
        setOrganizations(orgs);
      } else if (activeTab === 'audit') {
        const logs = await getPlatformAuditLogs({ action: actionFilter || undefined });
        setAuditLogs(logs);
      }
    } catch (err: unknown) {
      console.error('Failed to load admin data:', err);
    }
  };

  const handleToggleStatus = async (orgId: string, currentStatus: string) => {
    const newStatus = currentStatus === 'ACTIVE' ? 'SUSPENDED' : 'ACTIVE';
    if (!confirm(`Are you sure you want to change organization status to ${newStatus}?`)) return;
    try {
      await updateOrganizationStatus(orgId, newStatus);
      const updated = await getAllOrganizations();
      setOrganizations(updated);
    } catch {
      alert('Failed to update organization status');
    }
  };

  if (!isOpen || !isSuperAdmin) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-md">
      <div className="relative w-full max-w-5xl max-h-[88vh] bg-slate-900 border border-slate-700/80 rounded-2xl shadow-2xl flex flex-col overflow-hidden animate-in fade-in zoom-in-95 duration-200">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800 bg-slate-900/90">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-xl bg-gradient-to-br from-purple-500 to-indigo-600 text-white shadow-md">
              <ShieldCheck size={20} />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-lg font-bold text-white">Platform Admin HQ</h2>
                <span className="text-[10px] font-bold tracking-wider px-2 py-0.5 rounded-full bg-purple-500/20 text-purple-300 border border-purple-500/30 uppercase">
                  Superadmin Scope
                </span>
              </div>
              <p className="text-xs text-slate-400">Multi-tenant management & platform governance</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
          >
            <X size={18} />
          </button>
        </div>

        {/* Tab Navigation */}
        <div className="flex items-center px-6 border-b border-slate-800 bg-slate-950/40 gap-2">
          <button
            onClick={() => setActiveTab('overview')}
            className={`flex items-center gap-2 py-3 px-3 text-xs font-semibold border-b-2 transition-all ${
              activeTab === 'overview'
                ? 'border-purple-400 text-purple-400'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <Flame size={15} />
            <span>Platform Metrics</span>
          </button>

          <button
            onClick={() => setActiveTab('organizations')}
            className={`flex items-center gap-2 py-3 px-3 text-xs font-semibold border-b-2 transition-all ${
              activeTab === 'organizations'
                ? 'border-purple-400 text-purple-400'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <Building2 size={15} />
            <span>All Organizations</span>
          </button>

          <button
            onClick={() => setActiveTab('audit')}
            className={`flex items-center gap-2 py-3 px-3 text-xs font-semibold border-b-2 transition-all ${
              activeTab === 'audit'
                ? 'border-purple-400 text-purple-400'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <History size={15} />
            <span>Platform Audit Logs</span>
          </button>
        </div>

        {/* Tab Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {/* 1. OVERVIEW */}
          {activeTab === 'overview' && overview && (
            <div className="space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800">
                  <span className="text-xs text-slate-400">Total Organizations</span>
                  <p className="text-2xl font-black text-white mt-1">{overview.organizations.total}</p>
                  <span className="text-[11px] text-emerald-400">{overview.organizations.active} active</span>
                </div>

                <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800">
                  <span className="text-xs text-slate-400">Total Users</span>
                  <p className="text-2xl font-black text-white mt-1">{overview.users.total}</p>
                  <span className="text-[11px] text-emerald-400">{overview.users.active} active</span>
                </div>

                <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800">
                  <span className="text-xs text-slate-400">Monitored Facilities</span>
                  <p className="text-2xl font-black text-amber-400 mt-1">{overview.intelligence.total_facilities_monitored}</p>
                  <span className="text-[11px] text-slate-500">Public & Private</span>
                </div>

                <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800">
                  <span className="text-xs text-slate-400">System Status</span>
                  <p className="text-2xl font-black text-emerald-400 mt-1">{overview.system_status}</p>
                  <span className="text-[11px] text-slate-500">Autonomous Services Online</span>
                </div>
              </div>

              {/* Plans breakdown */}
              <div className="p-5 rounded-xl bg-slate-950/60 border border-slate-800 space-y-3">
                <h3 className="text-xs font-bold uppercase tracking-wider text-slate-300">Tenant Subscription Breakdown</h3>
                <div className="flex gap-4">
                  {Object.entries(overview.organizations.by_plan).map(([plan, count]) => (
                    <div key={plan} className="px-4 py-2 rounded-lg bg-slate-900 border border-slate-800">
                      <span className="text-xs text-slate-400 uppercase font-semibold">{plan}</span>
                      <p className="text-lg font-bold text-amber-400">{count} tenants</p>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* 2. ALL ORGANIZATIONS */}
          {activeTab === 'organizations' && (
            <div className="border border-slate-800 rounded-xl overflow-hidden divide-y divide-slate-800/80">
              {organizations.map((org) => (
                <div key={org.id} className="p-4 bg-slate-900/60 flex items-center justify-between hover:bg-slate-800/40">
                  <div>
                    <div className="flex items-center gap-2">
                      <h4 className="text-sm font-bold text-white">{org.name}</h4>
                      <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-300 border border-amber-500/30 uppercase">
                        {org.plan}
                      </span>
                      <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${
                        org.status === 'ACTIVE' ? 'bg-emerald-500/20 text-emerald-300' : 'bg-rose-500/20 text-rose-300'
                      }`}>
                        {org.status}
                      </span>
                    </div>
                    <p className="text-xs text-slate-400 font-mono mt-0.5">ID: {org.id}</p>
                  </div>

                  <button
                    onClick={() => handleToggleStatus(org.id || org.organization_id || '', org.status || 'ACTIVE')}
                    className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors ${
                      org.status === 'ACTIVE'
                        ? 'bg-rose-500/10 hover:bg-rose-500/20 text-rose-400 border border-rose-500/30'
                        : 'bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                    }`}
                  >
                    {org.status === 'ACTIVE' ? 'Suspend Tenant' : 'Activate Tenant'}
                  </button>
                </div>
              ))}
            </div>
          )}

          {/* 3. AUDIT LOGS */}
          {activeTab === 'audit' && (
            <div className="space-y-4">
              <div className="flex items-center gap-2">
                <input
                  type="text"
                  placeholder="Filter by action (e.g. user.login, api_key.created)"
                  value={actionFilter}
                  onChange={(e) => setActionFilter(e.target.value)}
                  className="px-3 py-1.5 bg-slate-950 border border-slate-700 rounded-lg text-xs text-slate-200 focus:outline-none focus:border-purple-500"
                />
                <button
                  onClick={loadData}
                  className="px-3 py-1.5 rounded-lg bg-purple-600 hover:bg-purple-500 text-white font-semibold text-xs transition-colors"
                >
                  Filter
                </button>
              </div>

              <div className="border border-slate-800 rounded-xl overflow-hidden divide-y divide-slate-800/80 font-mono text-xs">
                {auditLogs.map((log) => (
                  <div key={log.id} className="p-3 bg-slate-900/60 hover:bg-slate-800/40 flex items-center justify-between">
                    <div>
                      <span className="text-purple-400 font-bold">{log.action}</span>
                      <span className="text-slate-400 ml-2">by {log.actor_email || 'system'}</span>
                      {log.details && (
                        <p className="text-[11px] text-slate-500 font-sans mt-0.5 truncate max-w-xl">
                          {JSON.stringify(log.details)}
                        </p>
                      )}
                    </div>
                    <span className="text-[11px] text-slate-500 shrink-0">
                      {new Date(log.created_at).toLocaleString()}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
