#!/usr/bin/env python3
"""
context_usage.py — Claude Code 세션의 컨텍스트 / 토큰 사용량 측정.

JSONL 파싱을 통해 정확한 측정 우선, 실패 시 fallback 모드.

Usage:
    python context_usage.py [--project-root <path>]

Output: JSON to stdout. ok=True면 측정 성공, fallback_reason 포함되면 추정 모드.

Exit codes:
    0 정상 응답 (성공 또는 fallback)
    1 내부 오류
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path

# Force UTF-8 stdio (Windows cp949 회피)
if hasattr(sys.stdin, "reconfigure"):
    sys.stdin.reconfigure(encoding="utf-8")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")


# ============================================================
# Helpers
# ============================================================

def derive_project_key(project_path: Path) -> str:
    """프로젝트 경로 → Claude Code 세션 폴더 키.
    예: D:\\GitPrjs\\hen-llm-skill → D--GitPrjs-hen-llm-skill
    경로 구분자(\\, /, :)를 각각 1:1로 -로 치환 (인접해도 각자 치환).
    """
    return re.sub(r"[\\/:]", "-", str(project_path).rstrip("\\/"))


def get_context_limit(model: str, observed_total: int = 0):
    """모델 이름 → 컨텍스트 한계 토큰 수. 알 수 없으면 None.

    JSONL의 model 필드는 보통 base name만 (예: 'claude-opus-4-7') —
    '[1m]' 접미사가 없을 수 있음. 그래서:
    1) '[1m]' 명시되면 1M
    2) 관측된 사용량이 200k 초과 → 1M 모델로 추정 (반응형 검출)
    3) 모델별 default 200k
    """
    if not model:
        # 모델 모르지만 관측치로 추정 가능
        if observed_total > 200_000:
            return 1_000_000
        return None

    if "[1m]" in model:
        return 1_000_000

    # 관측치가 200k를 초과하면 1M 모델임이 확실 (모델명 접미사 없어도)
    if observed_total > 200_000:
        return 1_000_000

    # 기본 컨텍스트 매핑 (대략)
    if "opus-4-7" in model or "opus-4-6" in model:
        return 200_000
    if "sonnet-4" in model:
        return 200_000
    if "haiku-4" in model:
        return 200_000
    return None


def find_latest_jsonl(sessions_dir: Path):
    """가장 최근 수정된 .jsonl 파일 반환. 없으면 None."""
    if not sessions_dir.exists() or not sessions_dir.is_dir():
        return None
    jsonls = list(sessions_dir.glob("*.jsonl"))
    if not jsonls:
        return None
    return max(jsonls, key=lambda p: p.stat().st_mtime)


def parse_jsonl_usage(jsonl_path: Path):
    """JSONL 파일 끝까지 읽어 마지막 assistant usage 정보 반환.

    Returns: (last_usage: dict | None, last_model: str | None, message_count: int)
    """
    last_usage = None
    last_model = None
    message_count = 0

    try:
        with open(jsonl_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue

                rec_type = rec.get("type")
                if rec_type in ("user", "assistant"):
                    message_count += 1

                if rec_type == "assistant":
                    msg = rec.get("message", {})
                    usage = msg.get("usage")
                    if usage:
                        last_usage = usage
                        last_model = msg.get("model") or last_model
    except (OSError, IOError):
        return None, None, 0

    return last_usage, last_model, message_count


def fallback(reason: str, **extra) -> dict:
    """Fallback 응답 — JSONL 파싱 실패 시."""
    response = {
        "ok": True,
        "method": "fallback_estimate",
        "fallback_reason": reason,
        "fallback_notice": "정확한 측정 불가 — JSONL 파싱 실패 또는 데이터 없음. 추정 모드.",
        "session_id": None,
        "session_file": None,
        "model": None,
        "context_limit": None,
        "tokens": None,
        "usage_percent": None,
        "near_limit": None,
        "message_count": None,
    }
    response.update(extra)
    return response


# ============================================================
# Main measurement
# ============================================================

def measure_context(project_root: Path) -> dict:
    """프로젝트 루트 기준 현재 세션의 컨텍스트 사용량 측정."""
    project_key = derive_project_key(project_root)
    sessions_dir = Path.home() / ".claude" / "projects" / project_key

    if not sessions_dir.exists():
        return fallback(
            f"세션 디렉토리 없음: {sessions_dir}",
            project_key=project_key,
            sessions_dir=str(sessions_dir),
        )

    latest = find_latest_jsonl(sessions_dir)
    if latest is None:
        return fallback(
            "JSONL 세션 파일 없음",
            project_key=project_key,
            sessions_dir=str(sessions_dir),
        )

    last_usage, last_model, message_count = parse_jsonl_usage(latest)

    if last_usage is None:
        return fallback(
            "JSONL에서 usage 정보 파싱 실패 (assistant 응답 없거나 형식 변경 가능성)",
            session_id=latest.stem,
            session_file=str(latest),
            message_count=message_count,
        )

    # 토큰 추출
    input_tokens = last_usage.get("input_tokens", 0) or 0
    cache_creation = last_usage.get("cache_creation_input_tokens", 0) or 0
    cache_read = last_usage.get("cache_read_input_tokens", 0) or 0
    output_tokens = last_usage.get("output_tokens", 0) or 0

    total_context = input_tokens + cache_creation + cache_read

    # 컨텍스트 한계 / 사용률 (관측치 기반 추정 가능)
    context_limit = get_context_limit(last_model, observed_total=total_context)
    usage_percent = (
        round(total_context / context_limit * 100, 1)
        if context_limit and context_limit > 0
        else None
    )
    near_limit = usage_percent is not None and usage_percent >= 80.0

    return {
        "ok": True,
        "method": "jsonl_parse",
        "session_id": latest.stem,
        "session_file": str(latest),
        "model": last_model,
        "context_limit": context_limit,
        "tokens": {
            "input": input_tokens,
            "cache_creation": cache_creation,
            "cache_read": cache_read,
            "total_context": total_context,
            "output_last_turn": output_tokens,
        },
        "usage_percent": usage_percent,
        "near_limit": near_limit,
        "message_count": message_count,
    }


# ============================================================
# CLI
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        prog="context_usage",
        description="Measure Claude Code session context / token usage",
    )
    parser.add_argument(
        "--project-root",
        default=None,
        help="프로젝트 루트 (기본: cwd)",
    )
    args = parser.parse_args()

    try:
        project_root = Path(args.project_root) if args.project_root else Path.cwd()
        project_root = project_root.resolve()
        result = measure_context(project_root)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        sys.exit(0)
    except Exception as e:
        print(json.dumps({
            "ok": False,
            "code": "internal_error",
            "message": f"내부 오류: {e}",
            "details": {"exception": type(e).__name__},
        }, ensure_ascii=False, indent=2))
        sys.exit(1)


if __name__ == "__main__":
    main()
