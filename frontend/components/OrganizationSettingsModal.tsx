'use client';

import React, { useState, useEffect } from 'react';
import { useAuth } from '../lib/authContext';
import {
  getOrganizationMembers,
  updateMemberRole,
  removeMember,
  inviteMember,
  getPendingInvitations,
  getApiKeys,
  createApiKey,
  revokeApiKey,
  getWebhooks,
  createWebhook,
  deleteWebhook,
  updateCurrentOrganization,
  SaasMember,
  SaasInvitation,
  SaasApiKey,
  SaasWebhook,
  SaasApiKeyCreated
} from '../lib/api';
import {
  X, Users, Key, Webhook, Settings, Plus, Trash2, Copy, Check,
  AlertTriangle, Send
} from 'lucide-react';

interface OrganizationSettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
  onOpenBilling?: () => void;
}

export const OrganizationSettingsModal: React.FC<OrganizationSettingsModalProps> = ({
  isOpen,
  onClose,
  onOpenBilling
}) => {
  const { activeOrg, refreshTenantState } = useAuth();
  const [activeTab, setActiveTab] = useState<'profile' | 'members' | 'apikeys' | 'webhooks'>('members');

  // Members state
  const [members, setMembers] = useState<SaasMember[]>([]);
  const [invitations, setInvitations] = useState<SaasInvitation[]>([]);
  const [inviteEmail, setInviteEmail] = useState('');
  const [inviteRole, setInviteRole] = useState('ANALYST');
  const [inviteLoading, setInviteLoading] = useState(false);
  const [inviteError, setInviteError] = useState('');

  // API Keys state
  const [apiKeys, setApiKeys] = useState<SaasApiKey[]>([]);
  const [newKeyName, setNewKeyName] = useState('');
  const [newKeyPermissions] = useState<string[]>(['events.read', 'analytics.read']);
  const [createdApiKey, setCreatedApiKey] = useState<SaasApiKeyCreated | null>(null);
  const [copiedKey, setCopiedKey] = useState(false);

  // Webhooks state
  const [webhooks, setWebhooks] = useState<SaasWebhook[]>([]);
  const [webhookUrl, setWebhookUrl] = useState('');
  const [webhookEvents] = useState<string[]>(['alert.created', 'alert.escalated']);

  // Profile state
  const [orgName, setOrgName] = useState('');
  const [customRegion, setCustomRegion] = useState('');
  const [profileSaved, setProfileSaved] = useState(false);

  const [statusMsg, setStatusMsg] = useState('');

  useEffect(() => {
    if (isOpen && activeOrg) {
      setOrgName(activeOrg.name || '');
      setCustomRegion(activeOrg.custom_region || '');
      loadTabData(activeTab);
    }
  }, [isOpen, activeOrg, activeTab]);

  const loadTabData = async (tab: string) => {
    setStatusMsg('');
    try {
      if (tab === 'members') {
        const [m, inv] = await Promise.all([
          getOrganizationMembers().catch(() => []),
          getPendingInvitations().catch(() => [])
        ]);
        setMembers(m);
        setInvitations(inv);
      } else if (tab === 'apikeys') {
        const keys = await getApiKeys().catch(() => []);
        setApiKeys(keys);
      } else if (tab === 'webhooks') {
        const wh = await getWebhooks().catch(() => []);
        setWebhooks(wh);
      }
    } catch (err: unknown) {
      const apiErr = err as { response?: { data?: { detail?: string } } };
      setStatusMsg(apiErr?.response?.data?.detail || 'Failed to load settings data');
    }
  };

  if (!isOpen || !activeOrg) return null;

  // Handlers
  const handleSaveProfile = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await updateCurrentOrganization({ name: orgName, custom_region: customRegion });
      setProfileSaved(true);
      await refreshTenantState();
      setTimeout(() => setProfileSaved(false), 3000);
    } catch (err: unknown) {
      const apiErr = err as { response?: { data?: { detail?: string } } };
      setStatusMsg(apiErr?.response?.data?.detail || 'Failed to update profile');
    }
  };

  const handleInvite = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inviteEmail.trim()) return;
    setInviteLoading(true);
    setInviteError('');
    try {
      await inviteMember({ email: inviteEmail, role: inviteRole });
      setInviteEmail('');
      loadTabData('members');
    } catch (err: unknown) {
      const apiErr = err as { response?: { data?: { detail?: string } } };
      setInviteError(apiErr?.response?.data?.detail || 'Failed to send invitation');
    } finally {
      setInviteLoading(false);
    }
  };

  const handleRoleChange = async (memberId: string, newRole: string) => {
    try {
      await updateMemberRole(memberId, newRole);
      loadTabData('members');
    } catch (err: unknown) {
      const apiErr = err as { response?: { data?: { detail?: string } } };
      alert(apiErr?.response?.data?.detail || 'Failed to update role');
    }
  };

  const handleRemoveMember = async (memberId: string) => {
    if (!confirm('Are you sure you want to remove this member from the organization?')) return;
    try {
      await removeMember(memberId);
      loadTabData('members');
    } catch (err: unknown) {
      const apiErr = err as { response?: { data?: { detail?: string } } };
      alert(apiErr?.response?.data?.detail || 'Failed to remove member');
    }
  };

  const handleCreateApiKey = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newKeyName.trim()) return;
    try {
      const created = await createApiKey({
        name: newKeyName,
        permissions: newKeyPermissions
      });
      setCreatedApiKey(created);
      setNewKeyName('');
      loadTabData('apikeys');
    } catch (err: unknown) {
      const apiErr = err as { response?: { data?: { detail?: string } } };
      setStatusMsg(apiErr?.response?.data?.detail || 'Failed to generate API key');
    }
  };

  const handleRevokeKey = async (keyId: string) => {
    if (!confirm('Revoke this API key immediately? External integrations will fail.')) return;
    try {
      await revokeApiKey(keyId);
      loadTabData('apikeys');
    } catch (err: unknown) {
      const apiErr = err as { response?: { data?: { detail?: string } } };
      alert(apiErr?.response?.data?.detail || 'Failed to revoke key');
    }
  };

  const handleCreateWebhook = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!webhookUrl.trim()) return;
    try {
      await createWebhook({
        url: webhookUrl,
        subscribed_events: webhookEvents
      });
      setWebhookUrl('');
      loadTabData('webhooks');
    } catch (err: unknown) {
      const apiErr = err as { response?: { data?: { detail?: string } } };
      setStatusMsg(apiErr?.response?.data?.detail || 'Failed to create webhook');
    }
  };

  const handleDeleteWebhook = async (webhookId: string) => {
    if (!confirm('Delete this webhook endpoint?')) return;
    try {
      await deleteWebhook(webhookId);
      loadTabData('webhooks');
    } catch (err: unknown) {
      const apiErr = err as { response?: { data?: { detail?: string } } };
      alert(apiErr?.response?.data?.detail || 'Failed to delete webhook');
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-md">
      <div className="relative w-full max-w-4xl max-h-[85vh] bg-slate-900 border border-slate-700/80 rounded-2xl shadow-2xl flex flex-col overflow-hidden animate-in fade-in zoom-in-95 duration-200">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800 bg-slate-900/90">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-xl bg-amber-500/10 text-amber-400 border border-amber-500/20">
              <Settings size={20} />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-lg font-bold text-white">{activeOrg.name}</h2>
                <span className="text-[10px] font-bold tracking-wider px-2 py-0.5 rounded-full bg-amber-500/20 text-amber-300 border border-amber-500/30 uppercase">
                  {activeOrg.plan}
                </span>
              </div>
              <p className="text-xs text-slate-400">Organization Settings & Role-Based Access Control</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {onOpenBilling && (
              <button
                onClick={() => { onClose(); onOpenBilling(); }}
                className="px-3 py-1.5 rounded-lg bg-amber-500/10 hover:bg-amber-500/20 text-amber-400 border border-amber-500/30 text-xs font-semibold transition-colors"
              >
                Plan & Limits
              </button>
            )}
            <button
              onClick={onClose}
              className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
            >
              <X size={18} />
            </button>
          </div>
        </div>

        {/* Tab Navigation */}
        <div className="flex items-center px-6 border-b border-slate-800 bg-slate-950/40 gap-2">
          <button
            onClick={() => setActiveTab('members')}
            className={`flex items-center gap-2 py-3 px-3 text-xs font-semibold border-b-2 transition-all ${
              activeTab === 'members'
                ? 'border-amber-400 text-amber-400'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <Users size={15} />
            <span>Team & RBAC ({members.length})</span>
          </button>

          <button
            onClick={() => setActiveTab('apikeys')}
            className={`flex items-center gap-2 py-3 px-3 text-xs font-semibold border-b-2 transition-all ${
              activeTab === 'apikeys'
                ? 'border-amber-400 text-amber-400'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <Key size={15} />
            <span>API Keys ({apiKeys.length})</span>
          </button>

          <button
            onClick={() => setActiveTab('webhooks')}
            className={`flex items-center gap-2 py-3 px-3 text-xs font-semibold border-b-2 transition-all ${
              activeTab === 'webhooks'
                ? 'border-amber-400 text-amber-400'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <Webhook size={15} />
            <span>Webhooks ({webhooks.length})</span>
          </button>

          <button
            onClick={() => setActiveTab('profile')}
            className={`flex items-center gap-2 py-3 px-3 text-xs font-semibold border-b-2 transition-all ${
              activeTab === 'profile'
                ? 'border-amber-400 text-amber-400'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <Settings size={15} />
            <span>Workspace Profile</span>
          </button>
        </div>

        {/* Tab Content Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {statusMsg && (
            <div className="p-3 rounded-xl bg-amber-500/10 border border-amber-500/20 text-amber-300 text-xs">
              {statusMsg}
            </div>
          )}

          {/* 1. MEMBERS & RBAC */}
          {activeTab === 'members' && (
            <div className="space-y-6">
              {/* Invite Form */}
              <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800 space-y-3">
                <h3 className="text-xs font-bold uppercase tracking-wider text-slate-300">Invite Team Member</h3>
                <form onSubmit={handleInvite} className="flex flex-wrap items-center gap-2">
                  <input
                    type="email"
                    required
                    placeholder="colleague@domain.com"
                    value={inviteEmail}
                    onChange={(e) => setInviteEmail(e.target.value)}
                    className="flex-1 min-w-[200px] px-3 py-1.5 bg-slate-900 border border-slate-700 rounded-lg text-xs text-slate-200 focus:outline-none focus:border-amber-500"
                  />
                  <select
                    value={inviteRole}
                    onChange={(e) => setInviteRole(e.target.value)}
                    className="px-3 py-1.5 bg-slate-900 border border-slate-700 rounded-lg text-xs text-slate-200 focus:outline-none focus:border-amber-500"
                  >
                    <option value="ANALYST">Analyst (Investigate & Review)</option>
                    <option value="OPERATOR">Operator (Alerts & Acknowledge)</option>
                    <option value="ORG_ADMIN">Org Admin (Full Tenant Admin)</option>
                    <option value="REPORT_MANAGER">Report Manager (Reports Export)</option>
                    <option value="VIEWER">Viewer (Read-Only)</option>
                  </select>
                  <button
                    type="submit"
                    disabled={inviteLoading}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-amber-500 hover:bg-amber-600 text-slate-950 font-bold text-xs transition-colors cursor-pointer"
                  >
                    <Send size={13} />
                    <span>Send Invite</span>
                  </button>
                </form>
                {inviteError && <p className="text-[11px] text-rose-400">{inviteError}</p>}
              </div>

              {/* Members Table */}
              <div className="space-y-2">
                <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400">Active Members</h3>
                <div className="border border-slate-800 rounded-xl overflow-hidden divide-y divide-slate-800/80">
                  {members.map((m) => (
                    <div key={m.id} className="p-3.5 bg-slate-900/60 flex items-center justify-between hover:bg-slate-800/40 transition-colors">
                      <div>
                        <p className="text-sm font-semibold text-slate-200">{m.user_name || 'Anonymous User'}</p>
                        <p className="text-xs text-slate-400">{m.user_email}</p>
                      </div>
                      <div className="flex items-center gap-3">
                        <select
                          value={m.role}
                          onChange={(e) => handleRoleChange(m.id, e.target.value)}
                          className="px-2.5 py-1 bg-slate-950 border border-slate-700 rounded-lg text-xs font-medium text-amber-400 focus:outline-none"
                        >
                          <option value="ORG_ADMIN">ORG_ADMIN</option>
                          <option value="ANALYST">ANALYST</option>
                          <option value="OPERATOR">OPERATOR</option>
                          <option value="REPORT_MANAGER">REPORT_MANAGER</option>
                          <option value="VIEWER">VIEWER</option>
                        </select>
                        <button
                          onClick={() => handleRemoveMember(m.id)}
                          className="p-1.5 rounded-lg text-slate-500 hover:text-rose-400 hover:bg-rose-500/10 transition-colors"
                          title="Remove Member"
                        >
                          <Trash2 size={15} />
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Pending Invitations */}
              {invitations.length > 0 && (
                <div className="space-y-2">
                  <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400">Pending Invitations ({invitations.length})</h3>
                  <div className="border border-slate-800 rounded-xl overflow-hidden divide-y divide-slate-800/80">
                    {invitations.map((inv) => (
                      <div key={inv.id} className="p-3 bg-slate-950/40 flex items-center justify-between text-xs">
                        <div>
                          <span className="text-slate-300 font-medium">{inv.email}</span>
                          <span className="ml-2 text-slate-500 font-mono text-[10px]">Token: {inv.token.slice(0, 8)}...</span>
                        </div>
                        <span className="px-2 py-0.5 rounded bg-blue-500/10 text-blue-400 border border-blue-500/20 font-semibold">
                          {inv.role}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* 2. API KEYS */}
          {activeTab === 'apikeys' && (
            <div className="space-y-6">
              {/* Created API Key Alert */}
              {createdApiKey && (
                <div className="p-4 rounded-xl bg-amber-500/10 border border-amber-500/30 space-y-2">
                  <div className="flex items-center gap-2 text-amber-400 font-bold text-xs uppercase tracking-wider">
                    <AlertTriangle size={15} />
                    <span>Copy API Key Immediately</span>
                  </div>
                  <p className="text-xs text-slate-300 leading-relaxed">
                    This raw secret will never be displayed again. Store it securely in your secrets manager.
                  </p>
                  <div className="flex items-center gap-2">
                    <input
                      type="text"
                      readOnly
                      value={createdApiKey.raw_api_key}
                      className="flex-1 px-3 py-1.5 bg-slate-950 border border-slate-700 rounded-lg text-xs font-mono text-amber-300 select-all"
                    />
                    <button
                      onClick={() => {
                        navigator.clipboard.writeText(createdApiKey.raw_api_key);
                        setCopiedKey(true);
                        setTimeout(() => setCopiedKey(false), 2000);
                      }}
                      className="px-3 py-1.5 rounded-lg bg-amber-500 text-slate-950 font-bold text-xs flex items-center gap-1.5"
                    >
                      {copiedKey ? <Check size={14} /> : <Copy size={14} />}
                      <span>{copiedKey ? 'Copied' : 'Copy'}</span>
                    </button>
                  </div>
                </div>
              )}

              {/* Create Key Form */}
              <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800 space-y-3">
                <h3 className="text-xs font-bold uppercase tracking-wider text-slate-300">Create Headless Integration Key</h3>
                <form onSubmit={handleCreateApiKey} className="flex items-center gap-2">
                  <input
                    type="text"
                    required
                    placeholder="e.g. Telemetry Ingest Daemon"
                    value={newKeyName}
                    onChange={(e) => setNewKeyName(e.target.value)}
                    className="flex-1 px-3 py-1.5 bg-slate-900 border border-slate-700 rounded-lg text-xs text-slate-200 focus:outline-none focus:border-amber-500"
                  />
                  <button
                    type="submit"
                    className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg bg-amber-500 hover:bg-amber-600 text-slate-950 font-bold text-xs transition-colors cursor-pointer"
                  >
                    <Plus size={13} />
                    <span>Generate Key</span>
                  </button>
                </form>
              </div>

              {/* API Keys Table */}
              <div className="border border-slate-800 rounded-xl overflow-hidden divide-y divide-slate-800/80">
                {apiKeys.length === 0 ? (
                  <div className="p-6 text-center text-xs text-slate-500">
                    No API keys active for this workspace. Create one above for headless integrations.
                  </div>
                ) : (
                  apiKeys.map((k) => (
                    <div key={k.id} className="p-3.5 bg-slate-900/60 flex items-center justify-between hover:bg-slate-800/40">
                      <div>
                        <div className="flex items-center gap-2">
                          <p className="text-sm font-semibold text-slate-200">{k.name}</p>
                          <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700">
                            {k.key_prefix}...
                          </span>
                        </div>
                        <p className="text-[11px] text-slate-500 mt-0.5">
                          Created {new Date(k.created_at).toLocaleDateString()}
                          {k.last_used_at ? ` · Last used ${new Date(k.last_used_at).toLocaleDateString()}` : ' · Never used'}
                        </p>
                      </div>
                      <button
                        onClick={() => handleRevokeKey(k.id)}
                        className="px-2.5 py-1 rounded bg-rose-500/10 hover:bg-rose-500/20 text-rose-400 border border-rose-500/30 text-xs font-semibold transition-colors"
                      >
                        Revoke
                      </button>
                    </div>
                  ))
                )}
              </div>
            </div>
          )}

          {/* 3. WEBHOOKS */}
          {activeTab === 'webhooks' && (
            <div className="space-y-6">
              {/* Create Webhook Form */}
              <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800 space-y-3">
                <h3 className="text-xs font-bold uppercase tracking-wider text-slate-300">Add Destination Webhook</h3>
                <form onSubmit={handleCreateWebhook} className="flex items-center gap-2">
                  <input
                    type="url"
                    required
                    placeholder="https://api.yourdomain.com/infernox/webhook"
                    value={webhookUrl}
                    onChange={(e) => setWebhookUrl(e.target.value)}
                    className="flex-1 px-3 py-1.5 bg-slate-900 border border-slate-700 rounded-lg text-xs text-slate-200 focus:outline-none focus:border-amber-500"
                  />
                  <button
                    type="submit"
                    className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg bg-amber-500 hover:bg-amber-600 text-slate-950 font-bold text-xs transition-colors cursor-pointer"
                  >
                    <Plus size={13} />
                    <span>Register</span>
                  </button>
                </form>
                <p className="text-[11px] text-slate-500">
                  Dispatches signed HMAC-SHA256 payloads with header <code className="text-amber-400">X-InfernoX-Signature</code>.
                </p>
              </div>

              {/* Webhooks List */}
              <div className="border border-slate-800 rounded-xl overflow-hidden divide-y divide-slate-800/80">
                {webhooks.length === 0 ? (
                  <div className="p-6 text-center text-xs text-slate-500">
                    No webhooks registered. Configure endpoints to receive real-time incident and alert callbacks.
                  </div>
                ) : (
                  webhooks.map((wh) => (
                    <div key={wh.id} className="p-3.5 bg-slate-900/60 flex items-center justify-between hover:bg-slate-800/40">
                      <div>
                        <p className="text-xs font-mono text-slate-200">{wh.url}</p>
                        <div className="flex items-center gap-2 mt-1">
                          <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${wh.is_active ? 'bg-emerald-500/20 text-emerald-400' : 'bg-rose-500/20 text-rose-400'}`}>
                            {wh.is_active ? 'ACTIVE' : 'DISABLED'}
                          </span>
                          <span className="text-[11px] text-slate-500">
                            Subscribed: {wh.subscribed_events?.join(', ')}
                          </span>
                        </div>
                      </div>
                      <button
                        onClick={() => handleDeleteWebhook(wh.id)}
                        className="p-1.5 text-slate-500 hover:text-rose-400 transition-colors"
                        title="Delete Webhook"
                      >
                        <Trash2 size={15} />
                      </button>
                    </div>
                  ))
                )}
              </div>
            </div>
          )}

          {/* 4. WORKSPACE PROFILE */}
          {activeTab === 'profile' && (
            <form onSubmit={handleSaveProfile} className="max-w-lg space-y-4">
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1.5">Workspace Name</label>
                <input
                  type="text"
                  required
                  value={orgName}
                  onChange={(e) => setOrgName(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-700 rounded-xl text-sm text-slate-200 focus:outline-none focus:border-amber-500"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1.5">Custom Geographic Focus (Optional Bounding Box or Region)</label>
                <input
                  type="text"
                  placeholder="e.g. 68.0,7.0,97.0,36.0 or Gujarat Petrochemical Corridor"
                  value={customRegion}
                  onChange={(e) => setCustomRegion(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-700 rounded-xl text-sm text-slate-200 focus:outline-none focus:border-amber-500"
                />
              </div>

              <div className="pt-2 flex items-center gap-3">
                <button
                  type="submit"
                  className="px-4 py-2 rounded-xl bg-amber-500 hover:bg-amber-600 text-slate-950 font-bold text-xs shadow-md transition-colors cursor-pointer"
                >
                  Save Workspace Changes
                </button>
                {profileSaved && <span className="text-xs text-emerald-400 font-medium">Saved successfully!</span>}
              </div>
            </form>
          )}
        </div>
      </div>
    </div>
  );
};
