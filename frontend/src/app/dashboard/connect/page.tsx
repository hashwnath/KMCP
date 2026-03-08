'use client';
import { useEffect, useState } from 'react';
import { getMe } from '@/lib/api';

const tabs = ['VS Code / Copilot', 'Cursor', 'Claude Code', 'Claude Desktop', 'Generic'];

export default function ConnectPage() {
  const [me, setMe] = useState<any>(null); const [tab, setTab] = useState(0);
  useEffect(() => { getMe().then(r => setMe(r.data)); }, []);
  const url = `https://mcp.knowledgemcp.io/mcp/${me?.slug ?? 'your-slug'}`;
  const key = me?.api_key ?? 'sk-your-api-key';

  const snippets: Record<number, string> = {
    0: JSON.stringify({ "mcpServers": { [me?.name ?? "MyDocs"]: { "url": url, "type": "http", "headers": { "x-api-key": key } } } }, null, 2),
    1: `// .cursor/mcp.json\n${JSON.stringify({ "mcpServers": { [me?.name ?? "MyDocs"]: { "url": url, "type": "http", "headers": { "x-api-key": key } } } }, null, 2)}`,
    2: `// Claude Code MCP config\n${JSON.stringify({ "mcpServers": { [me?.name ?? "MyDocs"]: { "url": url, "type": "http", "headers": { "x-api-key": key } } } }, null, 2)}`,
    3: `// claude_desktop_config.json\n${JSON.stringify({ "mcpServers": { [me?.name ?? "MyDocs"]: { "command": "npx", "args": ["-y", "mcp-remote", url], "env": { "MCP_API_KEY": key } } } }, null, 2)}`,
    4: `POST ${url}\nHeaders: x-api-key: ${key}, content-type: application/json\n\n${JSON.stringify({ jsonrpc: "2.0", method: "tools/list", id: 1 }, null, 2)}`,
  };

  return (
    <main className="container py-10 page-enter">
      <p className="text-sm font-semibold" style={{ color: 'var(--accent)' }}>Integration</p>
      <h1 className="text-4xl font-bold mb-2" style={{ fontFamily: 'var(--font-display), sans-serif' }}>How to Connect</h1>
      <p className="mb-6" style={{ color: 'var(--muted)' }}>Pick your client, copy the snippet, then paste your endpoint and API key.</p>
      <div className="card p-5 mb-6 text-sm" style={{ color: 'var(--muted)' }}>
        <p className="font-semibold mb-2" style={{ color: 'var(--primary-strong)' }}>Quick steps</p>
        <ol className="list-decimal ml-5 space-y-1">
          <li>Select your client tab below.</li>
          <li>Copy the generated snippet.</li>
          <li>Paste it in your client MCP config file.</li>
          <li>Restart the client and run a `tools/list` check.</li>
        </ol>
      </div>
      <div className="flex gap-2 mb-6 flex-wrap">{tabs.map((t, i) => <button key={i} onClick={() => setTab(i)} className={`px-4 py-2 rounded-lg text-sm font-medium ${tab === i ? 'text-white' : 'bg-gray-200'}`} style={tab === i ? { background: 'var(--primary)' } : undefined}>{t}</button>)}</div>
      <div className="card p-6">
        <div className="flex justify-between items-center mb-3">
          <p className="text-sm" style={{ color: 'var(--muted)' }}>Selected profile: {tabs[tab]}</p>
          <button className="btn-secondary px-3 py-2 text-sm" onClick={() => navigator.clipboard.writeText(snippets[tab])}>Copy Snippet</button>
        </div>
        <pre className="p-4 rounded-xl text-xs overflow-x-auto whitespace-pre-wrap" style={{ background: '#152014', color: '#d0f9e8' }}>{snippets[tab]}</pre>
      </div>
    </main>
  );
}
