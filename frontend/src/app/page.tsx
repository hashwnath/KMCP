'use client';

import Link from 'next/link';

export default function Home() {
  return (
    <main className="page-enter">
      <section className="container py-14 sm:py-20">
        <div className="grid gap-8 md:grid-cols-[1.2fr_0.8fr] items-center">
          <div className="stagger">
            <p className="inline-flex items-center rounded-full px-4 py-1 text-sm font-semibold mb-4" style={{ background: '#e8f4f2', color: 'var(--primary-strong)' }}>
              Built for teams that ship with AI
            </p>
            <h1 className="text-4xl sm:text-6xl leading-tight mb-6" style={{ fontFamily: 'var(--font-display), sans-serif' }}>
              Turn internal docs into a trusted <span style={{ color: 'var(--primary)' }}>MCP endpoint</span>
            </h1>
            <p className="text-lg sm:text-xl max-w-2xl mb-8" style={{ color: 'var(--muted)' }}>
              Connect your knowledge once. Let VS Code, Claude, Cursor, and custom agents query the same reliable source of truth.
            </p>
            <div className="flex flex-wrap gap-3">
              <Link href="/signup" className="btn-primary">Start Free</Link>
              <Link href="/dashboard/connect" className="btn-secondary">See Integration Guide</Link>
            </div>
          </div>

          <div className="card p-6 sm:p-8 stagger">
            <h3 className="text-lg font-semibold mb-3" style={{ fontFamily: 'var(--font-display), sans-serif' }}>Live Value Snapshot</h3>
            <div className="grid grid-cols-2 gap-3 text-sm">
              <div className="rounded-xl p-4" style={{ background: '#f0f7ee' }}>
                <div style={{ color: 'var(--muted)' }}>Setup time</div>
                <div className="text-2xl font-bold">~8 min</div>
              </div>
              <div className="rounded-xl p-4" style={{ background: '#ecf8f6' }}>
                <div style={{ color: 'var(--muted)' }}>Source types</div>
                <div className="text-2xl font-bold">6</div>
              </div>
              <div className="rounded-xl p-4" style={{ background: '#fff2e8' }}>
                <div style={{ color: 'var(--muted)' }}>Protocols</div>
                <div className="text-2xl font-bold">MCP + HTTP</div>
              </div>
              <div className="rounded-xl p-4" style={{ background: '#edf2e1' }}>
                <div style={{ color: 'var(--muted)' }}>Search quality</div>
                <div className="text-2xl font-bold">Hybrid</div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="container pb-8">
        <div className="card p-6 sm:p-8 max-w-4xl mx-auto">
          <h3 className="text-xl font-bold mb-2" style={{ fontFamily: 'var(--font-display), sans-serif' }}>Try it now, no signup needed</h3>
          <p className="text-sm mb-4" style={{ color: 'var(--muted)' }}>Pre-indexed docs include Stripe, MongoDB, FastAPI, Tailwind, and Redis. Drop this in your MCP config:</p>
          <pre className="p-4 rounded-xl text-xs overflow-x-auto text-left" style={{ background: '#152014', color: '#d0f9e8' }}>{JSON.stringify({
            mcpServers: {
              StripeDocs: {
                url: 'https://mcp.knowledgemcp.io/mcp/stripe-docs',
                type: 'http',
                headers: { 'x-api-key': 'demo-public-key' },
              },
            },
          }, null, 2)}</pre>
        </div>
      </section>

      <section className="container py-14 sm:py-20">
        <h2 className="text-3xl sm:text-4xl text-center mb-12" style={{ fontFamily: 'var(--font-display), sans-serif' }}>A focused 3-step flow</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 stagger">
          {[
            ['01', 'Add your docs', 'Paste URLs, upload files, or connect wiki/cloud/git sources.'],
            ['02', 'Index automatically', 'Content is chunked, embedded, and optimized for retrieval quality.'],
            ['03', 'Connect any agent', 'Copy one snippet and your assistants can query your documentation.'],
          ].map(([n, t, d]) => (
            <div key={n} className="card p-7">
              <div className="text-sm font-bold mb-3" style={{ color: 'var(--accent)' }}>{n}</div>
              <h3 className="text-xl font-semibold mb-2" style={{ fontFamily: 'var(--font-display), sans-serif' }}>{t}</h3>
              <p style={{ color: 'var(--muted)' }}>{d}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="container pb-20">
        <h2 className="text-3xl sm:text-4xl text-center mb-12" style={{ fontFamily: 'var(--font-display), sans-serif' }}>Simple pricing, clear limits</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 max-w-4xl mx-auto">
          <div className="card p-8">
            <h3 className="text-2xl font-bold mb-2" style={{ fontFamily: 'var(--font-display), sans-serif' }}>Free</h3>
            <p className="text-3xl font-bold mb-6" style={{ color: 'var(--primary)' }}>$0<span className="text-base" style={{ color: 'var(--muted)' }}>/mo</span></p>
            <ul className="space-y-2 mb-8" style={{ color: 'var(--muted)' }}>
              <li>500 pages indexed</li>
              <li>1,000 queries per month</li>
              <li>1 source included</li>
              <li>Basic analytics</li>
            </ul>
            <Link href="/signup" className="btn-secondary w-full text-center">Get Started</Link>
          </div>
          <div className="card p-8 relative" style={{ borderColor: '#149d8f' }}>
            <div className="absolute top-4 right-4 px-3 py-1 rounded-full text-xs font-bold" style={{ background: '#e4fbf7', color: '#0b4e46' }}>Most popular</div>
            <h3 className="text-2xl font-bold mb-2" style={{ fontFamily: 'var(--font-display), sans-serif' }}>Pro</h3>
            <p className="text-3xl font-bold mb-6" style={{ color: 'var(--primary)' }}>$99<span className="text-base" style={{ color: 'var(--muted)' }}>/mo</span></p>
            <ul className="space-y-2 mb-8" style={{ color: 'var(--muted)' }}>
              <li>Unlimited pages</li>
              <li>Unlimited queries</li>
              <li>Unlimited sources</li>
              <li>Advanced analytics</li>
              <li>Priority support</li>
            </ul>
            <Link href="/signup" className="btn-primary w-full text-center">Start Pro</Link>
          </div>
        </div>
      </section>
    </main>
  );
}
