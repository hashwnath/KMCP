'use client';
import Link from 'next/link';
import { useEffect, useState } from 'react';
import { getMe, getOverview, getSources } from '@/lib/api';

export default function DashboardPage() {
  const [me, setMe] = useState<any>(null);
  const [overview, setOverview] = useState<any>(null);
  const [sources, setSources] = useState<any[]>([]);

  useEffect(() => {
    getMe().then(r => setMe(r.data));
    getOverview().then(r => setOverview(r.data));
    getSources().then(r => setSources((r.data as any)?.sources ?? []));
  }, []);

  const anyIndexing = sources.some((s: any) => s.status === 'indexing' || s.status === 'crawling' || s.status === 'pending');
  const allReady = sources.length > 0 && sources.every((s: any) => s.status === 'ready');

  return (
    <main className="container py-10 page-enter">
      <div className="mb-8">
        <p className="text-sm font-semibold" style={{ color: 'var(--accent)' }}>Workspace overview</p>
        <h1 className="text-4xl font-bold" style={{ fontFamily: 'var(--font-display), sans-serif' }}>Dashboard</h1>
      </div>

      {/* Status Card */}
      <div className="card p-6 mb-8" style={allReady ? { borderColor: '#2a8f64', background: '#eefaf4' } : anyIndexing ? { borderColor: '#b88911', background: '#fff7e8' } : {}}>
        <div className="flex items-center gap-3">
          <span className="text-2xl">{allReady ? '✅' : anyIndexing ? '⏳' : '📭'}</span>
          <div>
            <h2 className="text-lg font-bold">
              {allReady ? 'Your MCP endpoint is READY' : anyIndexing ? 'Indexing in progress...' : sources.length === 0 ? 'No sources added yet' : 'Endpoint status unknown'}
            </h2>
            <p className="text-sm" style={{ color: 'var(--muted)' }}>
              {sources.length} source{sources.length !== 1 ? 's' : ''} connected
              {overview?.last_sync ? ` · Last sync: ${new Date(overview.last_sync).toLocaleDateString()}` : ''}
            </p>
          </div>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-10 stagger">
        <div className="card p-6"><div className="text-sm mb-2" style={{ color: 'var(--muted)' }}>Queries Today</div><div className="text-3xl font-bold">{overview?.total_queries_today ?? '—'}</div></div>
        <div className="card p-6"><div className="text-sm mb-2" style={{ color: 'var(--muted)' }}>Queries This Week</div><div className="text-3xl font-bold">{overview?.total_queries_week ?? '—'}</div></div>
        <div className="card p-6"><div className="text-sm mb-2" style={{ color: 'var(--muted)' }}>Docs Indexed</div><div className="text-3xl font-bold">{overview?.total_docs_indexed ?? '—'}</div></div>
        <div className="card p-6"><div className="text-sm mb-2" style={{ color: 'var(--muted)' }}>Last Sync</div><div className="text-lg font-bold">{overview?.last_sync ? new Date(overview.last_sync).toLocaleString() : '—'}</div></div>
      </div>

      {/* MCP Endpoint */}
      <div className="card p-8 mb-10">
        <h2 className="text-2xl font-bold mb-4" style={{ fontFamily: 'var(--font-display), sans-serif' }}>Your MCP Endpoint</h2>
        <div className="flex items-center gap-2 mb-4">
          <code className="flex-1 p-4 rounded-xl text-sm break-all" style={{ background: '#eef3e5' }}>https://mcp.knowledgemcp.io/mcp/{me?.slug ?? 'your-slug'}</code>
          <button onClick={() => navigator.clipboard.writeText(`https://mcp.knowledgemcp.io/mcp/${me?.slug ?? ''}`)} className="btn-secondary px-3 py-2 text-sm">Copy</button>
        </div>
        <details className="mb-4">
          <summary className="cursor-pointer hover:underline font-medium" style={{ color: 'var(--primary)' }}>Show mcp.json snippet</summary>
          <pre className="p-4 rounded-xl text-xs overflow-x-auto mt-2" style={{ background: '#152014', color: '#d0f9e8' }}>{JSON.stringify({ "mcpServers": { [me?.name ?? "MyDocs"]: { "url": `https://mcp.knowledgemcp.io/mcp/${me?.slug ?? 'your-slug'}`, "type": "http", "headers": { "x-api-key": me?.api_key ?? "sk-..." } } } }, null, 2)}</pre>
        </details>
        <Link href="/dashboard/connect" className="hover:underline" style={{ color: 'var(--primary)' }}>View full integration guide →</Link>
      </div>

      {/* Quick Actions */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Link href="/dashboard/sources" className="card p-8 transition" style={{ borderColor: '#b8d7ce' }}><h3 className="text-xl font-bold mb-2">Manage Sources</h3><p style={{ color: 'var(--muted)' }}>Add or remove documentation sources</p></Link>
        <Link href="/dashboard/analytics" className="card p-8 transition" style={{ borderColor: '#f1cfbe' }}><h3 className="text-xl font-bold mb-2">View Analytics</h3><p style={{ color: 'var(--muted)' }}>Query volumes, top searches, content gaps</p></Link>
      </div>
    </main>
  );
}
