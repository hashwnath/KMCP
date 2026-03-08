'use client';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useState } from 'react';
import { signup } from '@/lib/api';
import { setToken } from '@/lib/auth';

export default function SignupPage() {
  const router = useRouter();
  const [name, setName] = useState(''); const [email, setEmail] = useState('');
  const [password, setPassword] = useState(''); const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault(); setError(''); setLoading(true);
    const { data, error: err } = await signup(name, email, password) as any;
    if (err) { setError(err); setLoading(false); return; }
    if (data?.token) { setToken(data.token); router.push('/onboarding'); }
    else { setError('Signup failed'); setLoading(false); }
  };

  return (
    <main className="min-h-screen flex items-center justify-center page-enter px-4 py-10">
      <div className="card w-full max-w-xl p-8 sm:p-10">
        <p className="text-sm font-semibold mb-2" style={{ color: 'var(--accent)' }}>Create your workspace</p>
        <h1 className="text-3xl sm:text-4xl mb-2" style={{ fontFamily: 'var(--font-display), sans-serif' }}>Get started in minutes</h1>
        <p className="text-sm mb-6" style={{ color: 'var(--muted)' }}>We will create your tenant and take you directly to onboarding.</p>

        {error && <div role="alert" className="px-4 py-3 rounded-xl mb-4" style={{ background: '#fde8e3', color: '#8e2f1d', border: '1px solid #f4c6ba' }}>{error}</div>}
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-semibold mb-2">Full name</label>
            <input type="text" value={name} onChange={e=>setName(e.target.value)} required className="w-full px-4 py-3 border rounded-xl" autoComplete="name" />
          </div>
          <div>
            <label className="block text-sm font-semibold mb-2">Work email</label>
            <input type="email" value={email} onChange={e=>setEmail(e.target.value)} required className="w-full px-4 py-3 border rounded-xl" autoComplete="email" />
          </div>
          <div>
            <label className="block text-sm font-semibold mb-2">Password</label>
            <input type="password" value={password} onChange={e=>setPassword(e.target.value)} required className="w-full px-4 py-3 border rounded-xl" autoComplete="new-password" />
            <p className="text-xs mt-2" style={{ color: 'var(--muted)' }}>Use at least 8 characters with one number.</p>
          </div>
          <button type="submit" disabled={loading} className="btn-primary w-full disabled:opacity-50">{loading ? 'Creating workspace...' : 'Create account'}</button>
        </form>
        <p className="text-center mt-6" style={{ color: 'var(--muted)' }}>Already have an account? <Link href="/login" style={{ color: 'var(--primary)' }} className="font-semibold hover:underline">Sign in</Link></p>
      </div>
    </main>
  );
}
