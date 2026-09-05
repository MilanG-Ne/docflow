import json
from dataclasses import replace
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from docflow.api import create_app
from docflow.config import Settings
from docflow.db import session_factory
from docflow.models import Base
from docflow.seed import DEMO_PASSWORD, seed


@pytest.fixture
def environment(tmp_path):
    settings = replace(
        Settings(),
        database_url=f"sqlite:///{tmp_path}/test.db",
        artifact_dir=tmp_path / "artifacts",
        demo_mode=True,
        frontend_dir=tmp_path / "no-frontend",
    )
    factory = session_factory(settings.database_url)
    Base.metadata.create_all(factory.kw["bind"])
    seed(factory, settings, proposals=False)
    yield settings, factory
    factory.kw["bind"].dispose()


@pytest.fixture
def clients(environment):
    settings, factory = environment
    app = create_app(settings, factory)
    with TestClient(app) as author, TestClient(app) as reviewer:
        for client, email in [(author, "alex@alder.example"), (reviewer, "jamie@alder.example")]:
            result = client.post("/api/login", json={"email": email, "password": DEMO_PASSWORD})
            assert result.status_code == 200
            client.headers["X-CSRF-Token"] = result.json()["csrf"]
        yield author, reviewer


@pytest.fixture
def content():
    return json.loads((Path(__file__).resolve().parents[2] / "examples/meridian.json").read_text())


def fake_generate(template, directory, content, number, reference, binary):
    """Keep workflow tests independent of an external converter; conversion has its own suite."""
    directory.mkdir(parents=True)
    files = {"docx": directory / "proposal.docx", "pdf": directory / "proposal.pdf"}
    for kind, file in files.items():
        file.write_bytes(f"{kind}:revision-{number}:{content['title']}".encode())
    return files
