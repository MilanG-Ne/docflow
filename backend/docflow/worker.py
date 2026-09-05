import argparse
import logging
import shutil
import signal
import threading
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import and_, or_, select, update

from .config import Settings
from .db import session_factory
from .documents import InvalidTemplate, file_hash, generate
from .models import Artifact, Event, Job, Revision, now, uid

logger = logging.getLogger(__name__)
MAX_ATTEMPTS = 3
LEASE_SECONDS = 120  # Longer than the converter's 60-second timeout.


@dataclass(frozen=True)
class Claim:
    job_id: str
    revision_id: str
    token: str
    attempts: int


def claim_next(factory) -> Claim | None:
    with factory.begin() as db:
        # A worker that disappeared during its final attempt must not leave a job stuck.
        db.execute(
            update(Job)
            .where(Job.state == "running", Job.lease_until <= now(), Job.attempts >= MAX_ATTEMPTS)
            .values(
                state="failed",
                error="Worker lease expired after the final attempt",
                lease_token=None,
            )
        )
        eligible = or_(
            and_(Job.state == "pending", Job.available_at <= now()),
            and_(Job.state == "running", Job.lease_until <= now()),
        )
        job = db.scalar(
            select(Job)
            .where(eligible, Job.attempts < MAX_ATTEMPTS)
            .order_by(Job.available_at, Job.id)
            .with_for_update(skip_locked=True)
            .limit(1)
        )
        if job is None:
            return None
        token = uid()
        # CAS covers SQLite's lack of row locks as well as an expired lease takeover.
        claimed = db.execute(
            update(Job)
            .where(Job.id == job.id, eligible, Job.attempts == job.attempts)
            .values(
                state="running",
                attempts=Job.attempts + 1,
                lease_until=now() + LEASE_SECONDS,
                lease_token=token,
                error=None,
            )
            .execution_options(synchronize_session=False)
        )
        if claimed.rowcount != 1:
            return None
        return Claim(job.id, job.revision_id, token, job.attempts + 1)


def process_one(factory, settings: Settings, generator=generate) -> bool:
    claim = claim_next(factory)
    if claim is None:
        return False
    directory = settings.artifact_dir / claim.revision_id / claim.token
    published = False
    try:
        with factory() as db:
            revision = db.get(Revision, claim.revision_id)
            if file_hash(settings.template_path) != revision.template_hash:
                raise InvalidTemplate(
                    "The template changed after this revision was created; create a new revision"
                )
            files = generator(
                settings.template_path,
                directory,
                revision.content,
                revision.number,
                revision.proposal_id[:8],
                settings.libreoffice_bin,
            )
        if set(files) != {"docx", "pdf"}:
            raise InvalidTemplate("Both Word and PDF files are required")
        with factory.begin() as db:
            job = db.scalar(select(Job).where(Job.id == claim.job_id).with_for_update())
            if job.lease_token != claim.token or job.state != "running":
                return True  # A newer lease owns this job. Its files must win.
            for kind, path in files.items():
                db.add(
                    Artifact(
                        revision_id=claim.revision_id,
                        kind=kind,
                        path=str(path.relative_to(settings.artifact_dir)),
                        sha256=file_hash(path),
                        size=path.stat().st_size,
                    )
                )
            job.state, job.lease_token, job.lease_until = "completed", None, None
            db.add(
                Event(
                    proposal_id=revision.proposal_id,
                    revision_number=revision.number,
                    actor="Document worker",
                    action="Generated Word and PDF",
                )
            )
        published = True
        logger.info("Generated documents for revision %s", claim.revision_id)
    except Exception as exc:
        logger.exception("Generation failed for job %s", claim.job_id)
        permanent = isinstance(exc, InvalidTemplate)
        with factory.begin() as db:
            job = db.scalar(select(Job).where(Job.id == claim.job_id).with_for_update())
            if job.lease_token == claim.token and job.state == "running":
                job.state = "failed" if permanent or claim.attempts >= MAX_ATTEMPTS else "pending"
                job.available_at = now() + 2**claim.attempts
                job.lease_token, job.lease_until = None, None
                job.error = (
                    str(exc)
                    if permanent
                    else "Document conversion failed. Check worker logs; transient failures retry up to three times."
                )
    finally:
        if not published:
            shutil.rmtree(directory, ignore_errors=True)
    return True


def main():
    parser = argparse.ArgumentParser(description="Generate pending DocFlow documents")
    parser.add_argument("--once", action="store_true", help="Process at most one job and exit")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    settings = Settings()
    settings.artifact_dir.mkdir(parents=True, exist_ok=True)
    factory = session_factory(settings.database_url)
    stop = threading.Event()
    signal.signal(signal.SIGTERM, lambda *_: stop.set())
    signal.signal(signal.SIGINT, lambda *_: stop.set())
    while not stop.is_set():
        try:
            worked = process_one(factory, settings)
            Path("/tmp/docflow-worker-heartbeat").touch()
        except Exception:
            logger.exception("Worker could not reach its job queue")
            worked = False
        if args.once:
            break
        if not worked:
            stop.wait(1)


if __name__ == "__main__":
    main()
