import hashlib
from pathlib import Path

from fastapi import HTTPException
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from .models import Artifact, Event, Job, Proposal, Review, Revision, User
from .schemas import ProposalContent, ReviewInput


def visible_proposal(db: Session, proposal_id: str, user: User, *, lock=False) -> Proposal:
    if lock:
        # All mutations acquire the proposal row first, including review decisions.
        # A no-op UPDATE also serializes writes in the SQLite development adapter.
        proposal = db.scalar(
            update(Proposal)
            .where(Proposal.id == proposal_id)
            .values(latest_number=Proposal.latest_number)
            .returning(Proposal)
            .execution_options(populate_existing=True)
        )
    else:
        proposal = db.get(Proposal, proposal_id)
    if not proposal or (user.role != "reviewer" and proposal.owner_id != user.id):
        raise HTTPException(404, "Proposal not found")
    return proposal


def require_author(proposal: Proposal | None, user: User):
    if user.role != "author" or (proposal and proposal.owner_id != user.id):
        raise HTTPException(403, "Only the proposal author can perform this action")


def log(db: Session, proposal: Proposal, number: int, actor: str, action: str):
    db.add(Event(proposal_id=proposal.id, revision_number=number, actor=actor, action=action))


def add_revision(
    db: Session, proposal: Proposal, content: ProposalContent, template: Path, actor: str
) -> Revision:
    revision = Revision(
        proposal_id=proposal.id,
        number=proposal.latest_number,
        content=content.model_dump(mode="json"),
        content_hash=content.fingerprint(),
        template_hash=hashlib.sha256(template.read_bytes()).hexdigest(),
    )
    db.add(revision)
    db.flush()
    db.add(Job(revision_id=revision.id))
    log(db, proposal, revision.number, actor, "Created revision")
    return revision


def create_proposal(db: Session, user: User, content: ProposalContent, template: Path) -> Proposal:
    require_author(None, user)
    proposal = Proposal(owner_id=user.id)
    db.add(proposal)
    db.flush()
    add_revision(db, proposal, content, template, user.name)
    return proposal


def revise(
    db: Session,
    user: User,
    proposal_id: str,
    expected: int,
    content: ProposalContent,
    template: Path,
):
    proposal = visible_proposal(db, proposal_id, user, lock=True)
    require_author(proposal, user)
    if proposal.latest_number != expected:
        raise HTTPException(409, "A newer revision exists. Reload the proposal before saving.")
    proposal.latest_number += 1
    add_revision(db, proposal, content, template, user.name)
    return proposal


def revision_for(db: Session, proposal: Proposal, revision_id: str) -> Revision:
    revision = db.get(Revision, revision_id)
    if revision is None or revision.proposal_id != proposal.id:
        raise HTTPException(404, "Revision not found")
    return revision


def submit(db: Session, user: User, proposal_id: str, revision_id: str):
    proposal = visible_proposal(db, proposal_id, user, lock=True)
    require_author(proposal, user)
    revision = revision_for(db, proposal, revision_id)
    if revision.number != proposal.latest_number or revision.state != "draft":
        raise HTTPException(409, "Only the latest draft can be submitted")
    job = db.scalar(select(Job).where(Job.revision_id == revision.id))
    files = db.scalars(select(Artifact).where(Artifact.revision_id == revision.id)).all()
    if job.state != "completed" or len(files) != 2:
        raise HTTPException(409, "Wait for both documents to finish generating")
    revision.state = "in_review"
    log(db, proposal, revision.number, user.name, "Requested review")


def review(db: Session, user: User, proposal_id: str, revision_id: str, data: ReviewInput):
    proposal = visible_proposal(db, proposal_id, user, lock=True)
    if user.role != "reviewer" or user.id == proposal.owner_id:
        raise HTTPException(403, "An independent reviewer must make this decision")
    revision = revision_for(db, proposal, revision_id)
    if revision.number != proposal.latest_number or revision.state != "in_review":
        raise HTTPException(409, "This revision is no longer awaiting review")
    if revision.content_hash != data.content_hash:
        raise HTTPException(409, "The reviewed content does not match this revision")
    files = db.scalars(select(Artifact).where(Artifact.revision_id == revision.id)).all()
    if {file.kind for file in files} != {"docx", "pdf"}:
        raise HTTPException(409, "Both documents are required for a review")
    db.add(
        Review(
            revision_id=revision.id,
            reviewer_id=user.id,
            decision=data.decision,
            comment=data.comment,
            content_hash=revision.content_hash,
            artifact_hashes={file.kind: file.sha256 for file in files},
        )
    )
    revision.state = data.decision
    log(
        db,
        proposal,
        revision.number,
        user.name,
        "Approved revision" if data.decision == "approved" else "Requested changes",
    )


def retry(db: Session, user: User, proposal_id: str, revision_id: str):
    proposal = visible_proposal(db, proposal_id, user, lock=True)
    require_author(proposal, user)
    revision = revision_for(db, proposal, revision_id)
    job = db.scalar(select(Job).where(Job.revision_id == revision.id).with_for_update())
    if (
        revision.number != proposal.latest_number
        or revision.state != "draft"
        or job.state != "failed"
    ):
        raise HTTPException(409, "Only a failed generation for the latest draft can be retried")
    from .models import now

    job.state, job.attempts, job.error, job.available_at = "pending", 0, None, now()
    log(db, proposal, revision.number, user.name, "Retried generation")


def serialize_revision(db: Session, revision: Revision) -> dict:
    job = db.scalar(select(Job).where(Job.revision_id == revision.id))
    files = db.scalars(select(Artifact).where(Artifact.revision_id == revision.id)).all()
    decision = db.scalar(select(Review).where(Review.revision_id == revision.id))
    return {
        "id": revision.id,
        "number": revision.number,
        "content": revision.content,
        "content_hash": revision.content_hash,
        "template_hash": revision.template_hash,
        "state": revision.state,
        "created_at": revision.created_at,
        "total_cents": ProposalContent.model_validate(revision.content).total_cents,
        "job": {"state": job.state, "attempts": job.attempts, "error": job.error},
        "artifacts": [
            {"id": f.id, "kind": f.kind, "sha256": f.sha256, "size": f.size} for f in files
        ],
        "review": None
        if decision is None
        else {
            "decision": decision.decision,
            "comment": decision.comment,
            "reviewer": db.get(User, decision.reviewer_id).name,
            "created_at": decision.created_at,
            "content_hash": decision.content_hash,
            "artifact_hashes": decision.artifact_hashes,
        },
    }


def detail(db: Session, proposal: Proposal) -> dict:
    revisions = db.scalars(
        select(Revision).where(Revision.proposal_id == proposal.id).order_by(Revision.number.desc())
    ).all()
    events = db.scalars(
        select(Event)
        .where(Event.proposal_id == proposal.id)
        .order_by(Event.created_at.desc(), Event.id)
    ).all()
    return {
        "id": proposal.id,
        "owner": db.get(User, proposal.owner_id).name,
        "latest_number": proposal.latest_number,
        "created_at": proposal.created_at,
        "revisions": [serialize_revision(db, r) for r in revisions],
        "events": [
            {
                "id": e.id,
                "revision_number": e.revision_number,
                "actor": e.actor,
                "action": e.action,
                "created_at": e.created_at,
            }
            for e in events
        ],
    }
