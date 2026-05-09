#!/usr/bin/env python3
"""
sync_claude_config.py — ~/.claude/ 의 hs 관련 설정을 프로젝트로 핫 카피.

대상 파일:
    ~/.claude/CLAUDE.md           → claude-config/CLAUDE.md
    ~/.claude/rules/*.md          → claude-config/rules/*.md
    ~/.claude/register_vault.ps1  → claude-config/scripts/register_vault.ps1

복사 안 함:
    settings.json (인증 정보), history.jsonl (개인 이력),
    cache / debug / sessions / projects / 기타 임시 데이터,
    plugins / commands / agents / styles / hooks (별개)

Usage:
    python scripts/sync_claude_config.py [--dry-run] [--target <project_root>]

기본 동작:
    - 대상 폴더 (claude-config/)가 없으면 생성
    - 기존 파일은 덮어쓰기 (사용자 ~/.claude/가 진실의 원천)
    - 결과 요약을 stdout에 표시

Output: JSON 형식 결과
"""

import argparse
import json
import os
import shutil
import sys
from pathlib import Path

if hasattr(sys.stdin, "reconfigure"):
    sys.stdin.reconfigure(encoding="utf-8")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")


# 복사 매핑: (source relative to ~/.claude/, dest relative to <project>/claude-config/)
COPY_MAP = [
    {"src": "CLAUDE.md", "dest": "CLAUDE.md", "type": "file"},
    {"src": "rules", "dest": "rules", "type": "dir"},
    {"src": "register_vault.ps1", "dest": "scripts/register_vault.ps1", "type": "file"},
]


def emit(response, exit_code=None):
    print(json.dumps(response, ensure_ascii=False, indent=2))
    if exit_code is None:
        exit_code = 0 if response.get("ok") else 1
    sys.exit(exit_code)


def copy_file(src: Path, dest: Path, dry_run: bool) -> dict:
    if not src.exists():
        return {"src": str(src), "dest": str(dest), "status": "skipped", "reason": "source not found"}
    if not src.is_file():
        return {"src": str(src), "dest": str(dest), "status": "skipped", "reason": "source not a file"}

    if dry_run:
        return {"src": str(src), "dest": str(dest), "status": "would_copy",
                "size_bytes": src.stat().st_size}

    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)
    return {"src": str(src), "dest": str(dest), "status": "copied",
            "size_bytes": dest.stat().st_size}


def copy_dir(src: Path, dest: Path, dry_run: bool) -> dict:
    if not src.exists():
        return {"src": str(src), "dest": str(dest), "status": "skipped", "reason": "source not found"}
    if not src.is_dir():
        return {"src": str(src), "dest": str(dest), "status": "skipped", "reason": "source not a directory"}

    files_info = []
    for item in sorted(src.iterdir()):
        if item.is_file() and not item.name.startswith("."):
            target = dest / item.name
            if dry_run:
                files_info.append({"file": item.name, "status": "would_copy",
                                   "size_bytes": item.stat().st_size})
            else:
                dest.mkdir(parents=True, exist_ok=True)
                shutil.copy2(item, target)
                files_info.append({"file": item.name, "status": "copied",
                                   "size_bytes": target.stat().st_size})

    return {"src": str(src), "dest": str(dest), "status": "dir_processed",
            "files": files_info, "file_count": len(files_info)}


def sync(target_root: Path, dry_run: bool) -> dict:
    home_claude = Path.home() / ".claude"
    if not home_claude.exists():
        return {"ok": False,
                "code": "no_claude_home",
                "message": f"~/.claude 디렉토리 없음: {home_claude}",
                "details": {}}

    config_root = target_root / "claude-config"

    results = []
    for entry in COPY_MAP:
        src_path = home_claude / entry["src"]
        dest_path = config_root / entry["dest"]
        if entry["type"] == "file":
            results.append(copy_file(src_path, dest_path, dry_run))
        elif entry["type"] == "dir":
            results.append(copy_dir(src_path, dest_path, dry_run))

    return {
        "ok": True,
        "dry_run": dry_run,
        "source": str(home_claude),
        "target": str(config_root),
        "items": results,
    }


def main():
    parser = argparse.ArgumentParser(
        prog="sync_claude_config",
        description="Hot-copy ~/.claude/ to project claude-config/",
    )
    parser.add_argument("--dry-run", action="store_true",
                        help="실제 복사하지 않고 계획만 표시")
    parser.add_argument("--target", default=None,
                        help="프로젝트 루트 (기본: cwd)")
    args = parser.parse_args()

    try:
        target = Path(args.target).resolve() if args.target else Path.cwd()
        result = sync(target, args.dry_run)
        emit(result)
    except SystemExit:
        raise
    except Exception as e:
        emit({"ok": False, "code": "internal_error",
              "message": f"내부 오류: {e}",
              "details": {"exception": type(e).__name__}}, exit_code=1)


if __name__ == "__main__":
    main()
