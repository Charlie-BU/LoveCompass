import json
from typing import Any

from src.cli.constants import IMMORTALITY_HOME_DIR

_SESSION_DIR = IMMORTALITY_HOME_DIR
_SESSION_FILE = _SESSION_DIR / "session.json"


def loadLocalSession() -> dict[str, Any]:
    """
    加载本地 session
    """
    if not _SESSION_FILE.exists():
        return {}
    try:
        raw = _SESSION_FILE.read_text(encoding="utf-8").strip()
        if raw == "":
            return {}
        data = json.loads(raw)
        if not isinstance(data, dict):
            return {}
        return data
    except Exception:
        return {}


def saveLocalSession(session_data: dict[str, Any]) -> None:
    """
    保存本地 session
    """
    _SESSION_DIR.mkdir(parents=True, exist_ok=True)
    _SESSION_FILE.write_text(
        json.dumps(session_data, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def clearLocalSession() -> None:
    """
    清除本地 session
    """
    if _SESSION_FILE.exists():
        _SESSION_FILE.unlink()
