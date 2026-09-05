"""Run against an isolated PostgreSQL database; each test gets its own schema."""

import json
import os
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path
from threading import Barrier
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, select, text

from docflow.config import Settings
from docflow.db import session_factory
from docflow.models import Base, Job, Proposal, Revision, User
from docflow.schemas import ProposalContent
from docflow.seed import seed
from docflow.worker import claim_next
from docflow.workflow import create_proposal, revise

pytestmark = [
    pytest.mark.postgres,
    pytest.mark.skipif(not os.getenv("TEST_POSTGRES_URL"), reason="TEST_POSTGRES_URL is not set"),
]


@pytest.fixture
def pg():
    url = os.environ["TEST_POSTGRES_URL"]
    schema = "test_" + uuid4().hex
    admin = create_engine(url)
    with admin.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    separator = "&" if "?" in url else "?"
    factory = session_factory(url + separator + "options=-csearch_path%3D" + schema)
    Base.metadata.create_all(factory.kw["bind"])
    settings = replace(Settings(), demo_mode=True)
    seed(factory, settings, proposals=False)
    content = ProposalContent.model_validate(
        json.loads((Path(__file__).resolve().parents[2] / "examples/meridian.json").read_text())
    )
    with factory.begin() as db:
        user = db.scalar(select(User).where(User.role == "author"))
        proposal = create_proposal(db, user, content, settings.template_path)
        proposal_id, user_id = proposal.id, user.id
    yield factory, settings, content, proposal_id, user_id
    factory.kw["bind"].dispose()
    with admin.begin() as connection:
        connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
    admin.dispose()


def test_two_workers_do_not_claim_the_same_job(pg):
    factory, *_ = pg
    barrier = Barrier(2)

    def claim():
        barrier.wait()
        return claim_next(factory)

    with ThreadPoolExecutor(max_workers=2) as pool:
        claims = list(pool.map(lambda _: claim(), range(2)))
    assert sum(c is not None for c in claims) == 1
    with factory() as db:
        assert db.scalar(select(Job)).attempts == 1


def test_simultaneous_edits_create_only_one_next_revision(pg):
    factory, settings, content, proposal_id, user_id = pg
    barrier = Barrier(2)

    def edit():
        barrier.wait()
        try:
            with factory.begin() as db:
                revise(db, db.get(User, user_id), proposal_id, 1, content, settings.template_path)
            return 201
        except HTTPException as error:
            return error.status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(lambda _: edit(), range(2)))
    assert sorted(outcomes) == [201, 409]
    with factory() as db:
        assert db.get(Proposal, proposal_id).latest_number == 2
        assert len(db.scalars(select(Revision)).all()) == 2
