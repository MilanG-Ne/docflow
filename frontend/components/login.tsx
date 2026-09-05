'use client';
import { useState } from 'react';
import Link from 'next/link';
import { ArrowRight, FileText, Layers, ShieldCheck } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import { api, type Identity } from '@/lib/api';

export function Brand() {
  return (
    <Link className="wordmark" href="/" aria-label="DocFlow home">
      <span className="brand-icon">
        <Layers size={22} />
      </span>
      docflow<span className="brand-dot">.</span>
    </Link>
  );
}
export function Login({
  demo,
  onLogin,
}: {
  demo: boolean;
  onLogin: (identity: Identity) => void;
}) {
  const [role, setRole] = useState('author');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  async function login(event: React.SyntheticEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError('');
    try {
      onLogin(
        await api<Identity>('/login', {
          method: 'POST',
          body: {
            email: demo
              ? role === 'author'
                ? 'alex@alder.example'
                : 'jamie@alder.example'
              : email,
            password: demo ? 'proposal-demo-2026' : password,
          },
        }),
      );
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not sign in');
    } finally {
      setBusy(false);
    }
  }
  return (
    <main className="entry">
      <section className="entry-brand">
        <Brand />
        <div className="entry-copy">
          <p className="eyebrow">ALDER & CO. / PROPOSAL WORKSPACE</p>
          <h1>
            Good work starts
            <br />
            with a clear proposal.
          </h1>
          <p>
            Bring the scope, fees, and review into one place. Every approval
            belongs to one exact revision.
          </p>
          <ol className="workflow">
            <li>
              <FileText />
              Write the proposal
            </li>
            <li>
              <Layers />
              Generate Word & PDF
            </li>
            <li>
              <ShieldCheck />
              Review and approve
            </li>
          </ol>
        </div>
        <p className="small">
          A fictional consultancy. A working document workflow.
        </p>
      </section>
      <section className="entry-form">
        <form className="login-panel" onSubmit={login}>
          <p className="eyebrow">WELCOME TO DOCFLOW</p>
          <h2>Your proposals, in order.</h2>
          <p className="muted">
            {demo
              ? 'Choose a demo account to explore both sides of the review process.'
              : 'Sign in with your workspace account.'}
          </p>
          {demo ? (
            <Tabs
              value={role}
              onValueChange={(value) => setRole(String(value))}
            >
              <TabsList className="login-tabs">
                <TabsTrigger value="author">Author</TabsTrigger>
                <TabsTrigger value="reviewer">Reviewer</TabsTrigger>
              </TabsList>
              <TabsContent value="author">
                <div className="account-avatar">AN</div>
                <h3>Alex Novak</h3>
                <p className="muted">
                  Prepare proposals, generate files, and send revisions for
                  review.
                </p>
              </TabsContent>
              <TabsContent value="reviewer">
                <div className="account-avatar">JL</div>
                <h3>Jamie Lee</h3>
                <p className="muted">
                  Review the scope and fees, leave feedback, and approve a
                  revision.
                </p>
              </TabsContent>
            </Tabs>
          ) : (
            <div className="login-fields">
              <label>
                Email
                <input
                  required
                  type="email"
                  autoComplete="username"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                />
              </label>
              <label>
                Password
                <input
                  required
                  type="password"
                  autoComplete="current-password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                />
              </label>
            </div>
          )}
          <Button type="submit" className="login-button" disabled={busy}>
            {busy ? 'Signing in…' : 'Open workspace'}
            <ArrowRight />
          </Button>
          {error && (
            <p className="notice error" role="alert">
              {error}
            </p>
          )}
          <p className="small muted">
            {demo
              ? 'Demo accounts use fictional information. Changes are saved in your local database.'
              : 'Your session expires after eight hours.'}
          </p>
        </form>
      </section>
    </main>
  );
}
