# Contributing

Start with the [local setup](docs/development.md) and [architecture](docs/architecture.md). Keep changes small enough to explain with a concrete workflow or failure case.

Before opening a pull request:

- Run the relevant backend/frontend checks and describe what was exercised.
- Add a regression test for a changed permission, revision, money, or worker invariant.
- Include a migration for a database change; check it on PostgreSQL.
- For template changes, generate Word and PDF examples and inspect every page for clipped text, broken rows, and unexpected page breaks.
- For interface changes, check keyboard labels, loading/error states, and the narrow layout.

Use fictional examples. Keep local databases, generated working files, credentials, and personal client documents out of commits. The small files under `examples/generated/` are intentional, reviewed release samples.

A useful issue includes the command or browser steps, expected behavior, actual behavior, and a redacted error. Never post live credentials or real client documents in an issue.
