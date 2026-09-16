# Verification

Release checks on 16 September 2026:

| Area | Check |
| --- | --- |
| Backend | 35 passing cases, including real PostgreSQL concurrency and LibreOffice PDF conversion |
| Frontend | TypeScript, Oxlint, three fee regression tests, and production static export |
| Database | Alembic upgrade on PostgreSQL and no model/migration drift |
| Complete demo | Compose startup, health checks, and the HTTP lifecycle in `scripts/smoke.py` |
| Browser | Chromium at 1440px and 390px: create, generate, download, submit, approve, revise, inspect old approval, search, and empty state |
| Documents | Both pages of the example DOCX/PDF visually inspected; original sample hashes match the approval record |

The browser walkthrough checked for page errors and page-level horizontal overflow. It verified the downloaded PDF against its approval hash, and confirmed that a new draft has no review while the earlier revision remains approved. The README screenshot comes from this running local application with fictional data.

The [CI workflow](../.github/workflows/ci.yml) repeats the backend, frontend, migration, and Docker checks on pushes and pull requests. The [Actions history](https://github.com/MilanG-Ne/docflow/actions/workflows/ci.yml) is the source of truth for the current branch; test counts here describe this release. Browser visual checks are a release check, not an automated CI browser suite.

## Regression coverage

- Author/reviewer permissions, ownership, self-review refusal, CSRF, origin checks, and session handling.
- Immutable revisions, stale edits, old decisions, missing/changed files, and download integrity.
- Concurrent worker claims, competing edits, and approval racing with an edit on PostgreSQL.
- Worker retries, exhausted and expired leases, stale-worker fencing, and template mismatch failures.
- Decimal rounding, invalid input, XML escaping, undefined template variables, repeated fee rows, optional assumptions, and real PDF conversion.

## Deliberate limits

- This is a local demonstration, not a managed production service. It has no invitations, password reset, login rate limiting, email delivery, tenant administration, or external identity provider.
- Templates are trusted and bundled. There is no arbitrary document upload or template editor.
- Approval is application metadata, not a cryptographic signature, legal signing service, or an externally secured audit log.
- There is no automatic artifact retention policy, orphan-directory cleanup, or backup scheduler.
- The worker lease is fixed rather than renewed. Large documents outside the bounded demo inputs would need a different conversion/lease policy.
- SQLite is convenient for local development; PostgreSQL is the concurrency target.
- The frontend polls every three seconds. Large workspaces would need paginated endpoints and a more selective update strategy.
- The generated files are the downloadable proposal; the HTML preview is a reading view and does not promise identical pagination.
- Progressive WebMCP registration exposes list/open tools and an author-only submit action in a supporting browser. The release browser did not expose `document.modelContext`; native tool discovery and invocation were therefore **not verified**. Ordinary browser use does not depend on that API.

The backend suite currently emits two upstream Starlette deprecation warnings. They do not fail the suite; dependency upgrades should review them.
