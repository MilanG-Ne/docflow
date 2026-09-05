from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker


def session_factory(url: str) -> sessionmaker[Session]:
    sqlite = url.startswith("sqlite")
    engine = create_engine(
        url,
        pool_pre_ping=True,
        connect_args={"check_same_thread": False, "timeout": 15} if sqlite else {},
    )
    if sqlite:

        @event.listens_for(engine, "connect")
        def configure_sqlite(connection, _):
            connection.execute("PRAGMA foreign_keys=ON")
            connection.execute("PRAGMA journal_mode=WAL")

    return sessionmaker(engine, expire_on_commit=False)
