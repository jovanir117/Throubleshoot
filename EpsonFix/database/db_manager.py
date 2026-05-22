from contextlib import contextmanager
import json
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, scoped_session, sessionmaker


DATA_DIR = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)

DB_PATH = DATA_DIR / "epsonfix.db"
engine = create_engine(
    f"sqlite:///{DB_PATH}",
    connect_args={"check_same_thread": False},
    echo=False,
)


class Base(DeclarativeBase):
    pass


SessionLocal = scoped_session(sessionmaker(bind=engine))


def init_db():
    import models  # noqa: F401 - registers models before create_all

    Base.metadata.create_all(engine)
    session = get_session()
    try:
        session.execute(text(
            "CREATE TABLE IF NOT EXISTS schema_migrations "
            "(version VARCHAR(50) PRIMARY KEY, applied_at DATETIME DEFAULT CURRENT_TIMESTAMP)"
        ))
        _apply_migration_001_solution_step_actions(session)
        _apply_migration_002_indexes(session)
        session.commit()
    except Exception as e:
        session.rollback()
        import sys
        print(f"DB Migration warning: {e}", file=sys.stderr)
    finally:
        session.close()
        SessionLocal.remove()


def _apply_migration_001_solution_step_actions(session: Session) -> None:
    version = "001_solution_step_actions"
    applied = session.execute(
        text("SELECT 1 FROM schema_migrations WHERE version = :version"),
        {"version": version},
    ).first()
    if applied:
        return

    res = session.execute(text("PRAGMA table_info(solution_steps)")).fetchall()
    columns = {row[1] for row in res}
    if "action_key" not in columns:
        session.execute(text("ALTER TABLE solution_steps ADD COLUMN action_key VARCHAR(50)"))
    if "action_label" not in columns:
        session.execute(text("ALTER TABLE solution_steps ADD COLUMN action_label VARCHAR(100)"))
    session.execute(
        text("INSERT INTO schema_migrations (version) VALUES (:version)"),
        {"version": version},
    )


def _apply_migration_002_indexes(session: Session) -> None:
    version = "002_performance_indexes"
    applied = session.execute(
        text("SELECT 1 FROM schema_migrations WHERE version = :version"),
        {"version": version},
    ).first()
    if applied:
        return

    index_statements = [
        "CREATE INDEX IF NOT EXISTS ix_solutions_error_code ON solutions (error_code)",
        "CREATE INDEX IF NOT EXISTS ix_repair_sessions_printer_started ON repair_sessions (printer_id, started_at)",
        "CREATE INDEX IF NOT EXISTS ix_repair_sessions_error_code ON repair_sessions (error_code)",
        "CREATE INDEX IF NOT EXISTS ix_error_events_printer_occurred ON error_events (printer_id, occurred_at)",
    ]
    for statement in index_statements:
        session.execute(text(statement))
    session.execute(
        text("INSERT INTO schema_migrations (version) VALUES (:version)"),
        {"version": version},
    )


def get_session() -> Session:
    return SessionLocal()


@contextmanager
def session_scope():
    session = get_session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
        SessionLocal.remove()


def remove_current_session() -> None:
    SessionLocal.remove()


def seed_knowledge_base():
    import models  # noqa: F401 - ensure all mappers configured
    from models.solution import Solution, SolutionStep

    with session_scope() as session:
        if session.query(Solution).count() > 0:
            return
        kb_path = Path(__file__).parent.parent / "knowledge" / "solutions.json"
        if not kb_path.exists():
            return
        with open(kb_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        for sol_data in data:
            steps_data = sol_data.pop("steps", [])
            sol = Solution(**sol_data)
            session.add(sol)
            session.flush()
            for step_data in steps_data:
                step = SolutionStep(solution_id=sol.id, **step_data)
                session.add(step)
