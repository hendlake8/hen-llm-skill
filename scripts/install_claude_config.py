#!/usr/bin/env python3
"""
install_claude_config.py — 프로젝트의 claude-config/ 를 ~/.claude/ 에 설치.
새 PC 설치 시 사용. 저장소(claude-config/)가 진실의 원천(SSOT)이다.

설치 매핑:
    claude-config/CLAUDE.md           → ~/.claude/CLAUDE.md          (복사)
    claude-config/rules/              ← ~/.claude/rules              (junction/symlink)
    claude-config/scripts/register_vault.ps1
                                      → ~/.claude/register_vault.ps1 (복사)

rules 는 복사가 아니라 junction(Windows) / symlink(Unix) 으로 연결한다.
저장소의 rules 수정이 즉시 라이브에 반영되고, 역방향 동기화가 필요 없다.
단일 파일(CLAUDE.md 등)은 junction 불가(폴더 전용)라 복사를 유지한다 —
수정은 항상 claude-config/ 쪽에서 하고 본 스크립트로 재배포한다.

안전 가드:
    기본: 기존 파일/폴더와 충돌 시 에러로 중단 (사용자 데이터 보호)
    --force: 기존 파일 덮어쓰기, 기존 rules 폴더 삭제 후 연결 (백업 없음)
    --backup: 덮어쓰기/연결 전 ~/.claude/.../<이름>.bak 으로 백업
    --dry-run: 실제 변경 안 함, 계획만

설치 후 안내:
    OBSIDIAN_VAULT 환경 변수 미설정 시 설정 방법 안내
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


# 설치 매핑: (src relative to claude-config/, dest relative to ~/.claude/)
# type: file = 복사, junction = 폴더 연결 (Windows junction / Unix symlink)
COPY_MAP = [
    {"src": "CLAUDE.md", "dest": "CLAUDE.md", "type": "file"},
    {"src": "rules", "dest": "rules", "type": "junction"},
    {"src": "scripts/register_vault.ps1", "dest": "register_vault.ps1", "type": "file"},
]


def emit(response, exit_code=None):
    print(json.dumps(response, ensure_ascii=False, indent=2))
    if exit_code is None:
        exit_code = 0 if response.get("ok") else 1
    sys.exit(exit_code)


def install_file(src: Path, dest: Path, dry_run: bool, force: bool, backup: bool) -> dict:
    if not src.exists() or not src.is_file():
        return {"src": str(src), "dest": str(dest), "status": "skipped",
                "reason": "source missing or not a file"}

    exists = dest.exists()
    if exists and not (force or backup):
        return {"src": str(src), "dest": str(dest), "status": "conflict",
                "reason": "existing file (use --force or --backup)"}

    if dry_run:
        action = "would_overwrite" if exists else "would_copy"
        return {"src": str(src), "dest": str(dest), "status": action,
                "size_bytes": src.stat().st_size,
                "would_backup": exists and backup}

    backup_path = None
    if exists and backup:
        backup_path = dest.with_suffix(dest.suffix + ".bak")
        shutil.copy2(dest, backup_path)

    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)

    return {"src": str(src), "dest": str(dest),
            "status": "overwritten" if exists else "copied",
            "backup": str(backup_path) if backup_path else None,
            "size_bytes": dest.stat().st_size}


def create_link(src: Path, dest: Path) -> None:
    """dest 를 src 폴더로 연결한다 (Windows junction / Unix symlink)."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    if os.name == "nt":
        import _winapi
        _winapi.CreateJunction(str(src), str(dest))
    else:
        os.symlink(str(src), str(dest), target_is_directory=True)


def is_link_dir(path: Path) -> bool:
    """path 가 junction/symlink 인지 판별 (실폴더면 False)."""
    return os.path.normcase(os.path.realpath(path)) != os.path.normcase(os.path.abspath(path))


