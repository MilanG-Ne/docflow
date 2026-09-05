import time
import uuid

from sqlalchemy import (
    JSON,
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def uid() -> str:
    return str(uuid.uuid4())


def now() -> int:
    return int(time.time())


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    email: Mapped[str] = mapped_column(String(254), unique=True)
    name: Mapped[str] = mapped_column(String(80))
    role: Mapped[str] = mapped_column(String(16))
    password_hash: Mapped[str] = mapped_column(Text)
    __table_args__ = (CheckConstraint("role IN ('author', 'reviewer')"),)


class LoginSession(Base):
    __tablename__ = "sessions"
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    csrf: Mapped[str] = mapped_column(String(64))
    expires_at: Mapped[int] = mapped_column(Integer, index=True)


class Proposal(Base):
    __tablename__ = "proposals"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    latest_number: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[int] = mapped_column(Integer, default=now)
    __table_args__ = (CheckConstraint("latest_number > 0"),)


class Revision(Base):
    __tablename__ = "revisions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    proposal_id: Mapped[str] = mapped_column(ForeignKey("proposals.id"), index=True)
    number: Mapped[int] = mapped_column(Integer)
    content: Mapped[dict] = mapped_column(JSON)
    content_hash: Mapped[str] = mapped_column(String(64))
    template_hash: Mapped[str] = mapped_column(String(64))
    state: Mapped[str] = mapped_column(String(24), default="draft")
    created_at: Mapped[int] = mapped_column(Integer, default=now)
    __table_args__ = (
        UniqueConstraint("proposal_id", "number"),
        CheckConstraint("number > 0"),
        CheckConstraint("state IN ('draft', 'in_review', 'approved', 'changes_requested')"),
    )


class Job(Base):
    __tablename__ = "jobs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    revision_id: Mapped[str] = mapped_column(ForeignKey("revisions.id"), unique=True)
    state: Mapped[str] = mapped_column(String(16), default="pending")
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    available_at: Mapped[int] = mapped_column(Integer, default=now)
    lease_until: Mapped[int | None] = mapped_column(Integer)
    lease_token: Mapped[str | None] = mapped_column(String(36))
    error: Mapped[str | None] = mapped_column(Text)
    __table_args__ = (
        CheckConstraint("state IN ('pending', 'running', 'completed', 'failed')"),
        Index("ix_jobs_claim", "state", "available_at"),
    )


class Artifact(Base):
    __tablename__ = "artifacts"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    revision_id: Mapped[str] = mapped_column(ForeignKey("revisions.id"))
    kind: Mapped[str] = mapped_column(String(8))
    path: Mapped[str] = mapped_column(Text)
    sha256: Mapped[str] = mapped_column(String(64))
    size: Mapped[int] = mapped_column(Integer)
    __table_args__ = (
        UniqueConstraint("revision_id", "kind"),
        CheckConstraint("kind IN ('docx', 'pdf')"),
    )


class Review(Base):
    __tablename__ = "reviews"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    revision_id: Mapped[str] = mapped_column(ForeignKey("revisions.id"), unique=True)
    reviewer_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    decision: Mapped[str] = mapped_column(String(24))
    comment: Mapped[str] = mapped_column(Text)
    content_hash: Mapped[str] = mapped_column(String(64))
    artifact_hashes: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[int] = mapped_column(Integer, default=now)
    __table_args__ = (CheckConstraint("decision IN ('approved', 'changes_requested')"),)


class Event(Base):
    __tablename__ = "events"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    proposal_id: Mapped[str] = mapped_column(ForeignKey("proposals.id"), index=True)
    revision_number: Mapped[int] = mapped_column(Integer)
    actor: Mapped[str] = mapped_column(String(80))
    action: Mapped[str] = mapped_column(String(60))
    created_at: Mapped[int] = mapped_column(Integer, default=now)
