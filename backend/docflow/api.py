import secrets
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import delete, select, text
from sqlalchemy.orm import Session

from . import auth, workflow
from .artifacts import verified_path
from .config import Settings
from .db import session_factory
from .models import Artifact, LoginSession, Proposal, Revision, User, now
from .schemas import LoginInput, NewRevision, ProposalContent, ReviewInput


def create_app(settings: Settings | None = None, factory=None) -> FastAPI:
    settings = settings or Settings()
    factory = factory or session_factory(settings.database_url)

    @asynccontextmanager
    async def lifespan(app):
        settings.artifact_dir.mkdir(parents=True, exist_ok=True)
        yield

    app = FastAPI(
        title="DocFlow",
        version="0.1.0",
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
        lifespan=lifespan,
    )
    app.state.settings, app.state.factory = settings, factory

    @app.middleware("http")
    async def request_policy(request: Request, call_next):
        if request.method not in {"GET", "HEAD", "OPTIONS"}:
            origin = request.headers.get("origin")
            if origin and origin != settings.origin:
                return JSONResponse({"detail": "Request origin is not allowed"}, status_code=403)
            if request.headers.get("sec-fetch-site") == "cross-site":
                return JSONResponse(
                    {"detail": "Cross-site requests are not allowed"}, status_code=403
                )
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "same-origin"
        response.headers["X-Frame-Options"] = "DENY"
        if request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
        return response

    def database():
        with factory() as db:
            yield db

    DB = Annotated[Session, Depends(database)]

    def identity(request: Request, db: DB):
        return auth.authenticate(request, db)

    Identity = Annotated[tuple[User, LoginSession], Depends(identity)]

    def user_info(user, session):
        return {
            "user": {"id": user.id, "name": user.name, "email": user.email, "role": user.role},
            "csrf": session.csrf,
        }

    @app.get("/api/health")
    def health(db: DB):
        db.execute(text("SELECT 1"))
        return {"status": "ok"}

    @app.get("/api/config")
    def config():
        return {"demo_mode": settings.demo_mode}

    @app.post("/api/login")
    def login(data: LoginInput, request: Request, response: Response, db: DB):
        user = db.scalar(select(User).where(User.email == data.email.lower()))
        if (
            not auth.password_matches(
                data.password, user.password_hash if user else auth.DUMMY_HASH
            )
            or not user
        ):
            raise HTTPException(401, "Email or password is incorrect")
        db.execute(delete(LoginSession).where(LoginSession.expires_at <= now()))
        old = request.cookies.get(auth.COOKIE_NAME)
        if old:
            db.execute(delete(LoginSession).where(LoginSession.token_hash == auth.digest(old)))
        token = secrets.token_urlsafe(32)
        session = LoginSession(
            token_hash=auth.digest(token),
            user_id=user.id,
            csrf=secrets.token_hex(32),
            expires_at=now() + auth.SESSION_SECONDS,
        )
        db.add(session)
        db.commit()
        response.set_cookie(
            auth.COOKIE_NAME,
            token,
            max_age=auth.SESSION_SECONDS,
            httponly=True,
            secure=settings.cookie_secure,
            samesite="strict",
            path="/",
        )
        return user_info(user, session)

    @app.get("/api/me")
    def me(identity: Identity):
        return user_info(*identity)

    @app.post("/api/logout", status_code=204)
    def logout(response: Response, db: DB, identity: Identity):
        db.delete(identity[1])
        db.commit()
        response.delete_cookie(
            auth.COOKIE_NAME,
            path="/",
            secure=settings.cookie_secure,
            httponly=True,
            samesite="strict",
        )

    @app.get("/api/proposals")
    def proposals(db: DB, identity: Identity):
        query = select(Proposal).order_by(Proposal.created_at.desc(), Proposal.id)
        if identity[0].role != "reviewer":
            query = query.where(Proposal.owner_id == identity[0].id)
        result = []
        for p in db.scalars(query).all():
            r = db.scalar(
                select(Revision).where(
                    Revision.proposal_id == p.id, Revision.number == p.latest_number
                )
            )
            result.append(
                {
                    "id": p.id,
                    "title": r.content["title"],
                    "client_name": r.content["client_name"],
                    "state": r.state,
                    "number": r.number,
                    "currency": r.content["currency"],
                    "total_cents": ProposalContent.model_validate(r.content).total_cents,
                    "created_at": p.created_at,
                }
            )
        return result

    @app.post("/api/proposals", status_code=201)
    def create(data: ProposalContent, db: DB, identity: Identity):
        proposal = workflow.create_proposal(db, identity[0], data, settings.template_path)
        db.commit()
        return workflow.detail(db, proposal)

    @app.get("/api/proposals/{proposal_id}")
    def get(proposal_id: str, db: DB, identity: Identity):
        return workflow.detail(db, workflow.visible_proposal(db, proposal_id, identity[0]))

    @app.post("/api/proposals/{proposal_id}/revisions", status_code=201)
    def revise(proposal_id: str, data: NewRevision, db: DB, identity: Identity):
        p = workflow.revise(
            db, identity[0], proposal_id, data.expected_number, data.content, settings.template_path
        )
        db.commit()
        return workflow.detail(db, p)

    @app.post("/api/proposals/{proposal_id}/revisions/{revision_id}/submit")
    def submit(proposal_id: str, revision_id: str, db: DB, identity: Identity):
        workflow.submit(db, identity[0], proposal_id, revision_id)
        db.commit()
        return {"ok": True}

    @app.post("/api/proposals/{proposal_id}/revisions/{revision_id}/review")
    def review(proposal_id: str, revision_id: str, data: ReviewInput, db: DB, identity: Identity):
        workflow.review(db, identity[0], proposal_id, revision_id, data, settings.artifact_dir)
        db.commit()
        return {"ok": True}

    @app.post("/api/proposals/{proposal_id}/revisions/{revision_id}/retry")
    def retry(proposal_id: str, revision_id: str, db: DB, identity: Identity):
        workflow.retry(db, identity[0], proposal_id, revision_id)
        db.commit()
        return {"ok": True}

    @app.get("/api/artifacts/{artifact_id}")
    def download(artifact_id: str, db: DB, identity: Identity):
        file = db.get(Artifact, artifact_id)
        if file is None:
            raise HTTPException(404, "File not found")
        revision = db.get(Revision, file.revision_id)
        workflow.visible_proposal(db, revision.proposal_id, identity[0])
        path = verified_path(file, settings.artifact_dir)
        media = (
            "application/pdf"
            if file.kind == "pdf"
            else "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
        return FileResponse(
            path,
            media_type=media,
            filename=f"proposal-{revision.proposal_id[:8]}-r{revision.number}.{file.kind}",
        )

    if settings.frontend_dir.is_dir():
        app.mount("/", StaticFiles(directory=settings.frontend_dir, html=True), name="frontend")
    return app


app = create_app()
