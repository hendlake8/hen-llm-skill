"""
_user.py — 공유 user detection / sanitization helpers.

cm_state.py / plan_state.py 등이 import 사용.
"""

import os
import re
import subprocess
from pathlib import Path


def sanitize_user(name: str) -> str:
    """Option A 최소 처리: 차단 글자만 _로 치환, trim, lstrip dot."""
    if not name:
        return ""
    name = re.sub(r'[/\\:<>"|?*\x00]', '_', name)
    name = name.strip().lstrip('.')
    return name or "unknown"


def detect_user(project_root: Path) -> dict:
    """git → OS 순서로 사용자 식별.

    Returns: {user, source, raw}
        user: sanitized 사용자명
        source: "git" / "os" / "fallback"
        raw: 원본 이름 (sanitize 전)
    """
    # 1) git config user.name
    if (project_root / ".git").exists():
        try:
            result = subprocess.run(
                ["git", "-C", str(project_root), "config", "user.name"],
                capture_output=True, text=True, encoding="utf-8", timeout=5,
            )
            if result.returncode == 0 and result.stdout.strip():
                raw = result.stdout.strip()
                return {"user": sanitize_user(raw), "source": "git", "raw": raw}
        except (subprocess.SubprocessError, FileNotFoundError, OSError):
            pass

    # 2) OS user
    raw = os.environ.get("USERNAME") or os.environ.get("USER")
    if raw:
        return {"user": sanitize_user(raw), "source": "os", "raw": raw}

    return {"user": "unknown", "source": "fallback", "raw": None}
