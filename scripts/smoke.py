"""Exercise the shipped application over HTTP, including actual document conversion."""
import argparse
import hashlib
import http.cookiejar
import json
import time
import urllib.error
import urllib.request
from pathlib import Path


class Client:
    def __init__(self, base, email):
        self.base = base
        self.csrf = ""
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
        session = self.request("/login", {"email": email, "password": "proposal-demo-2026"})
        self.csrf = session["csrf"]

    def request(self, path, data=None, *, post=False, raw=False):
        payload = json.dumps(data).encode() if data is not None else b"" if post else None
        request = urllib.request.Request(self.base + "/api" + path, data=payload,
            headers={"Content-Type": "application/json", "X-CSRF-Token": self.csrf})
        with self.opener.open(request, timeout=20) as response:
            body = response.read()
            return body if raw else json.loads(body) if body else None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    author = Client(args.base_url, "alex@alder.example")
    reviewer = Client(args.base_url, "jamie@alder.example")
    content = json.loads((Path(__file__).resolve().parents[1] / "examples/meridian.json").read_text())
    proposal = author.request("/proposals", content)
    path = f"/proposals/{proposal['id']}"
    for _ in range(90):
        proposal = author.request(path)
        revision = proposal["revisions"][0]
        if revision["job"]["state"] == "completed":
            break
        if revision["job"]["state"] == "failed":
            raise RuntimeError(revision["job"]["error"])
        time.sleep(1)
    else:
        raise RuntimeError("Timed out waiting for document generation")
    revision_path = f"{path}/revisions/{revision['id']}"
    files = {f["kind"]: author.request(f"/artifacts/{f['id']}", raw=True) for f in revision["artifacts"]}
    assert files["docx"].startswith(b"PK") and files["pdf"].startswith(b"%PDF-")
    author.request(revision_path + "/submit", post=True)
    reviewer.request(revision_path + "/review", {"decision": "approved", "comment": "Scope, fees, and generated documents reviewed.", "content_hash": revision["content_hash"]})
    approved = author.request(path)["revisions"][0]
    assert approved["review"]["artifact_hashes"] == {k: hashlib.sha256(v).hexdigest() for k, v in files.items()}
    content["title"] = "Client portal redesign with reporting"
    updated = author.request(path + "/revisions", {"expected_number": 1, "content": content})
    assert updated["revisions"][0]["state"] == "draft"
    assert updated["revisions"][0]["review"] is None
    assert updated["revisions"][1]["state"] == "approved"
    for f in revision["artifacts"]:
        assert author.request(f"/artifacts/{f['id']}", raw=True) == files[f["kind"]]
    if args.output_dir:
        args.output_dir.mkdir(parents=True, exist_ok=True)
        for kind, data in files.items():
            (args.output_dir / f"approved-proposal.{kind}").write_bytes(data)
        (args.output_dir / "approval-record.json").write_text(json.dumps(approved["review"], indent=2) + "\n")
    print("PASS: create → generate Word/PDF → review → approve → revise; original approved files unchanged")


if __name__ == "__main__":
    main()
