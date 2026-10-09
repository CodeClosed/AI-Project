import os
from pathlib import Path
import logging
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import declarative_base, sessionmaker

logger = logging.getLogger(__name__)

# Locate project root directory
BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = BASE_DIR / "nutrimenu.db"

DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DEFAULT_DB_PATH}")

# SQLite requires check_same_thread=False for multithreaded FastAPI requests
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """FastAPI dependency yielding a database session per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initializes database schema using versioned Alembic migrations with create_all fallback."""
    import backend.db_models  # noqa: F401 Ensure models are registered

    try:
        from alembic.config import Config
        from alembic import command
        alembic_ini_path = BASE_DIR / "alembic.ini"
        if alembic_ini_path.exists():
            alembic_cfg = Config(str(alembic_ini_path))
            alembic_cfg.set_main_option("sqlalchemy.url", DATABASE_URL)
            command.upgrade(alembic_cfg, "head")
            logger.info("Alembic schema migrations applied successfully to head.")
            return
    except Exception as alembic_err:
        logger.warning("Alembic migration notice: %s. Using Base.metadata create_all.", alembic_err)

    Base.metadata.create_all(bind=engine)
    try:
        from sqlalchemy import text
        with engine.connect() as conn:
            conn.execute(text("UPDATE users SET backup_codes = '[]' WHERE backup_codes IS NULL OR backup_codes = '' OR backup_codes = ' '"))
            conn.commit()
    except Exception:
        pass


