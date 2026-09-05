import type { Metadata } from 'next';
import './globals.css';
export const metadata: Metadata = {
  title: 'DocFlow — Proposal workspace',
  description:
    'Document generation and revision-specific approvals for a fictional consulting agency.',
};
export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
