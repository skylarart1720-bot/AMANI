import './globals.css';
import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'AMANI Moderator Dashboard',
  description: 'Moderator queue dashboard',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
