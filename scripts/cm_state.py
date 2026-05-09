#!/usr/bin/env python3
"""
cm_state.py — CM (Chat Log) 세션 상태 관리 + JSONL → CHAT_LOG.md 변환.

저장 위치:
    .hs/{user}/CM/{topic}/CM_STATE.json
    .hs/{user}/CM/{topic}/Phase_NN/CHAT_LOG.md

사용자 추출 우선순위:
    1) git config user.name (프로젝트가 git이면)
    2) OS 사용자 (USERNAME / USER 환경변수)

서브커맨드:
    start <topic>    — 세션 시작
    save             — 현재 Phase 저장 (CHAT_LOG.md) + Phase 증가
    end              — 마지막 Phase 저장 + active=false
    status [topic]   — 활성 세션 또는 특정 토픽 정보
    list             — 현재 사용자 모든 CM 세션 목록
    detect-user      — git/OS 사용자 추출 결과 반환

응답: JSON to stdout. ok=True/False + 추가 필드.
"""

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

# Force UTF-8 stdio
if hasattr(sys.stdin, "reconfigure"):
    sys.stdin.reconfigure(encoding="utf-8")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

# Add scripts/ to path for _user import
sys.path.insert(0, str(Path(__file__).parent))
from _user import detect_user as _detect_user, sanitize_user as _sanitize_user

SCHEMA_VERSION = "1.0"


# ============================================================
# Common helpers
# ============================================================

def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_iso(s):
    if not s:
        return None
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(s)
    except ValueError:
        return None


def emit(response: dict, exit_code=None) -> None:
    print(json.dumps(response, ensure_ascii=False, indent=2))
    if exit_code is None:
        exit_code = 0 if response.get("ok") else 2
    sys.exit(exit_code)


def ok(payload: dict) -> dict:
    return {"ok": True, **payload}


def err(code: str, message: str, details=None) -> dict:
    return {"ok": False, "code": code, "message": message, "details": details or {}}


# ============================================================
# User detection (from _user module)
# ============================================================

# Re-export for backward compatibility within this module
detect_user = _detect_user
sanitize_user = _sanitize_user


# ============================================================
# Path / state helpers
# ============================================================

def cm_dir(project_root: Path, user: str, topic: str) -> Path:
    """{project}/.hs/{user}/CM/{topic}/"""
    return project_root / ".hs" / user / "CM" / topic


def cm_state_path(project_root: Path, user: str, topic: str) -> Path:
    return cm_dir(project_root, user, topic) / "CM_STATE.json"


def user_cm_root(project_root: Path, user: str) -> Path:
    return project_root / ".hs" / user / "CM"


def list_topics(project_root: Path, user: str) -> list:
    """현재 사용자의 모든 CM 토픽 폴더."""
    root = user_cm_root(project_root, user)
    if not root.exists():
        return []
    return sorted([
        d.name for d in root.iterdir()
        if d.is_dir() and (d / "CM_STATE.json").exists()
    ])


def find_active_topic(project_root: Path, user: str):
    """현재 사용자에서 active=true인 토픽 찾기. 없으면 None."""
    for topic in list_topics(project_root, user):
        state = read_state(project_root, user, topic)
        if state and state.get("active") is True:
            return topic
    return None


def read_state(project_root: Path, user: str, topic: str):
    path = cm_state_path(project_root, user, topic)
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def write_state(project_root: Path, user: str, topic: str, state: dict) -> None:
    """Atomic write."""
    path = cm_state_path(project_root, user, topic)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    tmp.replace(path)


# ============================================================
# JSONL session helpers
# ============================================================

def derive_project_key(project_path: Path) -> str:
    """경로 구분자(\\, /, :)를 각각 -로 치환."""
    return re.sub(r"[\\/:]", "-", str(project_path).rstrip("\\/"))


def find_latest_session(project_root: Path):
    """현재 프로젝트의 최신 JSONL 파일 반환. 없으면 None."""
    project_key = derive_project_key(project_root)
    sessions_dir = Path.home() / ".claude" / "projects" / project_key
    if not sessions_dir.exists():
        return None
    jsonls = list(sessions_dir.glob("*.jsonl"))
    if not jsonls:
        return None
    return max(jsonls, key=lambda p: p.stat().st_mtime)


def session_id_from_path(jsonl_path: Path) -> str:
    return jsonl_path.stem


# ============================================================
# JSONL → CHAT_LOG.md conversion
# ============================================================

