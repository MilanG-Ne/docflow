# DocFlow

A proposal workflow for a fictional consulting agency. Authors prepare structured proposals, a background worker generates Word and PDF files, and reviewers approve a specific revision.

An approval is attached to the revision's content and generated files. Editing a proposal creates a new revision and does not carry the approval forward.

## Stack

- Python / FastAPI API and document worker
- PostgreSQL with SQLAlchemy and Alembic
- React / TypeScript interface
- docxtpl and LibreOffice for document generation
- Docker Compose for a complete local demo

Implementation is in progress. Setup and verification instructions will be added alongside the working services.
