'use client';
import { useEffect, useState } from 'react';
import { getOverview, getGaps, getTopQueries, getToolUsage } from '@/lib/api';

export default function AnalyticsPage() {
  const [overview, setOverview] = useState<any>(null);
  const [gaps, setGaps] = useState<any[]>([]);
  const [top, setTop] = useState<any[]>([]);
  const [toolUsage, setToolUsage] = useState<Record<string, number>>({});

  useEffect(() => {
    getOverview().then(r => setOverview(r.data));
    getGaps().then(r => setGaps((r.data as any)?.gaps ?? []));
    getTopQueries().then(r => setTop((r.data as any)?.queries ?? []));
    getToolUsage().then(r => setToolUsage((r.data as any)?.usage ?? {}));
  }, []);

  const totalToolCalls = Object.values(toolUsage).reduce((a, b) => a + b, 0);

  return (
    <main className="container py-10">
      <h1 className="text-4xl font-bold mb-10">Analytics</h1>

      {/* Summary stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-10">
        <div className="card p-6"><div className="text-sm text-gray-600 mb-2">Queries Today</div><div className="text-3xl font-bold">{overview?.total_queries_today ?? 0}</div></div>
        <div className="card p-6"><div className="text-sm text-gray-600 mb-2">Queries This Week</div><div className="text-3xl font-bold">{overview?.total_queries_week ?? 0}</div></div>
        <div className="card p-6"><div className="text-sm text-gray-600 mb-2">Docs Indexed</div><div className="text-3xl font-bold">{overview?.total_docs_indexed ?? 0}</div></div>
        <div className="card p-6"><div className="text-sm text-gray-600 mb-2">Total Tool Calls</div><div className="text-3xl font-bold">{totalToolCalls}</div></div>
      </div>

      {/* Tool Usage Breakdown */}
      <div className="card p-6 mb-10">
        <h2 className="text-xl font-bold mb-4">Tool Usage Breakdown</h2>
        {totalToolCalls === 0 ? <p className="text-gray-500">No tool calls yet.</p> : (
          <div className="space-y-3">
            {Object.entries(toolUsage).sort((a, b) => b[1] - a[1]).map(([tool, count]) => (
              <div key={tool}>
                <div className="flex justify-between text-sm mb-1"><span className="font-medium">{tool}</span><span>{count} ({totalToolCalls > 0 ? Math.round(count / totalToolCalls * 100) : 0}%)</span></div>
                <div className="w-full bg-gray-200 rounded-full h-3"><div className="bg-blue-600 h-3 rounded-full" style={{ width: `${totalToolCalls > 0 ? (count / totalToolCalls * 100) : 0}%` }} /></div>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
        {/* Top Queries */}
        <div className="card p-6"><h2 className="text-xl font-bold mb-4">Top Queries</h2>
          {top.length === 0 ? <p className="text-gray-500">No data yet.</p> : <table className="w-full text-sm"><thead><tr><th className="text-left py-1">Query</th><th className="text-right py-1">Count</th></tr></thead><tbody>{top.map((q: any, i: number) => <tr key={i} className="border-t"><td className="py-2">{q.query}</td><td className="text-right py-2 font-medium">{q.count}</td></tr>)}</tbody></table>}
        </div>

        {/* Content Gaps */}
        <div className="card p-6"><h2 className="text-xl font-bold mb-4">Content Gaps <span className="text-xs bg-red-100 text-red-600 px-2 py-1 rounded-full ml-2">Action needed</span></h2>
          <p className="text-sm text-gray-500 mb-3">Queries where agents got 0-2 results — your docs may be missing this content.</p>
          {gaps.length === 0 ? <p className="text-gray-500">No gaps detected.</p> : <table className="w-full text-sm"><thead><tr><th className="text-left py-1">Query</th><th className="text-right py-1">Times Asked</th><th className="text-right py-1">Avg Results</th></tr></thead><tbody>{gaps.map((g: any, i: number) => <tr key={i} className="border-t"><td className="py-2">{g.query}</td><td className="text-right py-2">{g.count}</td><td className="text-right py-2 text-red-600 font-medium">{g.avg_results}</td></tr>)}</tbody></table>}
        </div>
      </div>
    </main>
  );
}
