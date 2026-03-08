import type { Metadata } from 'next';
import { Sora, Source_Sans_3 } from 'next/font/google';
import Navbar from '@/components/Navbar';
import './globals.css';

export const metadata: Metadata = { title: 'KnowledgeMCP', description: 'Give your docs an MCP endpoint' };

const sora = Sora({ subsets: ['latin'], variable: '--font-display', weight: ['500', '600', '700'] });
const sourceSans = Source_Sans_3({ subsets: ['latin'], variable: '--font-body', weight: ['400', '500', '600', '700'] });

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${sora.variable} ${sourceSans.variable}`}>
      <body style={{ fontFamily: 'var(--font-body), sans-serif' }}>
        <Navbar />
        {children}
      </body>
    </html>
  );
}
