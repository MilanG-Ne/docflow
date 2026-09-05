'use client';
import { useState } from 'react';
import {
  Check,
  Download,
  FileText,
  GitBranch,
  LockKeyhole,
  Send,
  RotateCcw,
  Clock3,
  PencilLine,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import {
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
} from '@/components/ui/table';
import { Textarea } from '@/components/ui/textarea';
import {
  type Proposal,
  type User,
  type Revision,
  stateLabel,
  money,
  date,
} from '@/lib/api';

export function Status({ state }: { state: Revision['state'] }) {
  return (
    <span className={`status status-${state}`}>
      <span />
      {stateLabel[state]}
    </span>
  );
}

export function ProposalDetail({
  proposal,
  user,
  busy,
  onEdit,
  onAction,
}: {
  proposal: Proposal;
  user: User;
  busy: boolean;
  onEdit: () => void;
  onAction: (
    revision: Revision,
    action: 'submit' | 'review' | 'retry',
    decision?: string,
    comment?: string,
  ) => Promise<void>;
}) {
  const [number, setNumber] = useState<number | null>(null);
  const [comment, setComment] = useState('');
  const revision =
    proposal.revisions.find((r) => r.number === number) ??
    proposal.revisions[0];
  const content = revision.content;
  const latest = revision.number === proposal.latest_number;
  const author = user.role === 'author';
  const generating =
    revision.job.state === 'pending' || revision.job.state === 'running';
  return (
    <div className="proposal-detail">
      <header className="detail-heading">
        <div>
          <p className="eyebrow">{content.client_name}</p>
          <h1>{content.title}</h1>
          <p className="muted">
            Prepared by {proposal.owner} · Created {date(proposal.created_at)}
          </p>
        </div>
        {author && (
          <Button variant="outline" onClick={onEdit} disabled={busy}>
            <PencilLine />
            New revision
          </Button>
        )}
      </header>
      <div className="revision-bar">
        <div className="revision-picker">
          <GitBranch size={17} />
          <label htmlFor="revision-number" className="sr-only">
            View revision
          </label>
          <select
            id="revision-number"
            value={revision.number}
            onChange={(e) => setNumber(Number(e.target.value))}
          >
            {proposal.revisions.map((r) => (
              <option key={r.id} value={r.number}>
                Revision {r.number}
                {r.number === proposal.latest_number ? ' · latest' : ''}
              </option>
            ))}
          </select>
        </div>
        <Status state={revision.state} />
        <span className="small muted">{date(revision.created_at)}</span>
      </div>
      {!latest && (
        <div className="notice">
          You are viewing revision {revision.number}. The latest is revision{' '}
          {proposal.latest_number}.{' '}
          {revision.state === 'approved'
            ? 'This approval and its files remain valid for this revision.'
            : 'This revision has been superseded.'}
          <button
            className="inline-link"
            onClick={() => setNumber(proposal.latest_number)}
          >
            View latest
          </button>
        </div>
      )}
      <div className="detail-columns">
        <div className="detail-main">
          <Tabs defaultValue="proposal">
            <TabsList variant="line" className="detail-tabs">
              <TabsTrigger value="proposal">Proposal</TabsTrigger>
              <TabsTrigger value="activity">
                Activity <span className="count">{proposal.events.length}</span>
              </TabsTrigger>
              <TabsTrigger value="record">Revision record</TabsTrigger>
            </TabsList>
            <TabsContent value="proposal">
              <article className="paper">
                <div className="paper-brand">
                  <span>ALDER & CO.</span>
                  <span>
                    PROJECT PROPOSAL / {proposal.id.slice(0, 8).toUpperCase()}
                  </span>
                </div>
                <h2>{content.title}</h2>
                <div className="paper-meta">
                  <div>
                    <span>PREPARED FOR</span>
                    <strong>{content.client_name}</strong>
                    <p>{content.client_contact}</p>
                  </div>
                  <div>
                    <span>REVISION</span>
                    <strong>{String(revision.number).padStart(2, '0')}</strong>
                    <p>{date(revision.created_at)}</p>
                  </div>
                </div>
                <section>
                  <h3>
                    <span>01</span>Overview
                  </h3>
                  <p className="preserve-text">{content.summary}</p>
                </section>
                <section>
                  <h3>
                    <span>02</span>Deliverables
                  </h3>
                  <p className="preserve-text">{content.deliverables}</p>
                </section>
                <section>
                  <h3>
                    <span>03</span>Timeline
                  </h3>
                  <p className="preserve-text">{content.timeline}</p>
                </section>
                <section>
                  <h3>
                    <span>04</span>Fees
                  </h3>
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Service</TableHead>
                        <TableHead className="numeric">Days</TableHead>
                        <TableHead className="numeric">Day rate</TableHead>
                        <TableHead className="numeric">Amount</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {content.line_items.map((item, i) => (
                        <TableRow key={i}>
                          <TableCell className="service-cell">
                            {item.description}
                          </TableCell>
                          <TableCell className="numeric">
                            {item.quantity}
                          </TableCell>
                          <TableCell className="numeric">
                            {money(item.unit_cents, content.currency)}
                          </TableCell>
                          <TableCell className="numeric">
                            {money(
                              Math.round(
                                Number(item.quantity) * item.unit_cents,
                              ),
                              content.currency,
                            )}
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                  <div className="paper-total">
                    <span>Total fee</span>
                    <strong>
                      {money(revision.total_cents, content.currency)}
                    </strong>
                  </div>
                  <p className="small muted">Excludes applicable taxes.</p>
                </section>
                {content.assumptions && (
                  <section>
                    <h3>
                      <span>05</span>Assumptions
                    </h3>
                    <p className="preserve-text">{content.assumptions}</p>
                  </section>
                )}
                <footer className="paper-footer">
                  Alder & Co. · Revision {revision.number}
                  <span>Proposal v1</span>
                </footer>
              </article>
            </TabsContent>
            <TabsContent value="activity">
              <div className="activity-panel">
                <h2>Proposal activity</h2>
                <p className="muted">
                  The recorded history across all revisions.
                </p>
                <ol className="activity-list">
                  {proposal.events.map((e) => (
                    <li key={e.id}>
                      <div className="activity-dot">
                        <Clock3 size={14} />
                      </div>
                      <div>
                        <strong>{e.action}</strong>
                        <p>
                          {e.actor} · Revision {e.revision_number}
                        </p>
                        <time>
                          {new Date(e.created_at * 1000).toLocaleString(
                            'en-GB',
                          )}
                        </time>
                      </div>
                    </li>
                  ))}
                </ol>
              </div>
            </TabsContent>
            <TabsContent value="record">
              <div className="activity-panel">
                <h2>Revision {revision.number} record</h2>
                <p className="muted">
                  The content and template are fingerprinted when a revision is
                  created. An approval records the hashes of both generated
                  files.
                </p>
                <dl className="record">
                  <dt>Content SHA-256</dt>
                  <dd>{revision.content_hash}</dd>
                  <dt>Template SHA-256</dt>
                  <dd>{revision.template_hash}</dd>
                  {revision.artifacts.map((file) => (
                    <div key={file.id}>
                      <dt>{file.kind.toUpperCase()} SHA-256</dt>
                      <dd>{file.sha256}</dd>
                    </div>
                  ))}
                </dl>
                <p className="small muted">
                  These checks detect file changes inside this application. They
                  are not a digital signature or an external audit service.
                </p>
              </div>
            </TabsContent>
          </Tabs>
        </div>
        <aside className="review-sidebar">
          <section className="side-section">
            <p className="eyebrow">DOCUMENTS</p>
            <h2>Ready to share</h2>
            <p className="muted small">
              Files are generated from revision {revision.number}. Approval is
              tracked in the workspace.
            </p>
            {generating && (
              <output className="generation-state">
                <span className="spinner" />
                <div>
                  <strong>
                    {revision.job.state === 'running'
                      ? 'Generating files'
                      : 'Queued for generation'}
                  </strong>
                  <p>Attempt {revision.job.attempts || 1} of 3</p>
                </div>
              </output>
            )}
            {revision.job.state === 'failed' && (
              <div className="notice error">
                <strong>Generation needs attention</strong>
                <p>{revision.job.error}</p>
                {author && latest && revision.state === 'draft' && (
                  <Button
                    variant="outline"
                    disabled={busy}
                    onClick={() => void onAction(revision, 'retry')}
                  >
                    <RotateCcw />
                    Retry generation
                  </Button>
                )}
              </div>
            )}
            {revision.artifacts.map((file) => (
              <a
                key={file.id}
                className="download-row"
                href={`/api/artifacts/${file.id}`}
                download
              >
                <span className={`file-icon file-${file.kind}`}>
                  <FileText size={19} />
                </span>
                <span>
                  <strong>Proposal.{file.kind}</strong>
                  <small>
                    {Math.ceil(file.size / 1024)} KB · Revision{' '}
                    {revision.number}
                  </small>
                </span>
                <Download size={17} />
              </a>
            ))}
          </section>
          <section className="side-section">
            <p className="eyebrow">REVIEW</p>
            <h2>
              {revision.state === 'approved'
                ? 'Revision approved'
                : revision.state === 'changes_requested'
                  ? 'Changes requested'
                  : revision.state === 'in_review'
                    ? 'Awaiting a decision'
                    : 'A second pair of eyes'}
            </h2>
            {revision.review ? (
              <div className="decision-record">
                <span className={`decision-icon ${revision.state}`}>
                  <Check size={19} />
                </span>
                <p>
                  <strong>{revision.review.reviewer}</strong>
                  <br />
                  <span className="small muted">
                    {date(revision.review.created_at)}
                  </span>
                </p>
                <blockquote>{revision.review.comment}</blockquote>
              </div>
            ) : (
              <p className="muted small">
                {revision.state === 'in_review'
                  ? 'Review the scope, fees, and generated documents before making a decision.'
                  : 'Once both files are ready, the author can send this revision to a reviewer.'}
              </p>
            )}
            {author && latest && revision.state === 'draft' && (
              <Button
                className="wide"
                disabled={busy || revision.job.state !== 'completed'}
                onClick={() => void onAction(revision, 'submit')}
              >
                <Send />
                Send for review
              </Button>
            )}
            {!author && latest && revision.state === 'in_review' && (
              <form
                className="review-form"
                onSubmit={(e) => {
                  e.preventDefault();
                  void onAction(revision, 'review', 'approved', comment);
                }}
              >
                <label htmlFor="review-comment">
                  Review notes
                  <Textarea
                    id="review-comment"
                    value={comment}
                    onChange={(e) => setComment(e.target.value)}
                    required
                    minLength={5}
                    maxLength={1500}
                    placeholder="What did you check?"
                    rows={4}
                  />
                </label>
                <Button
                  type="submit"
                  className="wide"
                  disabled={busy || comment.trim().length < 5}
                >
                  <Check />
                  Approve revision {revision.number}
                </Button>
                <Button
                  type="button"
                  variant="outline"
                  className="wide"
                  disabled={busy || comment.trim().length < 5}
                  onClick={() =>
                    void onAction(
                      revision,
                      'review',
                      'changes_requested',
                      comment,
                    )
                  }
                >
                  Request changes
                </Button>
              </form>
            )}
          </section>
          <div className="approval-note">
            <LockKeyhole size={17} />
            <p>
              Approvals belong to a revision. Editing creates a new revision
              that needs its own approval.
            </p>
          </div>
        </aside>
      </div>
    </div>
  );
}
