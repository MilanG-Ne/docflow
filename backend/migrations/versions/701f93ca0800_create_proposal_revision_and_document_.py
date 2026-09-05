"""Create proposal revision and document job tables"""

import sqlalchemy as sa
from alembic import op

revision = "701f93ca0800"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "users",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("email", sa.String(length=254), nullable=False),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("role", sa.String(length=16), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.CheckConstraint("role IN ('author', 'reviewer')"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_table(
        "proposals",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("owner_id", sa.String(length=36), nullable=False),
        sa.Column("latest_number", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.Integer(), nullable=False),
        sa.CheckConstraint("latest_number > 0"),
        sa.ForeignKeyConstraint(
            ["owner_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "sessions",
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("csrf", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("token_hash"),
    )
    op.create_index(op.f("ix_sessions_expires_at"), "sessions", ["expires_at"], unique=False)
    op.create_table(
        "events",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("proposal_id", sa.String(length=36), nullable=False),
        sa.Column("revision_number", sa.Integer(), nullable=False),
        sa.Column("actor", sa.String(length=80), nullable=False),
        sa.Column("action", sa.String(length=60), nullable=False),
        sa.Column("created_at", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["proposal_id"],
            ["proposals.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_events_proposal_id"), "events", ["proposal_id"], unique=False)
    op.create_table(
        "revisions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("proposal_id", sa.String(length=36), nullable=False),
        sa.Column("number", sa.Integer(), nullable=False),
        sa.Column("content", sa.JSON(), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("template_hash", sa.String(length=64), nullable=False),
        sa.Column("state", sa.String(length=24), nullable=False),
        sa.Column("created_at", sa.Integer(), nullable=False),
        sa.CheckConstraint("state IN ('draft', 'in_review', 'approved', 'changes_requested')"),
        sa.CheckConstraint("number > 0"),
        sa.ForeignKeyConstraint(
            ["proposal_id"],
            ["proposals.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("proposal_id", "number"),
    )
    op.create_index(op.f("ix_revisions_proposal_id"), "revisions", ["proposal_id"], unique=False)
    op.create_table(
        "artifacts",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("revision_id", sa.String(length=36), nullable=False),
        sa.Column("kind", sa.String(length=8), nullable=False),
        sa.Column("path", sa.Text(), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("size", sa.Integer(), nullable=False),
        sa.CheckConstraint("kind IN ('docx', 'pdf')"),
        sa.ForeignKeyConstraint(
            ["revision_id"],
            ["revisions.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("revision_id", "kind"),
    )
    op.create_table(
        "jobs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("revision_id", sa.String(length=36), nullable=False),
        sa.Column("state", sa.String(length=16), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("available_at", sa.Integer(), nullable=False),
        sa.Column("lease_until", sa.Integer(), nullable=True),
        sa.Column("lease_token", sa.String(length=36), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.CheckConstraint("state IN ('pending', 'running', 'completed', 'failed')"),
        sa.ForeignKeyConstraint(
            ["revision_id"],
            ["revisions.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("revision_id"),
    )
    op.create_index("ix_jobs_claim", "jobs", ["state", "available_at"], unique=False)
    op.create_table(
        "reviews",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("revision_id", sa.String(length=36), nullable=False),
        sa.Column("reviewer_id", sa.String(length=36), nullable=False),
        sa.Column("decision", sa.String(length=24), nullable=False),
        sa.Column("comment", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("artifact_hashes", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.Integer(), nullable=False),
        sa.CheckConstraint("decision IN ('approved', 'changes_requested')"),
        sa.ForeignKeyConstraint(
            ["reviewer_id"],
            ["users.id"],
        ),
        sa.ForeignKeyConstraint(
            ["revision_id"],
            ["revisions.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("revision_id"),
    )


def downgrade():
    op.drop_table("reviews")
    op.drop_index("ix_jobs_claim", table_name="jobs")
    op.drop_table("jobs")
    op.drop_table("artifacts")
    op.drop_index(op.f("ix_revisions_proposal_id"), table_name="revisions")
    op.drop_table("revisions")
    op.drop_index(op.f("ix_events_proposal_id"), table_name="events")
    op.drop_table("events")
    op.drop_index(op.f("ix_sessions_expires_at"), table_name="sessions")
    op.drop_table("sessions")
    op.drop_table("proposals")
    op.drop_table("users")
