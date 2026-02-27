import os
from pathlib import Path
from threading import RLock
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

_engine = None
_session_factory = None
_lock = RLock()

def _load_db_env():
    project_root = Path(__file__).resolve().parents[2]
    env_path = project_root / ".env"
    if env_path.exists():
        load_dotenv(dotenv_path=env_path, override=False)

def _resolve_db_url() -> str:
    _load_db_env()
    db_url = os.getenv("DB_URL")
    if not db_url:
        raise RuntimeError(
            "DB_URL environment variable is not set. "
            "Please add it to your project root .env file."
        )
    return db_url

def get_shared_engine():
    """Return a process-wide singleton Engine with pool and timeout settings."""
    global _engine
    if _engine is None:
        with _lock:
            if _engine is None:
                db_url = _resolve_db_url()
                pool_size = int(os.getenv("DB_POOL_SIZE", "10"))
                max_overflow = int(os.getenv("DB_MAX_OVERFLOW", "20"))
                pool_recycle = int(os.getenv("DB_POOL_RECYCLE", "1800"))
                connect_timeout = int(os.getenv("DB_CONNECT_TIMEOUT", "5"))

                engine_kwargs = dict(
                    pool_pre_ping=True,
                    pool_size=pool_size,
                    max_overflow=max_overflow,
                    pool_recycle=pool_recycle,
                )

                if db_url.startswith(("postgresql", "postgres")):
                    engine_kwargs["connect_args"] = {"connect_timeout": connect_timeout}

                _engine = create_engine(db_url, **engine_kwargs)
    return _engine

def get_shared_session_factory():
    """Return a process-wide singleton scoped_session bound to shared engine."""
    global _session_factory
    if _session_factory is None:
        with _lock:
            if _session_factory is None:
                engine = get_shared_engine()
                _session_factory = scoped_session(sessionmaker(bind=engine))
    return _session_factory

def dispose_shared_engine():
    """Tear down shared engine and session factory (for shutdown/tests)."""
    global _engine, _session_factory
    with _lock:
        if _session_factory is not None:
            _session_factory.remove()
            _session_factory = None
        if _engine is not None:
            _engine.dispose()
            _engine = None