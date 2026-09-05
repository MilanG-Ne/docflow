export type User = {
  id: string;
  name: string;
  email: string;
  role: 'author' | 'reviewer';
};
export type Identity = { user: User; csrf: string };
export type LineItem = {
  description: string;
  quantity: string;
  unit_cents: number;
};
export type Content = {
  title: string;
  client_name: string;
  client_contact: string;
  summary: string;
  deliverables: string;
  timeline: string;
  assumptions: string;
  currency: 'EUR' | 'USD' | 'GBP';
  line_items: LineItem[];
};
export type State = 'draft' | 'in_review' | 'approved' | 'changes_requested';
export type ProposalSummary = {
  id: string;
  title: string;
  client_name: string;
  state: State;
  number: number;
  currency: string;
  total_cents: number;
  created_at: number;
};
export type Artifact = {
  id: string;
  kind: 'docx' | 'pdf';
  sha256: string;
  size: number;
};
export type Revision = {
  id: string;
  number: number;
  content: Content;
  content_hash: string;
  template_hash: string;
  state: State;
  created_at: number;
  total_cents: number;
  job: {
    state: 'pending' | 'running' | 'completed' | 'failed';
    attempts: number;
    error: string | null;
  };
  artifacts: Artifact[];
  review: null | {
    decision: State;
    comment: string;
    reviewer: string;
    created_at: number;
    content_hash: string;
    artifact_hashes: Record<string, string>;
  };
};
export type Proposal = {
  id: string;
  owner: string;
  latest_number: number;
  created_at: number;
  revisions: Revision[];
  events: {
    id: string;
    revision_number: number;
    actor: string;
    action: string;
    created_at: number;
  }[];
};

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
  ) {
    super(message);
  }
}
export async function api<T>(
  path: string,
  options: {
    method?: string;
    body?: unknown;
    csrf?: string;
    signal?: AbortSignal;
  } = {},
): Promise<T> {
  const response = await fetch(`/api${path}`, {
    method: options.method ?? 'GET',
    credentials: 'same-origin',
    signal: options.signal,
    headers: {
      ...(options.body !== undefined
        ? { 'Content-Type': 'application/json' }
        : {}),
      ...(options.csrf ? { 'X-CSRF-Token': options.csrf } : {}),
    },
    ...(options.body !== undefined
      ? { body: JSON.stringify(options.body) }
      : {}),
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    const detail: unknown = payload && typeof payload === 'object' && 'detail' in payload ? payload.detail : undefined;
    const message =
      typeof detail === 'string'
        ? detail
        : Array.isArray(detail)
          ? detail
              .map(
                (item: { loc?: string[]; msg?: string }) =>
                  `${item.loc?.slice(1).join(' › ') ?? 'Input'}: ${item.msg ?? 'Invalid value'}`,
              )
              .join('; ')
          : 'The service could not complete this request. Try again.';
    throw new ApiError(message, response.status);
  }
  return response.status === 204 ? (undefined as T) : response.json();
}
export const stateLabel: Record<State, string> = {
  draft: 'Draft',
  in_review: 'In review',
  approved: 'Approved',
  changes_requested: 'Changes requested',
};
export const money = (cents: number, currency: string) =>
  new Intl.NumberFormat('en-GB', {
    style: 'currency',
    currency,
    maximumFractionDigits: 2,
  }).format(cents / 100);
export const date = (timestamp: number) =>
  new Intl.DateTimeFormat('en-GB', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  }).format(timestamp * 1000);
export const blankContent: Content = {
  title: '',
  client_name: '',
  client_contact: '',
  summary: '',
  deliverables: '',
  timeline: '',
  assumptions: '',
  currency: 'EUR',
  line_items: [{ description: '', quantity: '1', unit_cents: 0 }],
};
