'use client';
import { useCallback, useEffect, useState } from 'react';
import { api, ApiError, type Identity } from '@/lib/api';
import { Login, Brand } from '@/components/login';
import { Workspace } from '@/components/workspace';
import { Button } from '@/components/ui/button';

export default function Home() {
  const [identity, setIdentity] = useState<Identity | null>(null);
  const [demo, setDemo] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [attempt, setAttempt] = useState(0);
  const logout = useCallback(() => setIdentity(null), []);
  useEffect(() => {
    const controller = new AbortController();
    Promise.all([
      api<{ demo_mode: boolean }>('/config', { signal: controller.signal }),
      api<Identity>('/me', { signal: controller.signal }).catch((e) => {
        if (e instanceof ApiError && e.status === 401) return null;
        throw e;
      }),
    ])
      .then(([config, user]) => {
        if (!controller.signal.aborted) {
          setDemo(config.demo_mode);
          setIdentity(user);
          setLoading(false);
        }
      })
      .catch((e) => {
        if (!controller.signal.aborted) {
          setError(
            e instanceof Error ? e.message : 'The service is unavailable',
          );
          setLoading(false);
        }
      });
    return () => controller.abort();
  }, [attempt]);
  if (loading || error)
    return (
      <main className="connection-state">
        <Brand />
        {loading ? (
          <output>
            <span className="spinner" />
            Connecting to your workspace…
          </output>
        ) : (
          <>
            <h1>The workspace is unavailable</h1>
            <p className="muted">{error}</p>
            <Button
              onClick={() => {
                setError('');
                setLoading(true);
                setAttempt(attempt + 1);
              }}
            >
              Try again
            </Button>
          </>
        )}
      </main>
    );
  return identity ? (
    <Workspace key={identity.user.id} identity={identity} onLogout={logout} />
  ) : (
    <Login demo={demo} onLogin={setIdentity} />
  );
}