def render_text_block(content) -> str:
    """JSONL message content를 마크다운 텍스트로 렌더."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if not isinstance(block, dict):
                parts.append(str(block))
                continue
            btype = block.get("type")
            if btype == "text":
                parts.append(block.get("text", ""))
            elif btype == "tool_use":
                tool_name = block.get("name", "?")
                tool_input = block.get("input", {})
                input_str = json.dumps(tool_input, ensure_ascii=False, indent=2)
                if len(input_str) > 500:
                    input_str = input_str[:500] + "\n... (생략)"
                parts.append(f"\n**[Tool: {tool_name}]**\n```json\n{input_str}\n```")
            elif btype == "tool_result":
                result = block.get("content", "")
                if isinstance(result, list):
                    result = render_text_block(result)
                result_str = str(result)
                if len(result_str) > 800:
                    result_str = result_str[:800] + "\n... (생략)"
                parts.append(f"\n**[Tool Result]**\n```\n{result_str}\n```")
            elif btype == "thinking":
                # Skip extended thinking for chat log brevity
                continue
            else:
                parts.append(f"[{btype}]")
        return "\n".join(p for p in parts if p)
    return str(content)


def parse_jsonl_messages(jsonl_path: Path, since_iso: str = None):
    """JSONL 파일에서 메시지 추출. since_iso 있으면 그 시각 이후만.

    Returns: list of (timestamp, role, rendered_content)
    """
    since_dt = parse_iso(since_iso) if since_iso else None
    messages = []

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
                if rec_type not in ("user", "assistant"):
                    continue

                # Timestamp filter
                ts_str = rec.get("timestamp")
                if since_dt and ts_str:
                    ts_dt = parse_iso(ts_str)
                    if ts_dt and ts_dt < since_dt:
                        continue

                msg = rec.get("message", {})
                content = msg.get("content", "")
                rendered = render_text_block(content)
                if rendered.strip():
                    messages.append((ts_str, rec_type, rendered))
    except (OSError, IOError):
        return []

    return messages


def write_chat_log(jsonl_path: Path, output_path: Path, since_iso: str,
                   topic: str, phase: int) -> dict:
    """CHAT_LOG.md 생성. Returns stats."""
    messages = parse_jsonl_messages(jsonl_path, since_iso)

    output_path.parent.mkdir(parents=True, exist_ok=True)

    lines = []
    lines.append(f"# {topic} - Phase {phase:02d} CHAT_LOG")
    lines.append("")
    lines.append(f"- 세션 ID: `{jsonl_path.stem}`")
    lines.append(f"- Phase 시작: {since_iso or '(세션 시작)'}")
    lines.append(f"- 저장 시각: {now_iso()}")
    lines.append(f"- 메시지 수: {len(messages)}")
    lines.append("")
    lines.append("---")
    lines.append("")

    for idx, (ts, role, content) in enumerate(messages, 1):
        role_label = "User" if role == "user" else "Assistant"
        ts_label = f" ({ts})" if ts else ""
        lines.append(f"## {idx}. {role_label}{ts_label}")
        lines.append("")
        lines.append(content)
        lines.append("")
        lines.append("---")
        lines.append("")

    with open(output_path, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines))

    return {
        "messages_written": len(messages),
        "file_size_bytes": output_path.stat().st_size,
    }


# ============================================================
# Subcommand: detect-user
# ============================================================

def cmd_detect_user(args):
    project_root = Path.cwd()
    info = detect_user(project_root)
    emit(ok({
        "user": info["user"],
        "source": info["source"],
        "raw": info["raw"],
        "project_root": str(project_root),
    }))


# ============================================================
# Subcommand: start
# ============================================================

def cmd_start(args):
    project_root = Path.cwd()
    topic_raw = args.topic
    topic = sanitize_user(topic_raw)  # 같은 sanitize 룰 적용

    if not topic:
        emit(err("invalid_input", "topic 비어있거나 무효함."))

    user_info = detect_user(project_root)
    user = user_info["user"]

    # 상호 배타 검사
    active = find_active_topic(project_root, user)
    if active and active != topic:
        emit(err("another_session_active",
                 f"이미 활성 CM 세션 있음: '{active}'. 먼저 /hs:cl-end로 종료.",
                 {"active_topic": active, "user": user}))

    # 기존 토픽 재시작 처리
    existing = read_state(project_root, user, topic)
    if existing:
        if existing.get("active"):
            emit(err("already_active",
                     f"토픽 '{topic}' 이미 활성. 추가 동작 불필요.",
                     {"topic": topic, "phase": existing.get("phase")}))
        # 비활성 상태면 새 phase 시작
        emit(err("topic_exists_inactive",
                 f"토픽 '{topic}' 이미 등록됨 (비활성). 같은 이름 재사용 시 데이터 보존을 위해 별도 처리 필요.",
                 {"topic": topic,
                  "existing_phases": len(existing.get("phases", [])),
                  "hint": "다른 토픽명 사용 또는 .hs/{user}/CM/{topic}/ 수동 정리 후 재시도"}))

    # 세션 ID 추출
    jsonl = find_latest_session(project_root)
    session_id = session_id_from_path(jsonl) if jsonl else None

    started_at = now_iso()
    state = {
        "version": SCHEMA_VERSION,
        "active": True,
        "topic": topic,
        "user": user,
        "user_source": user_info["source"],
        "phase": 1,
        "sessionId": session_id,
        "projectPath": str(project_root),
        "outputDir": str(cm_dir(project_root, user, topic).relative_to(project_root)).replace("\\", "/"),
        "startedAt": started_at,
        "phases": [
            {
                "phase": 1,
                "startedAt": started_at,
                "endedAt": None,
                "trigger": None,
                "files": {"chatLog": None},
            }
        ],
    }
    write_state(project_root, user, topic, state)

    # Phase_01 폴더 미리 생성
    (cm_dir(project_root, user, topic) / "Phase_01").mkdir(parents=True, exist_ok=True)

    emit(ok({
        "started": True,
        "topic": topic,
        "topic_raw": topic_raw,
        "user": user,
        "user_source": user_info["source"],
        "phase": 1,
        "session_id": session_id,
        "session_id_warning": None if session_id else "세션 JSONL 미발견 — save 시 다시 검출",
        "output_dir": state["outputDir"],
    }))


# ============================================================
# Subcommand: save
# ============================================================

def _do_save(project_root: Path, user: str, topic: str,
             trigger: str, end_session: bool):
    """save / end 공통 로직.

    1) 현재 phase 저장 (CHAT_LOG.md 생성)
    2) state 업데이트 (endedAt, files, trigger)
    3) end_session=False면 새 phase 시작, True면 active=false
    """
    state = read_state(project_root, user, topic)
    if state is None:
        return err("topic_not_found", f"토픽 '{topic}' 없음.", {"user": user, "topic": topic})
    if not state.get("active"):
        return err("session_inactive",
                   f"토픽 '{topic}' 비활성 상태. 먼저 /hs:cl-start로 시작.",
                   {"topic": topic})

    current_phase = state["phase"]
    current_phase_idx = next(
        (i for i, p in enumerate(state["phases"]) if p["phase"] == current_phase),
        None
    )
    if current_phase_idx is None:
        return err("state_corrupt",
                   f"현재 Phase {current_phase}가 phases 배열에 없음.",
                   {"topic": topic})

    # JSONL 찾기
    jsonl = find_latest_session(project_root)
    if jsonl is None:
        return err("session_not_found",
                   "세션 JSONL 파일 없음 — Claude Code 세션 디렉토리 확인 필요.",
                   {"project_root": str(project_root)})

    # session_id 갱신 (start 시 못 찾았을 수 있음)
    state["sessionId"] = session_id_from_path(jsonl)

    # CHAT_LOG.md 작성
    phase_started_at = state["phases"][current_phase_idx]["startedAt"]
    phase_dir = cm_dir(project_root, user, topic) / f"Phase_{current_phase:02d}"
    chat_log_path = phase_dir / "CHAT_LOG.md"
    stats = write_chat_log(jsonl, chat_log_path, phase_started_at, topic, current_phase)

    ended_at = now_iso()
    state["phases"][current_phase_idx]["endedAt"] = ended_at
    state["phases"][current_phase_idx]["trigger"] = trigger
    rel_path = str(chat_log_path.relative_to(project_root)).replace("\\", "/")
    state["phases"][current_phase_idx]["files"]["chatLog"] = rel_path

    new_phase_started = None
    if end_session:
        state["active"] = False
        state["endedAt"] = ended_at
    else:
        # 다음 Phase 자동 시작
        next_phase = current_phase + 1
        new_phase_started = ended_at
        state["phase"] = next_phase
        state["phases"].append({
            "phase": next_phase,
            "startedAt": new_phase_started,
            "endedAt": None,
            "trigger": None,
            "files": {"chatLog": None},
        })
        # 새 Phase 폴더 미리
        (cm_dir(project_root, user, topic) / f"Phase_{next_phase:02d}").mkdir(parents=True, exist_ok=True)

    write_state(project_root, user, topic, state)

    return ok({
        "saved_phase": current_phase,
        "topic": topic,
        "user": user,
        "chat_log_path": rel_path,
        "messages_written": stats["messages_written"],
        "file_size_bytes": stats["file_size_bytes"],
        "session_id": state["sessionId"],
        "trigger": trigger,
        "ended_at": ended_at,
        "session_active": state["active"],
        "next_phase": state["phase"] if not end_session else None,
        "next_phase_started_at": new_phase_started,
    })


def cmd_save(args):
    project_root = Path.cwd()
    user_info = detect_user(project_root)
    user = user_info["user"]

    topic = args.topic
    if topic is None:
        topic = find_active_topic(project_root, user)
        if topic is None:
            emit(err("no_active_session",
                     f"사용자 '{user}'에게 활성 CM 세션 없음.",
                     {"user": user}))

    response = _do_save(project_root, user, topic, trigger="manual", end_session=False)
    emit(response)


# ============================================================
# Subcommand: end
# ============================================================

def cmd_end(args):
    project_root = Path.cwd()
    user_info = detect_user(project_root)
    user = user_info["user"]

    topic = args.topic
    if topic is None:
        topic = find_active_topic(project_root, user)
        if topic is None:
            emit(err("no_active_session",
                     f"사용자 '{user}'에게 활성 CM 세션 없음.",
                     {"user": user}))

    response = _do_save(project_root, user, topic, trigger="manual_end", end_session=True)
    emit(response)


# ============================================================
# Subcommand: status
# ============================================================

def cmd_status(args):
    project_root = Path.cwd()
    user_info = detect_user(project_root)
    user = user_info["user"]

    topic = args.topic
    if topic is None:
        topic = find_active_topic(project_root, user)
        if topic is None:
            emit(ok({
                "active": False,
                "user": user,
                "user_source": user_info["source"],
                "message": "활성 CM 세션 없음.",
                "topics": list_topics(project_root, user),
            }))

    state = read_state(project_root, user, topic)
    if state is None:
        emit(err("topic_not_found", f"토픽 '{topic}' 없음.",
                 {"user": user, "topic": topic}))

    phases_info = [
        {
            "phase": p["phase"],
            "startedAt": p.get("startedAt"),
            "endedAt": p.get("endedAt"),
            "trigger": p.get("trigger"),
            "chat_log": p.get("files", {}).get("chatLog"),
        }
        for p in state.get("phases", [])
    ]

    emit(ok({
        "topic": topic,
        "user": user,
        "active": state.get("active", False),
        "current_phase": state.get("phase"),
        "session_id": state.get("sessionId"),
        "started_at": state.get("startedAt"),
        "ended_at": state.get("endedAt"),
        "output_dir": state.get("outputDir"),
        "phases": phases_info,
        "phase_count": len(phases_info),
    }))


# ============================================================
# Subcommand: list
# ============================================================

def cmd_list(args):
    project_root = Path.cwd()
    user_info = detect_user(project_root)
    user = user_info["user"]

    topics = list_topics(project_root, user)
    items = []
    for t in topics:
        state = read_state(project_root, user, t)
        if state is None:
            continue
        items.append({
            "topic": t,
            "active": state.get("active", False),
            "phase_count": len(state.get("phases", [])),
            "current_phase": state.get("phase"),
            "started_at": state.get("startedAt"),
            "ended_at": state.get("endedAt"),
        })

    emit(ok({
        "user": user,
        "user_source": user_info["source"],
        "topics": items,
        "active_topic": find_active_topic(project_root, user),
    }))


# ============================================================
# CLI
# ============================================================

def build_parser():
    parser = argparse.ArgumentParser(prog="cm_state", description="CM session state CLI")
    subs = parser.add_subparsers(dest="command", required=True)

    p = subs.add_parser("detect-user")
    p.set_defaults(fn=cmd_detect_user)

    p = subs.add_parser("start")
    p.add_argument("topic")
    p.set_defaults(fn=cmd_start)

    p = subs.add_parser("save")
    p.add_argument("topic", nargs="?", default=None)
    p.set_defaults(fn=cmd_save)

    p = subs.add_parser("end")
    p.add_argument("topic", nargs="?", default=None)
    p.set_defaults(fn=cmd_end)

    p = subs.add_parser("status")
    p.add_argument("topic", nargs="?", default=None)
    p.set_defaults(fn=cmd_status)

    p = subs.add_parser("list")
    p.set_defaults(fn=cmd_list)

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()
    try:
        args.fn(args)
    except SystemExit:
        raise
    except Exception as e:
        emit(err("internal_error",
                 f"내부 오류: {e}",
                 {"exception": type(e).__name__}),
             exit_code=1)


if __name__ == "__main__":
    main()
