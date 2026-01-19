import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import './globals.css';
import { Providers } from '@/components/providers';
import { Toaster } from '@terragon/ui';

const inter = Inter({ subsets: ['latin'] });

export const metadata: Metadata = {
  title: 'Terragon - AI Coding Agents',
  description: 'Delegate coding tasks to AI background agents. Get pull requests, not promises.',
  keywords: ['AI', 'coding', 'agents', 'automation', 'development', 'Claude', 'GPT'],
  authors: [{ name: 'Terragon Labs' }],
  openGraph: {
    title: 'Terragon - AI Coding Agents',
    description: 'Delegate coding tasks to AI background agents. Get pull requests, not promises.',
    type: 'website',
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={inter.className}>
        <Providers>
          {children}
          <Toaster />
        </Providers>
      </body>
    </html>
  );
}
