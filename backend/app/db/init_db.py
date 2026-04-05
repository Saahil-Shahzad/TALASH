from backend.app.db.session import Base, engine
from backend.app.models import analysis, candidate  # noqa: F401


def init_db() -> None:
    Base.metadata.create_all(bind=engine)


def safe_init_db() -> None:
    try:
        init_db()
    except Exception as exc:
        # Do not break API startup in managed DB environments where DDL may be restricted.
        print(f"[TALASH] DB initialization skipped: {exc}")

