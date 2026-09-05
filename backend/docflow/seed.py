import json
from pathlib import Path

from sqlalchemy import select

from .auth import hasher
from .config import Settings
from .db import session_factory
from .models import User
from .schemas import ProposalContent
from .workflow import create_proposal

DEMO_PASSWORD = "proposal-demo-2026"


def seed(factory, settings: Settings, *, proposals=True):
    if not settings.demo_mode:
        raise RuntimeError("Demo seeding requires DEMO_MODE=true")
    with factory.begin() as db:
        for email, name, role in [
            ("alex@alder.example", "Alex Novak", "author"),
            ("jamie@alder.example", "Jamie Lee", "reviewer"),
        ]:
            if db.scalar(select(User).where(User.email == email)) is None:
                db.add(
                    User(
                        email=email, name=name, role=role, password_hash=hasher.hash(DEMO_PASSWORD)
                    )
                )
        db.flush()
        author = db.scalar(select(User).where(User.email == "alex@alder.example"))
        from .models import Proposal

        if proposals and db.scalar(select(Proposal.id).limit(1)) is None:
            example_dir = Path(__file__).resolve().parents[2] / "examples"
            for path in sorted(example_dir.glob("*.json")):
                content = ProposalContent.model_validate(json.loads(path.read_text()))
                create_proposal(db, author, content, settings.template_path)


if __name__ == "__main__":
    settings = Settings()
    seed(session_factory(settings.database_url), settings)
