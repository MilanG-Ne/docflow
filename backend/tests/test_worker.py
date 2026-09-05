from dataclasses import replace

from conftest import fake_generate
from sqlalchemy import select

from docflow.documents import ConversionError, InvalidTemplate
from docflow.models import Artifact, Job, now, uid
from docflow.worker import MAX_ATTEMPTS, claim_next, process_one


def queued(clients, content):
    return clients[0].post("/api/proposals", json=content).json()


def test_transient_failure_retries_then_publishes_exactly_once(clients, environment, content):
    queued(clients, content)
    settings, factory = environment

    def fail(*args):
        raise ConversionError("Temporary converter failure")

    process_one(factory, settings, generator=fail)
    with factory.begin() as db:
        job = db.scalar(select(Job))
        assert job.state == "pending" and job.attempts == 1
        assert job.available_at > now()
        job.available_at = now()
    assert process_one(factory, settings, generator=fake_generate)
    assert not process_one(factory, settings, generator=fake_generate)
    with factory() as db:
        job = db.scalar(select(Job))
        assert job.state == "completed" and job.attempts == 2
        assert len(db.scalars(select(Artifact)).all()) == 2


def test_transient_failure_is_bounded(clients, environment, content):
    queued(clients, content)
    settings, factory = environment

    def fail(*args):
        raise ConversionError("Unavailable")

    for _ in range(MAX_ATTEMPTS):
        assert process_one(factory, settings, generator=fail)
        with factory.begin() as db:
            db.scalar(select(Job)).available_at = now()
    assert not process_one(factory, settings, generator=fail)
    with factory() as db:
        assert db.scalar(select(Job)).state == "failed"
        assert db.scalars(select(Artifact)).all() == []


def test_bad_template_is_a_permanent_failure(clients, environment, content):
    queued(clients, content)
    settings, factory = environment

    def fail(*args):
        raise InvalidTemplate("Undefined field")

    process_one(factory, settings, generator=fail)
    with factory() as db:
        job = db.scalar(select(Job))
        assert job.state == "failed" and job.attempts == 1


def test_changed_template_requires_a_new_revision(clients, environment, content, tmp_path):
    queued(clients, content)
    settings, factory = environment
    changed = tmp_path / "changed.docx"
    changed.write_bytes(b"different-template")
    process_one(factory, replace(settings, template_path=changed), generator=fake_generate)
    with factory() as db:
        job = db.scalar(select(Job))
        assert job.state == "failed" and "template changed" in job.error


def test_expired_lease_can_be_reclaimed(clients, environment, content):
    queued(clients, content)
    settings, factory = environment
    first = claim_next(factory)
    assert first
    assert claim_next(factory) is None
    with factory.begin() as db:
        db.get(Job, first.job_id).lease_until = now() - 1
    process_one(factory, settings, generator=fake_generate)
    with factory() as db:
        job = db.get(Job, first.job_id)
        assert job.state == "completed" and job.attempts == 2


def test_crash_on_last_attempt_is_terminal(clients, environment, content):
    queued(clients, content)
    _, factory = environment
    with factory.begin() as db:
        job = db.scalar(select(Job))
        job.state, job.attempts, job.lease_until = "running", MAX_ATTEMPTS, now() - 1
    assert claim_next(factory) is None
    with factory() as db:
        assert db.scalar(select(Job)).state == "failed"


def test_old_worker_cannot_publish_after_lease_takeover(clients, environment, content):
    queued(clients, content)
    settings, factory = environment

    def superseded(*args):
        files = fake_generate(*args)
        with factory.begin() as db:
            db.scalar(select(Job)).lease_token = uid()
        return files

    process_one(factory, settings, generator=superseded)
    with factory() as db:
        assert db.scalars(select(Artifact)).all() == []
    assert not list(settings.artifact_dir.rglob("*.pdf"))


def test_manual_retry_only_for_failed_latest_draft(clients, environment, content):
    author, reviewer = clients
    p = queued(clients, content)
    path = f"/api/proposals/{p['id']}/revisions/{p['revisions'][0]['id']}/retry"
    assert author.post(path).status_code == 409
    settings, factory = environment
    with factory.begin() as db:
        db.scalar(select(Job)).state = "failed"
    assert reviewer.post(path).status_code == 403
    assert author.post(path).status_code == 200
    with factory() as db:
        job = db.scalar(select(Job))
        assert job.state == "pending" and job.attempts == 0
