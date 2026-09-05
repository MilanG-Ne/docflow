import hashlib

from conftest import fake_generate
from fastapi.testclient import TestClient
from sqlalchemy import select

from docflow.api import create_app
from docflow.auth import hasher
from docflow.models import Artifact, User
from docflow.worker import process_one


def ready(author, environment, content):
    response = author.post("/api/proposals", json=content)
    assert response.status_code == 201, response.text
    proposal = response.json()
    settings, factory = environment
    assert process_one(factory, settings, generator=fake_generate)
    return author.get(f"/api/proposals/{proposal['id']}").json()


def route(proposal):
    return f"/api/proposals/{proposal['id']}/revisions/{proposal['revisions'][0]['id']}"


def test_approval_is_bound_to_original_revision_and_files(clients, environment, content):
    author, reviewer = clients
    proposal = ready(author, environment, content)
    revision = proposal["revisions"][0]
    assert author.post(route(proposal) + "/submit").status_code == 200
    decision = {
        "decision": "approved",
        "comment": "Scope and fees are agreed.",
        "content_hash": revision["content_hash"],
    }
    assert reviewer.post(route(proposal) + "/review", json=decision).status_code == 200
    original = {
        f["kind"]: author.get(f"/api/artifacts/{f['id']}").content for f in revision["artifacts"]
    }
    content["title"] = "Client portal redesign with reporting"
    updated = author.post(
        f"/api/proposals/{proposal['id']}/revisions",
        json={"expected_number": 1, "content": content},
    )
    assert updated.status_code == 201
    newest, approved = updated.json()["revisions"]
    assert newest["number"] == 2 and newest["state"] == "draft" and newest["review"] is None
    assert approved["state"] == "approved"
    assert approved["review"]["content_hash"] == revision["content_hash"]
    assert approved["review"]["artifact_hashes"] == {
        k: hashlib.sha256(v).hexdigest() for k, v in original.items()
    }
    for file in approved["artifacts"]:
        assert author.get(f"/api/artifacts/{file['id']}").content == original[file["kind"]]
    assert reviewer.post(route(proposal) + "/review", json=decision).status_code == 409


def test_stale_edit_does_not_create_revision(clients, environment, content):
    author, _ = clients
    proposal = ready(author, environment, content)
    path = f"/api/proposals/{proposal['id']}/revisions"
    payload = {"expected_number": 1, "content": content}
    assert author.post(path, json=payload).status_code == 201
    assert author.post(path, json=payload).status_code == 409
    assert len(author.get(f"/api/proposals/{proposal['id']}").json()["revisions"]) == 2


def test_new_revision_prevents_approval_of_obsolete_review(clients, environment, content):
    author, reviewer = clients
    p = ready(author, environment, content)
    assert author.post(route(p) + "/submit").status_code == 200
    assert (
        author.post(
            f"/api/proposals/{p['id']}/revisions", json={"expected_number": 1, "content": content}
        ).status_code
        == 201
    )
    response = reviewer.post(
        route(p) + "/review",
        json={
            "decision": "approved",
            "comment": "Looks good to me",
            "content_hash": p["revisions"][0]["content_hash"],
        },
    )
    assert response.status_code == 409


def test_permissions_and_csrf_are_enforced_by_server(clients, environment, content):
    author, reviewer = clients
    p = ready(author, environment, content)
    assert reviewer.post("/api/proposals", json=content).status_code == 403
    assert reviewer.post(route(p) + "/submit").status_code == 403
    assert (
        author.post(
            route(p) + "/review",
            json={
                "decision": "approved",
                "comment": "Looks good to me",
                "content_hash": p["revisions"][0]["content_hash"],
            },
        ).status_code
        == 403
    )
    assert author.post(route(p) + "/submit", headers={"X-CSRF-Token": "wrong"}).status_code == 403
    assert (
        author.post(route(p) + "/submit", headers={"Origin": "https://foreign.example"}).status_code
        == 403
    )
    assert author.post("/api/logout").status_code == 204
    assert author.get("/api/proposals").status_code == 401


def test_another_author_cannot_read_or_download(clients, environment, content):
    author, _ = clients
    p = ready(author, environment, content)
    settings, factory = environment
    with factory.begin() as db:
        db.add(
            User(
                email="other@alder.example",
                name="Other Author",
                role="author",
                password_hash=hasher.hash("other-password"),
            )
        )
    with TestClient(create_app(settings, factory)) as stranger:
        assert (
            stranger.post(
                "/api/login", json={"email": "other@alder.example", "password": "other-password"}
            ).status_code
            == 200
        )
        assert stranger.get("/api/proposals").json() == []
        assert stranger.get(f"/api/proposals/{p['id']}").status_code == 404
        assert (
            stranger.get(f"/api/artifacts/{p['revisions'][0]['artifacts'][0]['id']}").status_code
            == 404
        )


def test_generation_and_hash_must_match_before_review(clients, environment, content):
    author, reviewer = clients
    p = author.post("/api/proposals", json=content).json()
    assert author.post(route(p) + "/submit").status_code == 409
    settings, factory = environment
    process_one(factory, settings, generator=fake_generate)
    assert author.post(route(p) + "/submit").status_code == 200
    assert (
        reviewer.post(
            route(p) + "/review",
            json={
                "decision": "approved",
                "comment": "Reviewed the proposal",
                "content_hash": "0" * 64,
            },
        ).status_code
        == 409
    )


def test_change_request_requires_new_revision(clients, environment, content):
    author, reviewer = clients
    p = ready(author, environment, content)
    author.post(route(p) + "/submit")
    assert (
        reviewer.post(
            route(p) + "/review",
            json={
                "decision": "changes_requested",
                "comment": "Please clarify the delivery schedule.",
                "content_hash": p["revisions"][0]["content_hash"],
            },
        ).status_code
        == 200
    )
    assert author.post(route(p) + "/submit").status_code == 409
    assert (
        author.post(
            f"/api/proposals/{p['id']}/revisions", json={"expected_number": 1, "content": content}
        ).status_code
        == 201
    )


def test_tampered_file_cannot_be_downloaded(clients, environment, content):
    author, _ = clients
    ready(author, environment, content)
    settings, factory = environment
    with factory() as db:
        file = db.scalar(select(Artifact).limit(1))
        (settings.artifact_dir / file.path).write_bytes(b"tampered")
        assert author.get(f"/api/artifacts/{file.id}").status_code == 409