def install_junction(src: Path, dest: Path, dry_run: bool, force: bool, backup: bool) -> dict:
    if not src.exists() or not src.is_dir():
        return {"src": str(src), "dest": str(dest), "status": "skipped",
                "reason": "source missing or not a directory"}

    src_real = os.path.normcase(os.path.realpath(src))

    if os.path.lexists(dest):  # 깨진 링크도 감지 (exists 는 링크를 따라가므로 부적합)
        # 이미 원하는 대상을 가리키는 링크면 할 일 없음
        if is_link_dir(dest) and os.path.normcase(os.path.realpath(dest)) == src_real:
            return {"src": str(src), "dest": str(dest), "status": "ok",
                    "reason": "junction already points to source"}

        if not (force or backup):
            return {"src": str(src), "dest": str(dest), "status": "conflict",
                    "reason": "existing dir/link (use --force or --backup)"}

        if dry_run:
            return {"src": str(src), "dest": str(dest),
                    "status": "would_replace_with_junction",
                    "would_backup": backup}

        if backup:
            backup_path = dest.with_name(dest.name + ".bak")
            if backup_path.exists():
                return {"src": str(src), "dest": str(dest), "status": "conflict",
                        "reason": f"backup path already exists: {backup_path}"}
            dest.rename(backup_path)
        else:
            if is_link_dir(dest):
                os.rmdir(dest)  # 링크만 제거 (원본 폴더 내용은 보존)
            else:
                shutil.rmtree(dest)

    if dry_run:
        return {"src": str(src), "dest": str(dest), "status": "would_create_junction"}

    create_link(src, dest)
    return {"src": str(src), "dest": str(dest), "status": "junction_created",
            "target": str(src)}


def install(target_root: Path, dry_run: bool, force: bool, backup: bool) -> dict:
    config_root = target_root / "claude-config"
    if not config_root.exists():
        return {"ok": False, "code": "no_claude_config",
                "message": f"claude-config/ 폴더 없음: {config_root}",
                "details": {"hint": "저장소 git clone 여부와 --target 경로를 확인"}}

    home_claude = Path.home() / ".claude"

    results = []
    has_conflict = False
    for entry in COPY_MAP:
        src_path = config_root / entry["src"]
        dest_path = home_claude / entry["dest"]
        if entry["type"] == "file":
            r = install_file(src_path, dest_path, dry_run, force, backup)
            results.append(r)
            if r.get("status") == "conflict":
                has_conflict = True
        elif entry["type"] == "junction":
            r = install_junction(src_path, dest_path, dry_run, force, backup)
            results.append(r)
            if r.get("status") == "conflict":
                has_conflict = True

    # OBSIDIAN_VAULT 환경 변수 점검
    obsidian_vault = os.environ.get("OBSIDIAN_VAULT")

    return {
        "ok": not has_conflict,
        "code": "conflict" if has_conflict else "ok",
        "dry_run": dry_run,
        "source": str(config_root),
        "target": str(home_claude),
        "items": results,
        "has_conflict": has_conflict,
        "env_check": {
            "OBSIDIAN_VAULT": obsidian_vault,
            "set": bool(obsidian_vault),
            "hint": None if obsidian_vault else (
                "OBSIDIAN_VAULT 환경 변수 미설정. 설정 방법:\n"
                "  Windows: setx OBSIDIAN_VAULT \"D:\\path\\to\\vault\"\n"
                "  Unix:    export OBSIDIAN_VAULT=/path/to/vault"
            ),
        },
        "next_steps": (
            ["충돌 해결: --force (덮어쓰기) 또는 --backup (백업 후 덮어쓰기)"]
            if has_conflict else
            [
                "OBSIDIAN_VAULT 환경 변수 설정 (위 hint 참고)" if not obsidian_vault else None,
                "Claude Code 재시작 (룰 재로드)",
            ]
        ),
    }


def main():
    parser = argparse.ArgumentParser(
        prog="install_claude_config",
        description="Install project claude-config/ to ~/.claude/ (files copied, rules linked)",
    )
    parser.add_argument("--dry-run", action="store_true",
                        help="실제 복사하지 않고 계획만 표시")
    parser.add_argument("--force", action="store_true",
                        help="기존 파일 덮어쓰기 (백업 없음)")
    parser.add_argument("--backup", action="store_true",
                        help="덮어쓰기 전 .bak 백업")
    parser.add_argument("--target", default=None,
                        help="프로젝트 루트 (기본: cwd)")
    args = parser.parse_args()

    if args.force and args.backup:
        emit({"ok": False, "code": "invalid_args",
              "message": "--force와 --backup 동시 사용 불가. 하나만 선택.",
              "details": {}}, exit_code=2)

    try:
        target = Path(args.target).resolve() if args.target else Path.cwd()
        result = install(target, args.dry_run, args.force, args.backup)
        emit(result)
    except SystemExit:
        raise
    except Exception as e:
        emit({"ok": False, "code": "internal_error",
              "message": f"내부 오류: {e}",
              "details": {"exception": type(e).__name__}}, exit_code=1)


if __name__ == "__main__":
    main()
