'use client';
import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import { useEffect, useState } from 'react';
import { login, requestMagicLink, verifyMagicLink } from '@/lib/api';
import { setToken } from '@/lib/auth';

export default function LoginPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [email, setEmail] = useState(''); const [password, setPassword] = useState('');
  const [error, setError] = useState(''); const [loading, setLoading] = useState(false);
  const [magicRequested, setMagicRequested] = useState(false);

  useEffect(() => {
    const magicToken = searchParams.get('magic_token');
    if (!magicToken) return;
    (async () => {
      setLoading(true);
      const { data, error: err } = await verifyMagicLink(magicToken) as any;
      if (err) {
        setError(err);
        setLoading(false);
        return;
      }
      if (data?.token) {
        setToken(data.token);
        router.push('/dashboard');
        return;
      }
      setError('Magic link is invalid or expired.');
      setLoading(false);
    })();
  }, [router, searchParams]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault(); setError(''); setLoading(true);
    const { data, error: err } = await login(email, password) as any;
    if (err) { setError(err); setLoading(false); return; }
    if (data?.token) { setToken(data.token); router.push('/dashboard'); }
    else { setError('No token received'); setLoading(false); }
  };

  const handleMagicLink = async () => {
    setError('');
    if (!email) {
      setError('Enter your email first.');
      return;
    }
    setLoading(true);
    const { error: err } = await requestMagicLink(email);
    if (err) {
      setError(err);
      setLoading(false);
      return;
    }
    setMagicRequested(true);
    setLoading(false);
  };

  return (
    <main className="min-h-screen flex items-center justify-center page-enter px-4 py-10">
      <div className="card w-full max-w-lg p-8 sm:p-10">
        <p className="text-sm font-semibold mb-2" style={{ color: 'var(--accent)' }}>Welcome back</p>
        <h1 className="text-3xl sm:text-4xl mb-2" style={{ fontFamily: 'var(--font-display), sans-serif' }}>Sign in to your workspace</h1>
        <p className="text-sm mb-6" style={{ color: 'var(--muted)' }}>Use password login or request a magic link for faster access.</p>

        {error && <div role="alert" className="px-4 py-3 rounded-xl mb-4" style={{ background: '#fde8e3', color: '#8e2f1d', border: '1px solid #f4c6ba' }}>{error}</div>}
        {magicRequested && <div role="status" className="px-4 py-3 rounded-xl mb-4" style={{ background: '#e7f7f4', color: '#0d584e', border: '1px solid #b8e3db' }}>If your account exists, a magic link has been issued.</div>}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-semibold mb-2">Work email</label>
            <input type="email" value={email} onChange={e=>setEmail(e.target.value)} required className="w-full px-4 py-3 border rounded-xl" autoComplete="email" />
          </div>
          <div>
            <label className="block text-sm font-semibold mb-2">Password</label>
            <input type="password" value={password} onChange={e=>setPassword(e.target.value)} required className="w-full px-4 py-3 border rounded-xl" autoComplete="current-password" />
          </div>
          <button type="submit" disabled={loading} className="btn-primary w-full disabled:opacity-50">{loading ? 'Signing in...' : 'Sign in'}</button>
        </form>

        <div className="my-5 flex items-center gap-3" style={{ color: 'var(--muted)' }}>
          <div className="h-px flex-1" style={{ background: 'var(--border)' }} />
          <span className="text-xs uppercase tracking-wide">or</span>
          <div className="h-px flex-1" style={{ background: 'var(--border)' }} />
        </div>

        <button onClick={handleMagicLink} disabled={loading} className="btn-secondary w-full disabled:opacity-50">Send magic link</button>
        <p className="text-center mt-6" style={{ color: 'var(--muted)' }}>No account? <Link href="/signup" style={{ color: 'var(--primary)' }} className="font-semibold hover:underline">Create one</Link></p>
      </div>
    </main>
  );
}
