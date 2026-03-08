'use client';
import { useEffect, useState } from 'react';
import { getSettings, updateSettings, regenerateApiKey } from '@/lib/api';

export default function SettingsPage() {
  const [settings, setSettings] = useState<any>(null);
  const [slug, setSlug] = useState('');
  const [rateLimit, setRateLimit] = useState('100');
  const [maxDocs, setMaxDocs] = useState('500');

  useEffect(() => {
    getSettings().then(r => {
      const d = r.data as any;
      setSettings(d);
      setSlug(d?.slug ?? '');
      setRateLimit(String(d?.rate_limit ?? 100));
      setMaxDocs(String(d?.max_docs ?? 500));
    });
  }, []);

  const handleSave = async () => {
    await updateSettings({ slug, rate_limit: parseInt(rateLimit), max_docs: parseInt(maxDocs) });
    alert('Settings saved');
  };

  const handleRegen = async () => {
    if (confirm('Regenerate API key? The old key will stop working immediately.')) {
      const r = await regenerateApiKey();
      setSettings({ ...settings, ...(r.data as any) });
    }
  };

  return (
    <main className="container py-10 page-enter">
      <p className="text-sm font-semibold" style={{ color: 'var(--accent)' }}>Controls</p>
      <h1 className="text-4xl font-bold mb-8" style={{ fontFamily: 'var(--font-display), sans-serif' }}>Settings</h1>
      <div className="card p-8 space-y-6 max-w-xl">
        {/* API Key */}
        <div>
          <label className="block text-sm font-medium mb-2">API Key</label>
          <div className="flex gap-2">
            <input readOnly value={settings?.api_key ?? ''} className="flex-1 px-4 py-2 border rounded-xl bg-gray-50 font-mono text-sm" />
            <button onClick={() => navigator.clipboard.writeText(settings?.api_key ?? '')} className="btn-secondary px-3 py-2 text-sm">Copy</button>
            <button onClick={handleRegen} className="px-4 py-2 rounded-xl text-sm" style={{ background: '#fde8e3', color: '#8e2f1d' }}>Regenerate</button>
          </div>
        </div>

        {/* Endpoint Slug */}
        <div>
          <label className="block text-sm font-medium mb-2">Endpoint Slug</label>
          <div className="flex items-center gap-2">
            <span className="text-sm text-gray-500">https://mcp.knowledgemcp.io/mcp/</span>
            <input value={slug} onChange={e => setSlug(e.target.value)} className="flex-1 px-4 py-2 border rounded-xl" />
          </div>
        </div>

        {/* Rate Limit */}
        <div>
          <label className="block text-sm font-medium mb-2">Rate Limit (queries/hour)</label>
          <input type="number" value={rateLimit} onChange={e => setRateLimit(e.target.value)} className="w-full px-4 py-2 border rounded-xl" />
        </div>

        {/* Max Docs */}
        <div>
          <label className="block text-sm font-medium mb-2">Max Documents</label>
          <input type="number" value={maxDocs} onChange={e => setMaxDocs(e.target.value)} className="w-full px-4 py-2 border rounded-xl" />
        </div>

        <button onClick={handleSave} className="btn-primary w-full">Save Changes</button>
      </div>
    </main>
  );
}
