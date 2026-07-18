import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Settings, Upload, Plus, Trash2, Key, Copy, Check, Loader2,
  FileText, Shield, Eye, EyeOff, RefreshCw
} from 'lucide-react';
import api from '../lib/api';
import { useAuthStore } from '../store/authStore';
import { StatusBadge } from '../components/StatusBadge';

// ─── Resume Upload Section ───────────────────────────────────
function ResumeUpload() {
  const [uploading, setUploading] = useState(false);
  const [message, setMessage] = useState('');

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const allowed = ['application/pdf', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'];
    if (!allowed.includes(file.type)) {
      setMessage('Only PDF and DOCX files are accepted.');
      return;
    }
    if (file.size > 10 * 1024 * 1024) {
      setMessage('File must be under 10 MB.');
      return;
    }

    setUploading(true);
    setMessage('');
    const formData = new FormData();
    formData.append('file', file);

    try {
      const res = await api.post('/users/me/resume', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      setMessage(`✓ ${res.data.filename} uploaded. Parsing in background.`);
    } catch (err: any) {
      setMessage(err.response?.data?.detail || 'Upload failed');
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="bg-(--color-bg-card) border border-(--color-border-default) rounded-(--radius-lg) p-6 shadow-(--shadow-card)">
      <div className="flex items-center gap-2 mb-3">
        <FileText className="w-5 h-5 text-(--color-accent)" />
        <h2 className="text-base font-semibold text-(--color-text-primary)">Resume</h2>
      </div>
      <p className="text-sm text-(--color-text-muted) mb-4">
        Upload your resume (PDF or DOCX, max 10MB). The LLM will parse it to match jobs.
      </p>
      <label className="flex items-center justify-center gap-2 px-4 py-4 border-2 border-dashed border-(--color-border-default) rounded-(--radius-lg) cursor-pointer hover:border-(--color-accent)/40 hover:bg-(--color-accent-subtle) transition-all">
        {uploading ? (
          <Loader2 className="w-5 h-5 animate-spin text-(--color-accent)" />
        ) : (
          <Upload className="w-5 h-5 text-(--color-text-muted)" />
        )}
        <span className="text-sm text-(--color-text-secondary)">
          {uploading ? 'Uploading...' : 'Click to upload resume'}
        </span>
        <input type="file" accept=".pdf,.docx" onChange={handleUpload} className="hidden" />
      </label>
      {message && (
        <p className={`text-sm mt-3 ${message.startsWith('✓') ? 'text-(--color-success)' : 'text-(--color-error)'}`}>
          {message}
        </p>
      )}
    </div>
  );
}

// ─── Portal Management Section ───────────────────────────────
function PortalManager() {
  const [showForm, setShowForm] = useState(false);
  const [portalType, setPortalType] = useState('naukri');
  const [displayName, setDisplayName] = useState('');
  const [credentials, setCredentials] = useState('');
  const [showCred, setShowCred] = useState(false);
  const queryClient = useQueryClient();

  const { data: portals, isLoading } = useQuery({
    queryKey: ['portals'],
    queryFn: async () => {
      const res = await api.get('/portals');
      return res.data as Array<{ id: string; portal_type: string; display_name: string; status: string; created_at: string }>;
    },
  });

  const addMutation = useMutation({
    mutationFn: async () => {
      await api.post('/portals', {
        portal_type: portalType,
        display_name: displayName || portalType,
        credentials: credentials || undefined,
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['portals'] });
      setShowForm(false);
      setDisplayName('');
      setCredentials('');
    },
  });

  const deleteMutation = useMutation({
    mutationFn: async (id: string) => {
      await api.delete(`/portals/${id}`);
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['portals'] }),
  });

  const portalTypes = [
    { value: 'naukri', label: 'Naukri' },
    { value: 'linkedin', label: 'LinkedIn' },
    { value: 'indeed', label: 'Indeed' },
    { value: 'glassdoor', label: 'Glassdoor' },
    { value: 'seek', label: 'SEEK' },
    { value: 'other', label: 'Other' },
  ];

  return (
    <div className="bg-(--color-bg-card) border border-(--color-border-default) rounded-(--radius-lg) p-6 shadow-(--shadow-card)">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Shield className="w-5 h-5 text-(--color-accent)" />
          <h2 className="text-base font-semibold text-(--color-text-primary)">Job Portals</h2>
        </div>
        <button
          onClick={() => setShowForm(!showForm)}
          className="flex items-center gap-1.5 px-3 py-1.5 text-sm bg-(--color-accent) hover:bg-(--color-accent-hover) text-(--color-text-inverse) rounded-(--radius-md) transition-colors shadow-sm"
        >
          <Plus className="w-3.5 h-3.5" /> Add Portal
        </button>
      </div>

      {showForm && (
        <div className="mb-4 p-4 bg-(--color-bg-page) rounded-(--radius-md) border border-(--color-border-default) space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <select
              value={portalType}
              onChange={(e) => setPortalType(e.target.value)}
              className="px-3 py-2 bg-(--color-bg-input) border border-(--color-border-default) rounded-(--radius-md) text-sm text-(--color-text-primary) focus:border-(--color-border-focus) focus:outline-none"
            >
              {portalTypes.map((t) => (
                <option key={t.value} value={t.value}>{t.label}</option>
              ))}
            </select>
            <input
              type="text"
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              placeholder="Display name"
              className="px-3 py-2 bg-(--color-bg-input) border border-(--color-border-default) rounded-(--radius-md) text-sm text-(--color-text-primary) placeholder:text-(--color-text-muted) focus:border-(--color-border-focus) focus:outline-none"
            />
          </div>
          <div className="relative">
            <input
              type={showCred ? 'text' : 'password'}
              value={credentials}
              onChange={(e) => setCredentials(e.target.value)}
              placeholder="Credentials (optional, stored encrypted)"
              className="w-full px-3 py-2 pr-10 bg-(--color-bg-input) border border-(--color-border-default) rounded-(--radius-md) text-sm text-(--color-text-primary) placeholder:text-(--color-text-muted) focus:border-(--color-border-focus) focus:outline-none"
            />
            <button
              type="button"
              onClick={() => setShowCred(!showCred)}
              className="absolute right-2.5 top-1/2 -translate-y-1/2 text-(--color-text-muted) hover:text-(--color-text-secondary)"
            >
              {showCred ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
            </button>
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => addMutation.mutate()}
              disabled={addMutation.isPending}
              className="px-4 py-2 text-sm bg-(--color-accent) hover:bg-(--color-accent-hover) text-(--color-text-inverse) rounded-(--radius-md) transition-colors disabled:opacity-50 shadow-sm"
            >
              {addMutation.isPending ? 'Adding...' : 'Add'}
            </button>
            <button
              onClick={() => setShowForm(false)}
              className="px-4 py-2 text-sm text-(--color-text-secondary) hover:text-(--color-text-primary) transition-colors"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {isLoading ? (
        <div className="space-y-2">
          {[1, 2].map((i) => (
            <div key={i} className="h-14 bg-(--color-bg-elevated) rounded-(--radius-md) animate-pulse" />
          ))}
        </div>
      ) : portals && portals.length > 0 ? (
        <div className="space-y-2">
          {portals.map((p) => (
            <div key={p.id} className="flex items-center justify-between px-4 py-3 bg-(--color-bg-page) rounded-(--radius-md) border border-(--color-border-subtle)">
              <div className="flex items-center gap-3">
                <span className="text-sm font-medium text-(--color-text-primary)">{p.display_name}</span>
                <span className="text-xs text-(--color-text-muted) capitalize">{p.portal_type}</span>
                <StatusBadge status={p.status} />
              </div>
              <button
                onClick={() => deleteMutation.mutate(p.id)}
                className="p-1.5 text-(--color-text-muted) hover:text-(--color-error) hover:bg-(--color-error-bg) rounded-(--radius-md) transition-all"
              >
                <Trash2 className="w-4 h-4" />
              </button>
            </div>
          ))}
        </div>
      ) : (
        <p className="text-sm text-(--color-text-muted) text-center py-4">
          No portals connected. Add one to start fetching jobs.
        </p>
      )}
    </div>
  );
}

// ─── API Token Section ───────────────────────────────────────
function ApiTokenManager() {
  const [newToken, setNewToken] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const queryClient = useQueryClient();

  const { data: tokenInfo } = useQuery({
    queryKey: ['api-token'],
    queryFn: async () => {
      const res = await api.get('/users/me/api-token');
      return res.data as { prefix: string; created_at: string; last_used_at: string | null } | null;
    },
  });

  const generateMutation = useMutation({
    mutationFn: async () => {
      const res = await api.post('/users/me/api-token');
      return res.data.token as string;
    },
    onSuccess: (token) => {
      setNewToken(token);
      queryClient.invalidateQueries({ queryKey: ['api-token'] });
    },
  });

  const revokeMutation = useMutation({
    mutationFn: async () => {
      await api.delete('/users/me/api-token');
    },
    onSuccess: () => {
      setNewToken(null);
      queryClient.invalidateQueries({ queryKey: ['api-token'] });
    },
  });

  const handleCopy = () => {
    if (newToken) {
      navigator.clipboard.writeText(newToken);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <div className="bg-(--color-bg-card) border border-(--color-border-default) rounded-(--radius-lg) p-6 shadow-(--shadow-card)">
      <div className="flex items-center gap-2 mb-3">
        <Key className="w-5 h-5 text-(--color-accent)" />
        <h2 className="text-base font-semibold text-(--color-text-primary)">Extension API Token</h2>
      </div>
      <p className="text-sm text-(--color-text-muted) mb-4">
        Generate a token for the Chrome extension to forward LinkedIn posts to your account.
      </p>

      {newToken && (
        <div className="mb-4 p-4 bg-(--color-warning-bg) rounded-(--radius-md) border border-(--color-warning)/15">
          <p className="text-sm text-(--color-warning) font-medium mb-2">
            ⚠️ Copy this token now — it won't be shown again!
          </p>
          <div className="flex items-center gap-2">
            <code className="flex-1 text-xs bg-(--color-bg-page) px-3 py-2 rounded-(--radius-sm) font-mono text-(--color-text-primary) break-all select-all border border-(--color-border-subtle)">
              {newToken}
            </code>
            <button
              onClick={handleCopy}
              className="p-2 bg-(--color-bg-page) border border-(--color-border-subtle) rounded-(--radius-md) hover:bg-(--color-bg-elevated) transition-colors"
            >
              {copied ? <Check className="w-4 h-4 text-(--color-success)" /> : <Copy className="w-4 h-4 text-(--color-text-muted)" />}
            </button>
          </div>
        </div>
      )}

      {tokenInfo ? (
        <div className="flex items-center justify-between px-4 py-3 bg-(--color-bg-page) rounded-(--radius-md) border border-(--color-border-subtle)">
          <div>
            <code className="text-sm font-mono text-(--color-text-primary)">{tokenInfo.prefix}</code>
            <p className="text-xs text-(--color-text-muted) mt-0.5">
              Last used: {tokenInfo.last_used_at ? new Date(tokenInfo.last_used_at).toLocaleDateString() : 'Never'}
            </p>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => generateMutation.mutate()}
              disabled={generateMutation.isPending}
              className="flex items-center gap-1 px-3 py-1.5 text-xs bg-(--color-accent) hover:bg-(--color-accent-hover) text-(--color-text-inverse) rounded-(--radius-md) transition-colors disabled:opacity-50 shadow-sm"
            >
              <RefreshCw className="w-3 h-3" /> Rotate
            </button>
            <button
              onClick={() => revokeMutation.mutate()}
              disabled={revokeMutation.isPending}
              className="flex items-center gap-1 px-3 py-1.5 text-xs text-(--color-error) bg-(--color-error-bg) hover:bg-(--color-error-subtle) rounded-(--radius-md) transition-colors"
            >
              <Trash2 className="w-3 h-3" /> Revoke
            </button>
          </div>
        </div>
      ) : (
        <button
          onClick={() => generateMutation.mutate()}
          disabled={generateMutation.isPending}
          className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-(--color-accent) hover:bg-(--color-accent-hover) text-(--color-text-inverse) font-medium rounded-(--radius-md) transition-colors disabled:opacity-50 shadow-sm"
        >
          {generateMutation.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Key className="w-4 h-4" />}
          Generate Token
        </button>
      )}
    </div>
  );
}

// ─── Profile Section ─────────────────────────────────────────
function ProfileSection() {
  const { user } = useAuthStore();
  const [name, setName] = useState(user?.name || '');
  const [roles, setRoles] = useState(user?.target_roles?.join(', ') || '');
  const [locations, setLocations] = useState(user?.target_locations?.join(', ') || '');
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  const handleSave = async () => {
    setSaving(true);
    try {
      const res = await api.put('/users/me', {
        name: name || undefined,
        target_roles: roles ? roles.split(',').map((r) => r.trim()).filter(Boolean) : undefined,
        target_locations: locations ? locations.split(',').map((l) => l.trim()).filter(Boolean) : undefined,
      });
      useAuthStore.getState().setUser(res.data);
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } catch {
      // handle error
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="bg-(--color-bg-card) border border-(--color-border-default) rounded-(--radius-lg) p-6 shadow-(--shadow-card)">
      <div className="flex items-center gap-2 mb-4">
        <Settings className="w-5 h-5 text-(--color-accent)" />
        <h2 className="text-base font-semibold text-(--color-text-primary)">Profile & Preferences</h2>
      </div>
      <div className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-(--color-text-secondary) mb-1">Name</label>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Your name"
            className="w-full px-3 py-2 bg-(--color-bg-input) border border-(--color-border-default) rounded-(--radius-md) text-sm text-(--color-text-primary) placeholder:text-(--color-text-muted) focus:border-(--color-border-focus) focus:outline-none focus:shadow-(--shadow-glow) transition-all"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-(--color-text-secondary) mb-1">
            Target Roles <span className="text-(--color-text-muted) font-normal">(comma-separated)</span>
          </label>
          <input
            type="text"
            value={roles}
            onChange={(e) => setRoles(e.target.value)}
            placeholder="Software Engineer, Backend Developer, SRE"
            className="w-full px-3 py-2 bg-(--color-bg-input) border border-(--color-border-default) rounded-(--radius-md) text-sm text-(--color-text-primary) placeholder:text-(--color-text-muted) focus:border-(--color-border-focus) focus:outline-none focus:shadow-(--shadow-glow) transition-all"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-(--color-text-secondary) mb-1">
            Target Locations <span className="text-(--color-text-muted) font-normal">(comma-separated)</span>
          </label>
          <input
            type="text"
            value={locations}
            onChange={(e) => setLocations(e.target.value)}
            placeholder="New York, San Francisco, Remote"
            className="w-full px-3 py-2 bg-(--color-bg-input) border border-(--color-border-default) rounded-(--radius-md) text-sm text-(--color-text-primary) placeholder:text-(--color-text-muted) focus:border-(--color-border-focus) focus:outline-none focus:shadow-(--shadow-glow) transition-all"
          />
        </div>
        <button
          onClick={handleSave}
          disabled={saving}
          className="flex items-center gap-2 px-4 py-2 bg-(--color-accent) hover:bg-(--color-accent-hover) text-(--color-text-inverse) text-sm font-medium rounded-(--radius-md) transition-colors disabled:opacity-50 shadow-sm"
        >
          {saving ? <Loader2 className="w-4 h-4 animate-spin" /> :
           saved ? <><Check className="w-4 h-4" /> Saved!</> : 'Save Preferences'}
        </button>
      </div>
    </div>
  );
}

// ─── Page ────────────────────────────────────────────────────
export function JobSourcesPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-(--color-text-primary) flex items-center gap-2">
          <Settings className="w-5 h-5 text-(--color-accent)" />
          Job Sources & Settings
        </h1>
        <p className="text-sm text-(--color-text-muted) mt-0.5">
          Configure your resume, job portals, and extension API token.
        </p>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <ProfileSection />
        <ResumeUpload />
      </div>
      <PortalManager />
      <ApiTokenManager />
    </div>
  );
}
