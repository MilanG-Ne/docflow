'use client';
import { useState } from 'react';
import { ArrowLeft, Plus, Trash2, FileCheck2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { type Content, money } from '@/lib/api';
import { hundredths, lineTotal } from '@/lib/fees';

export function ProposalEditor({
  initial,
  number,
  onCancel,
  onSave,
}: {
  initial: Content;
  number: number;
  onCancel: () => void;
  onSave: (content: Content) => Promise<void>;
}) {
  const [content, setContent] = useState<Content>(() =>
    structuredClone(initial),
  );
  const [rates, setRates] = useState(() =>
    initial.line_items.map((item) => (item.unit_cents / 100).toFixed(2)),
  );
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  function field(
    key: Exclude<keyof Content, 'line_items' | 'currency'>,
    title: string,
    limit: number,
    multiline = false,
    min = 1,
  ) {
    const props = {
      id: key,
      value: content[key],
      maxLength: limit,
      minLength: min,
      required: key !== 'assumptions',
      onChange: (
        e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>,
      ) => setContent({ ...content, [key]: e.target.value }),
    };
    return (
      <label
        className={multiline ? 'form-field full' : 'form-field'}
        htmlFor={key}
      >
        <span>
          {title}
          {key === 'assumptions' && <span className="muted"> · optional</span>}
        </span>
        {multiline ? (
          <Textarea {...props} rows={key === 'timeline' ? 3 : 5} />
        ) : (
          <Input {...props} />
        )}
      </label>
    );
  }
  async function save(event: React.SyntheticEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError('');
    try {
      const items = content.line_items.map((item, i) => {
        const cents = hundredths(rates[i]);
        if (cents === null)
          throw new Error('Enter each day rate with up to two decimal places.');
        return {
          ...item,
          unit_cents: cents,
        };
      });
      await onSave({ ...content, line_items: items });
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not save the proposal');
    } finally {
      setBusy(false);
    }
  }
  const total = content.line_items.reduce(
    (sum, row, i) => sum + lineTotal(row.quantity, hundredths(rates[i]) ?? 0),
    0,
  );
  return (
    <form onSubmit={save} className="editor">
      <div className="editor-heading">
        <Button
          type="button"
          variant="ghost"
          onClick={onCancel}
          disabled={busy}
        >
          <ArrowLeft />
          Back to proposals
        </Button>
        <span className="small muted">REVISION {number}</span>
      </div>
      <div className="section-heading">
        <div>
          <p className="eyebrow">PROPOSAL DETAILS</p>
          <h1>{number === 1 ? 'Start a proposal' : 'Create a new revision'}</h1>
          <p className="muted">
            Saving creates a revision and queues its Word and PDF files.
          </p>
        </div>
      </div>
      {number > 1 && (
        <div className="notice">
          Earlier revisions and their approvals remain in the history. This
          revision will need its own review.
        </div>
      )}
      <div className="editor-section">
        <h2>
          01 <span>Client & project</span>
        </h2>
        <div className="form-grid">
          {field('title', 'Project title', 80)}
          {field('client_name', 'Client name', 80)}
          {field('client_contact', 'Client contact', 80)}
          <label className="form-field" htmlFor="currency">
            <span>Currency</span>
            <select
              id="currency"
              value={content.currency}
              onChange={(e) =>
                setContent({
                  ...content,
                  currency: e.target.value as Content['currency'],
                })
              }
            >
              <option value="EUR">EUR · Euro</option>
              <option value="USD">USD · US dollar</option>
              <option value="GBP">GBP · Pound sterling</option>
            </select>
          </label>
        </div>
      </div>
      <div className="editor-section">
        <h2>
          02 <span>Scope of work</span>
        </h2>
        <div className="form-grid">
          {field('summary', 'Overview', 2000, true, 20)}
          {field('deliverables', 'Deliverables', 3000, true, 10)}
          {field('timeline', 'Timeline', 500, true, 5)}
          {field('assumptions', 'Assumptions and exclusions', 1500, true)}
        </div>
      </div>
      <div className="editor-section">
        <h2>
          03 <span>Fees</span>
        </h2>
        <p className="muted small">
          Use days for quantities. Half days and other fractions are supported.
        </p>
        <div className="fee-editor">
          {content.line_items.map((item, index) => (
            <div className="fee-edit-row" key={index}>
              <label htmlFor={`service-${index}`}>
                Service
                <Input
                  required
                  maxLength={160}
                  id={`service-${index}`}
                  value={item.description}
                  onChange={(e) =>
                    setContent({
                      ...content,
                      line_items: content.line_items.map((row, i) =>
                        i === index
                          ? { ...row, description: e.target.value }
                          : row,
                      ),
                    })
                  }
                />
              </label>
              <label htmlFor={`days-${index}`}>
                Days
                <Input
                  required
                  type="number"
                  id={`days-${index}`}
                  min="0.01"
                  max="1000"
                  step="0.01"
                  value={item.quantity}
                  onChange={(e) =>
                    setContent({
                      ...content,
                      line_items: content.line_items.map((row, i) =>
                        i === index
                          ? { ...row, quantity: e.target.value }
                          : row,
                      ),
                    })
                  }
                />
              </label>
              <label htmlFor={`rate-${index}`}>
                Day rate
                <Input
                  required
                  id={`rate-${index}`}
                  inputMode="decimal"
                  pattern="[0-9]+(\.[0-9]{1,2})?"
                  value={rates[index]}
                  onChange={(e) =>
                    setRates(
                      rates.map((rate, i) =>
                        i === index ? e.target.value : rate,
                      ),
                    )
                  }
                />
              </label>
              <Button
                type="button"
                variant="ghost"
                size="icon"
                aria-label={`Remove service ${index + 1}`}
                disabled={content.line_items.length === 1}
                onClick={() => {
                  setContent({
                    ...content,
                    line_items: content.line_items.filter(
                      (_, i) => i !== index,
                    ),
                  });
                  setRates(rates.filter((_, i) => i !== index));
                }}
              >
                <Trash2 size={16} />
              </Button>
            </div>
          ))}
        </div>
        <div className="fee-total">
          <Button
            type="button"
            variant="outline"
            disabled={content.line_items.length >= 20}
            onClick={() => {
              setContent({
                ...content,
                line_items: [
                  ...content.line_items,
                  { description: '', quantity: '1', unit_cents: 0 },
                ],
              });
              setRates([...rates, '0.00']);
            }}
          >
            <Plus />
            Add service
          </Button>
          <span>
            Total fee{' '}
            <strong>
              {money(Number.isFinite(total) ? total : 0, content.currency)}
            </strong>
          </span>
        </div>
      </div>
      {error && (
        <p className="notice error" role="alert">
          {error}
        </p>
      )}
      <div className="editor-footer">
        <Button
          type="button"
          variant="outline"
          onClick={onCancel}
          disabled={busy}
        >
          Cancel
        </Button>
        <Button type="submit" disabled={busy}>
          <FileCheck2 />
          {busy ? 'Saving revision…' : 'Save & generate documents'}
        </Button>
      </div>
    </form>
  );
}
