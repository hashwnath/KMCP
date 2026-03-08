'use client';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';
import { clearToken, getToken } from '@/lib/auth';

export default function Navbar() {
  const router = useRouter();
  const [isAuth, setIsAuth] = useState(false);
  const [dark, setDark] = useState(false);
  useEffect(() => {
    setIsAuth(!!getToken());
    const saved = localStorage.getItem('theme');
    const prefersDark = saved === 'dark' || (!saved && window.matchMedia('(prefers-color-scheme: dark)').matches);
    setDark(prefersDark);
    document.documentElement.classList.toggle('dark', prefersDark);
  }, []);
  const toggleTheme = () => {
    const next = !dark;
    setDark(next);
    document.documentElement.classList.toggle('dark', next);
    localStorage.setItem('theme', next ? 'dark' : 'light');
  };
  return (
    <nav className="sticky top-0 z-40 border-b" style={{ background: dark ? 'rgba(15, 26, 20, 0.88)' : 'rgba(246, 248, 241, 0.86)', borderColor: 'var(--border)', backdropFilter: 'blur(8px)' }}>
      <div className="container flex flex-wrap justify-between items-center gap-3 py-4">
        <Link href="/" className="flex items-center gap-2 text-xl font-bold" style={{ color: 'var(--primary-strong)', fontFamily: 'var(--font-display), sans-serif' }}>
          <span className="inline-flex h-8 w-8 items-center justify-center rounded-lg text-white" style={{ background: 'linear-gradient(135deg, var(--primary), var(--accent))' }}>K</span>
          KnowledgeMCP
        </Link>
        <div className="flex gap-3 sm:gap-6 items-center text-sm sm:text-base" style={{ color: 'var(--muted)' }}>
          <button onClick={toggleTheme} className="p-2 rounded-lg transition hover:opacity-80" title="Toggle theme" aria-label="Toggle dark mode">
            {dark ? '☀️' : '🌙'}
          </button>
          {isAuth ? (<>
            <Link href="/dashboard" className="hover:opacity-100 opacity-85">Dashboard</Link>
            <Link href="/dashboard/sources" className="hover:opacity-100 opacity-85">Sources</Link>
            <Link href="/dashboard/analytics" className="hover:opacity-100 opacity-85">Analytics</Link>
            <Link href="/dashboard/settings" className="hover:opacity-100 opacity-85">Settings</Link>
            <button onClick={() => { clearToken(); router.push('/'); }} className="px-3 py-2 rounded-lg transition" style={{ color: '#922f17', background: '#fce7df' }}>Logout</button>
          </>) : (<>
            <Link href="/login" className="hover:opacity-100 opacity-85">Login</Link>
            <Link href="/signup" className="btn-primary text-sm">Start Free</Link>
          </>)}
        </div>
      </div>
    </nav>
  );
}
