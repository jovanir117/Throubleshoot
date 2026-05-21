from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker, Session
from pathlib import Path
import json

DATA_DIR = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)

DB_PATH = DATA_DIR / "epsonfix.db"
engine = create_engine(f"sqlite:///{DB_PATH}", echo=False)


class Base(DeclarativeBase):
    pass


SessionLocal = sessionmaker(engine)


def init_db():
    import models  # noqa — registers all models with mapper before create_all
    Base.metadata.create_all(engine)


def get_session() -> Session:
    return SessionLocal()


def seed_knowledge_base():
    """Carga knowledge base inicial si DB está vacía."""
    import models  # noqa — ensure all mappers configured
    from models.solution import Solution, SolutionStep
    session = get_session()
    try:
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
        session.commit()
    finally:
        session.close()
