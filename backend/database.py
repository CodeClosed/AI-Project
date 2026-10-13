import os
from pathlib import Path
import logging
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import declarative_base, sessionmaker

logger = logging.getLogger(__name__)

# Locate project root directory
BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = BASE_DIR / "nutrimenu.db"

RAW_DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DEFAULT_DB_PATH}")


def normalize_database_url(url: str) -> str:
    """
    Normalizes database connection URL for SQLAlchemy:
    - Replaces postgres:// or postgresql:// with postgresql+psycopg://
    - Enforces sslmode=require for non-localhost cloud Postgres (Neon, Supabase, Render)
    """
    clean_url = url.strip()
    if clean_url.startswith("postgres://"):
        clean_url = "postgresql+psycopg://" + clean_url[len("postgres://"):]
    elif clean_url.startswith("postgresql://") and not clean_url.startswith("postgresql+"):
        clean_url = "postgresql+psycopg://" + clean_url[len("postgresql://"):]

    if clean_url.startswith("postgresql"):
        parsed = urlparse(clean_url)
        # If remote host, ensure SSL is active
        if parsed.hostname and parsed.hostname not in {"localhost", "127.0.0.1"}:
            query = parse_qs(parsed.query)
            if "sslmode" not in query:
                query["sslmode"] = ["require"]
                new_query = urlencode(query, doseq=True)
                parsed = parsed._replace(query=new_query)
                clean_url = urlunparse(parsed)

    return clean_url


DATABASE_URL = normalize_database_url(RAW_DATABASE_URL)

engine_kwargs = {}
if DATABASE_URL.startswith("sqlite"):
    engine_kwargs["connect_args"] = {"check_same_thread": False}
else:
    # Production PostgreSQL connection pool settings optimized for cloud tiers (Neon/Supabase/Render)
    engine_kwargs["pool_pre_ping"] = True
    engine_kwargs["pool_size"] = int(os.getenv("DB_POOL_SIZE", "5"))
    engine_kwargs["max_overflow"] = int(os.getenv("DB_MAX_OVERFLOW", "5"))

engine = create_engine(
    DATABASE_URL,
    echo=False,
    **engine_kwargs
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
    """Initializes database schema using versioned Alembic migrations with create_all fallback in dev."""
    import backend.db_models  # noqa: F401 Ensure models are registered

    is_prod = (
        os.getenv("ENVIRONMENT", "").lower() in {"prod", "production"}
        or os.getenv("ENV", "").lower() in {"prod", "production"}
    )

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
        if is_prod:
            logger.error("CRITICAL PRODUCTION ERROR: Alembic database migration failed: %s", alembic_err)
            raise RuntimeError(f"Database migration failure: {alembic_err}") from alembic_err
        logger.warning("Alembic migration notice in dev: %s. Using Base.metadata create_all.", alembic_err)

    Base.metadata.create_all(bind=engine)
    try:
        with engine.connect() as conn:
            conn.execute(text("UPDATE users SET backup_codes = '[]' WHERE backup_codes IS NULL OR backup_codes = '' OR backup_codes = ' '"))
            conn.commit()
    except Exception:
        pass
