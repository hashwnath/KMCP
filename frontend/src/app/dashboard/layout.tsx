'use client';
import { useRouter } from 'next/navigation';
import { useEffect } from 'react';
import { getToken } from '@/lib/auth';

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  useEffect(() => { if (!getToken()) router.push('/login'); }, [router]);
  return <>{children}</>;
}
