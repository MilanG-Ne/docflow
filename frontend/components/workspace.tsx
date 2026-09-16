'use client';
import { useCallback, useEffect, useRef, useState } from 'react';
import {
  FileText,
  Search,
  Plus,
  LogOut,
  ArrowLeft,
  FolderOpen,
  CheckCheck,
  Clock3,
  ArrowUpRight,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Brand } from '@/components/login';
import { ProposalDetail, Status } from '@/components/proposal-detail';
import { ProposalEditor } from '@/components/proposal-editor';
import {
  api,
  ApiError,
  blankContent,
  money,
  type Content,
  type Identity,
  type Proposal,
  type ProposalSummary,
  type Revision,
} from '@/lib/api';
import { registerTools, validateId } from '@/lib/webmcp';

export function Workspace({
  identity,
  onLogout,
}: {
  identity: Identity;
  onLogout: () => void;
}) {
  const [items, setItems] = useState<ProposalSummary[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [proposal, setProposal] = useState<Proposal | null>(null);
  const [query, setQuery] = useState('');
  const [filter, setFilter] = useState('all');
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [editor, setEditor] = useState<{
    initial: Content;
    number: number;
    proposalId?: string;
    expected?: number;
  } | null>(null);
  const selectedRef = useRef<string | null>(null);
  const sequence = useRef(0);
  const { csrf, user } = identity;

  const report = useCallback(
    (e: unknown) => {
      if (e instanceof ApiError && e.status === 401) {
        onLogout();
        return;
      }
      setError(e instanceof Error ? e.message : 'The service is unavailable');
    },
    [onLogout],
  );
  const refreshList = useCallback(async () => {
    const data = await api<ProposalSummary[]>('/proposals');
    setItems(data);
    return data;
  }, []);
  const openProposal = useCallback(async (id: string) => {
    const turn = ++sequence.current;
    const detail = await api<Proposal>(`/proposals/${id}`);
    if (turn === sequence.current) {
      selectedRef.current = id;
      setSelected(id);
      setProposal(detail);
      setEditor(null);
      setError('');
    }
    return detail;
  }, []);
  const refreshDetail = useCallback(async () => {
    const id = selectedRef.current;
    if (!id) return;
    const turn = sequence.current;
    const detail = await api<Proposal>(`/proposals/${id}`);
    if (turn === sequence.current && selectedRef.current === id)
      setProposal(detail);
  }, []);

  useEffect(() => {
    let active = true;
    api<ProposalSummary[]>('/proposals')
      .then((data) => {
        if (active) {
          setItems(data);
          setLoading(false);
        }
      })
      .catch((e) => {
        if (active) {
          report(e);
          setLoading(false);
        }
      });
    return () => {
      active = false;
    };
  }, [report]);
  useEffect(() => {
    const timer = setInterval(() => {
      void Promise.all([refreshList(), refreshDetail()]).catch(report);
    }, 3000);
    return () => clearInterval(timer);
  }, [refreshList, refreshDetail, report]);

  const submitById = useCallback(
    async (id: string) => {
      const detail = await api<Proposal>(`/proposals/${id}`);
      const revision = detail.revisions[0];
      await api(`/proposals/${id}/revisions/${revision.id}/submit`, {
        method: 'POST',
        csrf,
      });
      const [, updated] = await Promise.all([refreshList(), openProposal(id)]);
      setNotice(`Revision ${revision.number} was sent for review.`);
      return {
        proposal_id: id,
        revision: revision.number,
        state: updated.revisions[0].state,
      };
    },
    [csrf, refreshList, openProposal],
  );
  useEffect(
    () =>
      registerTools([
        {
          name: 'list_proposals',
          description: 'List proposals visible to the signed-in account.',
          inputSchema: {
            type: 'object',
            properties: {},
            additionalProperties: false,
          },
          annotations: { readOnlyHint: true, untrustedContentHint: true },
          execute: async (input) => {
            if (
              !input ||
              typeof input !== 'object' ||
              Array.isArray(input) ||
              Object.keys(input).length
            )
              throw new Error('Expected an empty object');
            return refreshList();
          },
        },
        {
          name: 'open_proposal',
          description:
            'Open an existing proposal in the visible workspace. Does not edit it.',
          inputSchema: {
            type: 'object',
            properties: { proposal_id: { type: 'string', format: 'uuid' } },
            required: ['proposal_id'],
            additionalProperties: false,
          },
          annotations: { readOnlyHint: true, untrustedContentHint: true },
          execute: async (input) => {
            const p = await openProposal(validateId(input));
            return {
              proposal_id: p.id,
              revision: p.latest_number,
              state: p.revisions[0].state,
            };
          },
        },
        ...(user.role === 'author'
          ? [
              {
                name: 'submit_proposal_for_review',
                description:
                  'Submit the latest generated draft for review, using the signed-in author account. Fails if generation is incomplete or the draft is no longer current.',
                inputSchema: {
                  type: 'object',
                  properties: {
                    proposal_id: { type: 'string', format: 'uuid' },
                  },
                  required: ['proposal_id'],
                  additionalProperties: false,
                },
                annotations: {
                  readOnlyHint: false,
                  untrustedContentHint: false,
                },
                execute: async (input: unknown) =>
                  submitById(validateId(input)),
              },
            ]
          : []),
      ]),
    [user.role, refreshList, openProposal, submitById],
  );

  async function action(
    revision: Revision,
    kind: 'submit' | 'review' | 'retry',
    decision?: string,
    comment?: string,
  ) {
    if (!proposal) return;
    setBusy(true);
    setError('');
    setNotice('');
    try {
      if (kind === 'submit') {
        // Submit the revision shown on screen; never silently advance to an unseen revision.
        await api(`/proposals/${proposal.id}/revisions/${revision.id}/submit`, {
          method: 'POST',
          csrf,
        });
      } else
        await api(
          `/proposals/${proposal.id}/revisions/${revision.id}/${kind}`,
          {
            method: 'POST',
            csrf,
            ...(kind === 'review'
              ? {
                  body: {
                    decision,
                    comment,
                    content_hash: revision.content_hash,
                  },
                }
              : {}),
          },
        );
      await Promise.all([refreshList(), refreshDetail()]);
      setNotice(
        kind === 'submit'
          ? `Revision ${revision.number} was sent for review.`
          : kind === 'retry'
            ? 'Generation queued again.'
            : decision === 'approved'
              ? `Revision ${revision.number} was approved.`
              : 'Changes requested. The author can prepare a new revision.',
      );
    } catch (e) {
      report(e);
    } finally {
      setBusy(false);
    }
  }
  async function save(content: Content) {
    if (!editor) return;
    const result = await api<Proposal>(
      editor.proposalId
        ? `/proposals/${editor.proposalId}/revisions`
        : '/proposals',
      {
        method: 'POST',
        csrf,
        body: editor.proposalId
          ? { expected_number: editor.expected, content }
          : content,
      },
    );
    setEditor(null);
    setProposal(result);
    setSelected(result.id);
    selectedRef.current = result.id;
    ++sequence.current;
    await refreshList();
    setNotice(
      `Revision ${result.latest_number} saved. Document generation is queued.`,
    );
  }
  function back() {
    ++sequence.current;
    selectedRef.current = null;
    setSelected(null);
    setProposal(null);
    setNotice('');
  }
  async function logout() {
    setBusy(true);
    try {
      await api('/logout', { method: 'POST', csrf });
      onLogout();
    } catch (e) {
      report(e);
    } finally {
      setBusy(false);
    }
  }
  const filtered = items.filter(
    (p) =>
      (filter === 'all' || p.state === filter) &&
      `${p.title} ${p.client_name}`.toLowerCase().includes(query.toLowerCase()),
  );
  return (
    <div className="workspace">
      <aside className="app-sidebar">
        <Brand />
        <p className="workspace-name">
          ALDER & CO.<span>Consulting workspace</span>
        </p>
        <nav aria-label="Workspace">
          <button
            className="nav-item active"
            onClick={() => {
              back();
              setEditor(null);
              setFilter('all');
            }}
          >
            <FileText size={18} />
            Proposals<span>{items.length}</span>
          </button>
          <button
            className="nav-item"
            onClick={() => {
              back();
              setEditor(null);
              setFilter('in_review');
            }}
          >
            <Clock3 size={18} />
            Awaiting review
            <span>{items.filter((i) => i.state === 'in_review').length}</span>
          </button>
          <button
            className="nav-item"
            onClick={() => {
              back();
              setEditor(null);
              setFilter('approved');
            }}
          >
            <CheckCheck size={18} />
            Approved
          </button>
        </nav>
        <div className="sidebar-bottom">
          <span className="demo-label">LOCAL DEMO</span>
          <p>
            Fictional clients.
            <br />
            Real proposal workflows.
          </p>
          <a
            href="https://github.com/MilanG-Ne/docflow"
            target="_blank"
            rel="noreferrer"
          >
            View source
            <ArrowUpRight size={15} />
          </a>
        </div>
      </aside>
      <div className="app-main">
        <header className="app-header">
          <div className="breadcrumbs">
            <span>Workspace</span>
            <span>/</span>
            <strong>Proposals</strong>
            {selected && (
              <>
                <span>/</span>
                <span>Revision {proposal?.latest_number}</span>
              </>
            )}
          </div>
          <div className="user-menu">
            <span className="user-avatar">
              {user.role === 'author' ? 'AN' : 'JL'}
            </span>
            <div>
              <strong>{user.name}</strong>
              <span>
                {user.role === 'author' ? 'Proposal author' : 'Reviewer'}
              </span>
            </div>
            <Button
              variant="ghost"
              size="icon"
              aria-label="Sign out"
              onClick={() => void logout()}
              disabled={busy}
            >
              <LogOut size={17} />
            </Button>
          </div>
        </header>
        <main className="workspace-content">
          {error && (
            <div className="notice error" role="alert">
              {error}
              <button
                className="inline-link"
                onClick={() => {
                  setError('');
                  void Promise.all([refreshList(), refreshDetail()]).catch(
                    report,
                  );
                }}
              >
                Try again
              </button>
            </div>
          )}
          {notice && !editor && (
            <output className="notice success">
              {notice}
              <button className="inline-link" onClick={() => setNotice('')}>
                Dismiss
              </button>
            </output>
          )}
          {editor ? (
            <ProposalEditor
              key={`${editor.proposalId ?? 'new'}-${editor.number}`}
              {...editor}
              onCancel={() => setEditor(null)}
              onSave={save}
            />
          ) : proposal ? (
            <>
              <Button variant="ghost" className="back-button" onClick={back}>
                <ArrowLeft />
                All proposals
              </Button>
              <ProposalDetail
                key={proposal.id}
                proposal={proposal}
                user={user}
                busy={busy}
                onEdit={() =>
                  setEditor({
                    initial: proposal.revisions[0].content,
                    number: proposal.latest_number + 1,
                    proposalId: proposal.id,
                    expected: proposal.latest_number,
                  })
                }
                onAction={action}
              />
            </>
          ) : (
            <>
              <div className="section-heading">
                <div>
                  <p className="eyebrow">PROPOSAL WORKSPACE</p>
                  <h1>From first draft to sign-off.</h1>
                  <p className="muted">
                    Keep the scope clear and every revision accounted for.
                  </p>
                </div>
                {user.role === 'author' && (
                  <Button
                    onClick={() =>
                      setEditor({ initial: blankContent, number: 1 })
                    }
                  >
                    <Plus />
                    New proposal
                  </Button>
                )}
              </div>
              <div className="overview-stats">
                <div>
                  <span>Total proposals</span>
                  <strong>{items.length.toString().padStart(2, '0')}</strong>
                  <FileText />
                </div>
                <div>
                  <span>Awaiting review</span>
                  <strong>
                    {items
                      .filter((p) => p.state === 'in_review')
                      .length.toString()
                      .padStart(2, '0')}
                  </strong>
                  <Clock3 />
                </div>
                <div>
                  <span>Latest revision approved</span>
                  <strong>
                    {items
                      .filter((p) => p.state === 'approved')
                      .length.toString()
                      .padStart(2, '0')}
                  </strong>
                  <CheckCheck />
                </div>
              </div>
              <section className="proposal-list">
                <div className="list-toolbar">
                  <div className="list-filters" aria-label="Filter proposals">
                    {[
                      ['all', 'All proposals'],
                      ['draft', 'Drafts'],
                      ['in_review', 'In review'],
                      ['approved', 'Approved'],
                      ['changes_requested', 'Changes'],
                    ].map(([value, label]) => (
                      <button
                        key={value}
                        className={filter === value ? 'selected' : ''}
                        aria-pressed={filter === value}
                        onClick={() => setFilter(value)}
                      >
                        {label}
                      </button>
                    ))}
                  </div>
                  <label className="search-box">
                    <Search size={16} />
                    <input
                      aria-label="Search proposals"
                      value={query}
                      onChange={(e) => setQuery(e.target.value)}
                      placeholder="Search proposals…"
                    />
                  </label>
                </div>
                <div className="list-columns">
                  <span>PROJECT / CLIENT</span>
                  <span>STATUS</span>
                  <span>REVISION</span>
                  <span className="numeric">TOTAL FEE</span>
                  <span />
                </div>
                {loading ? (
                  <output className="empty-state">
                    <span className="spinner" />
                    Loading proposals…
                  </output>
                ) : filtered.length ? (
                  filtered.map((p) => (
                    <button
                      className="proposal-row"
                      key={p.id}
                      onClick={() => {
                        setBusy(true);
                        void openProposal(p.id)
                          .catch(report)
                          .finally(() => setBusy(false));
                      }}
                      disabled={busy}
                    >
                      <div className="project-cell">
                        <span className="project-icon">
                          <FileText size={22} />
                        </span>
                        <div>
                          <strong>{p.title}</strong>
                          <span>{p.client_name}</span>
                        </div>
                      </div>
                      <Status state={p.state} />
                      <span className="revision-chip">v{p.number}</span>
                      <strong className="numeric fee-value">
                        {money(p.total_cents, p.currency)}
                      </strong>
                      <ArrowUpRight size={18} />
                    </button>
                  ))
                ) : (
                  <div className="empty-state">
                    <FolderOpen size={32} />
                    <h2>
                      {items.length
                        ? 'No matching proposals'
                        : 'Your first proposal starts here'}
                    </h2>
                    <p>
                      {items.length
                        ? 'Try another search or filter.'
                        : 'Add a client, describe the work, and set the fees.'}
                    </p>
                    {items.length > 0 && (
                      <Button
                        variant="outline"
                        onClick={() => {
                          setQuery('');
                          setFilter('all');
                        }}
                      >
                        Clear filters
                      </Button>
                    )}
                  </div>
                )}
              </section>
              <p className="list-footnote">
                <GitBranchIcon />
                Each revision keeps its own content, generated files, and review
                decision.
              </p>
            </>
          )}
        </main>
      </div>
    </div>
  );
}
function GitBranchIcon() {
  return <span aria-hidden="true">↳</span>;
}
