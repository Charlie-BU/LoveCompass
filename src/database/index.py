import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

_engine = None
_session_factory = None
_session_factory_pid = None


def _buildEngine():
    return create_engine(
        url=os.getenv("DATABASE_URI") or "",
        echo=False,
        pool_size=int(os.getenv("DB_POOL_SIZE", "5")),
        max_overflow=int(os.getenv("DB_MAX_OVERFLOW", "10")),
        pool_timeout=int(os.getenv("DB_POOL_TIMEOUT", "60")),
        pool_recycle=int(os.getenv("DB_POOL_RECYCLE", "3600")),
        pool_pre_ping=True,
    )


def _getSessionFactory():
    global _engine, _session_factory, _session_factory_pid
    pid = os.getpid()
    if _session_factory is None or _session_factory_pid != pid:
        if _engine is not None:
            _engine.dispose()
        _engine = _buildEngine()
        _session_factory = sessionmaker(autocommit=False, autoflush=False, bind=_engine)
        _session_factory_pid = pid
    return _session_factory


def session():
    return _getSessionFactory()()


def checkDatabaseConnection():
    with session() as db:
        db.execute(text("SELECT 1"))
    return True