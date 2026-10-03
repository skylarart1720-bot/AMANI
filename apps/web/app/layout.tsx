import './globals.css';
import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'AMANI',
  description: 'Rights & wellbeing support platform',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
