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

SCHEMA_VERSION = "1.1"


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


def compute_duration_seconds(started_at, ended_at) -> int:
    """ISO 8601 두 시각 차이(초). 정수. 음수 또는 파싱 실패 시 0."""
    if started_at is None or ended_at is None:
        return 0
    s = parse_iso(started_at)
    e = parse_iso(ended_at)
    if s is None or e is None:
        return 0
    delta = (e - s).total_seconds()
    if delta < 0:
        return 0
    return int(delta)


def format_duration(seconds: int) -> str:
    """초 → '12분 31초' / '1시간 5분 30초' 형식."""
    if seconds is None or seconds <= 0:
        return "0초"
    if seconds < 60:
        return f"{seconds}초"
    minutes, sec = divmod(seconds, 60)
    if minutes < 60:
        return f"{minutes}분 {sec}초"
    hours, mins = divmod(minutes, 60)
    return f"{hours}시간 {mins}분 {sec}초"


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


def aggregate_usage_in_range(jsonl_path: Path, since_iso: str,
                             until_iso: str = None) -> dict:
    """timestamp [since_iso, until_iso) 범위 내 assistant message.usage 합산.

    Returns:
        {
            "input": int, "output": int,
            "cache_creation": int, "cache_read": int,
            "message_count": int,
            "model": str | None,    # 단일이면 모델명, 둘 이상이면 "mixed", 0건이면 None
        }
    """
    since_dt = parse_iso(since_iso) if since_iso else None
    until_dt = parse_iso(until_iso) if until_iso else None

    totals = {
        "input": 0,
        "output": 0,
        "cache_creation": 0,
        "cache_read": 0,
        "message_count": 0,
        "model": None,
    }
    models_seen = set()

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
                if rec.get("type") != "assistant":
                    continue
                ts_str = rec.get("timestamp")
                if ts_str:
                    ts_dt = parse_iso(ts_str)
                    if ts_dt is not None:
                        if since_dt is not None and ts_dt < since_dt:
                            continue
                        if until_dt is not None and ts_dt >= until_dt:
                            continue
                msg = rec.get("message") or {}
                usage = msg.get("usage")
                if not usage:
                    continue
                totals["input"] += usage.get("input_tokens", 0) or 0
                totals["output"] += usage.get("output_tokens", 0) or 0
                totals["cache_creation"] += usage.get("cache_creation_input_tokens", 0) or 0
                totals["cache_read"] += usage.get("cache_read_input_tokens", 0) or 0
                totals["message_count"] += 1
                model = msg.get("model")
                if model:
                    models_seen.add(model)
    except (OSError, IOError):
        pass

    if len(models_seen) == 1:
        totals["model"] = next(iter(models_seen))
    elif len(models_seen) > 1:
        totals["model"] = "mixed"

    return totals


def recompute_session_summary(state: dict) -> dict:
    """state.phases 를 순회해 누적치 계산."""
    total_duration = 0
    total_input = 0
    total_output = 0
    total_cc = 0
    total_cr = 0
    completed = 0
    models_seen = set()

    phases = state.get("phases") or []
    for p in phases:
        ds = p.get("durationSeconds")
        if isinstance(ds, int) and ds > 0:
            total_duration += ds
        tk = p.get("tokens") or {}
        total_input += tk.get("input", 0) or 0
        total_output += tk.get("output", 0) or 0
        total_cc += tk.get("cacheCreation", 0) or 0
        total_cr += tk.get("cacheRead", 0) or 0
        if p.get("endedAt"):
            completed += 1
        m = tk.get("model")
        if m:
            models_seen.add(m)

    return {
        "totalDurationSeconds": total_duration,
        "totalTokens": {
            "input": total_input,
            "output": total_output,
            "cacheCreation": total_cc,
            "cacheRead": total_cr,
        },
        "phaseCount": len(phases),
        "completedPhases": completed,
        "models": sorted(models_seen),
    }


def _render_metadata_lines(metadata: dict) -> list:
    """CHAT_LOG.md 헤더에 들어갈 토큰/시간 메타데이터 라인."""
    if not metadata:
        return []
    lines = []
    duration = metadata.get("durationSeconds")
    if isinstance(duration, int):
        lines.append(f"- 작업 시간: {format_duration(duration)} ({duration}초)")
    tokens = metadata.get("tokens") or {}
    if tokens:
        model = tokens.get("model") or "unknown"
        partial = tokens.get("partial", False)
        partial_label = " (partial — 세션 변경 감지)" if partial else ""
        input_t = tokens.get("input", 0) or 0
        output_t = tokens.get("output", 0) or 0
        cc = tokens.get("cacheCreation", 0) or 0
        cr = tokens.get("cacheRead", 0) or 0
        denom = cr + cc + input_t
        hit_ratio = (cr / denom * 100) if denom > 0 else 0.0
        if isinstance(duration, int) and duration > 0:
            tpm = (input_t + output_t + cc) / (duration / 60)
        else:
            tpm = 0
        lines.append(f"- 토큰 사용량 (모델: {model}){partial_label}")
        lines.append(f"  - 입력: {input_t:,} / 출력: {output_t:,}")
        lines.append(f"  - 캐시 생성: {cc:,} / 캐시 읽기: {cr:,}")
        lines.append(f"  - 캐시 적중률: {hit_ratio:.1f}% / 분당 처리: {tpm:,.0f} tok/min")
    return lines


def write_chat_log(jsonl_path: Path, output_path: Path, since_iso: str,
                   topic: str, phase: int, metadata: dict = None) -> dict:
    """CHAT_LOG.md 생성. metadata 있으면 헤더에 토큰/시간 정보 포함."""
    messages = parse_jsonl_messages(jsonl_path, since_iso)

    output_path.parent.mkdir(parents=True, exist_ok=True)

    lines = []
    lines.append(f"# {topic} - Phase {phase:02d} CHAT_LOG")
    lines.append("")
    lines.append(f"- 세션 ID: `{jsonl_path.stem}`")
    lines.append(f"- Phase 시작: {since_iso or '(세션 시작)'}")
    lines.append(f"- 저장 시각: {now_iso()}")
    lines.append(f"- 메시지 수: {len(messages)}")
    lines.extend(_render_metadata_lines(metadata))
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
                "sessionId": session_id,
                "durationSeconds": None,
                "tokens": None,
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
    current_session_id = session_id_from_path(jsonl)
    state["sessionId"] = current_session_id

    # phase 시작 시점 sessionId 확정 (cmd_start 시 None 이었거나 legacy state 케이스)
    phase_obj = state["phases"][current_phase_idx]
    phase_session_id = phase_obj.get("sessionId")
    if phase_session_id is None:
        phase_obj["sessionId"] = current_session_id
        phase_session_id = current_session_id
    partial = phase_session_id != current_session_id

    # 토큰 / 작업 시간 측정
    phase_started_at = phase_obj["startedAt"]
    ended_at = now_iso()
    duration = compute_duration_seconds(phase_started_at, ended_at)
    usage = aggregate_usage_in_range(jsonl, phase_started_at, ended_at)

    tokens_dict = {
        "input": usage["input"],
        "output": usage["output"],
        "cacheCreation": usage["cache_creation"],
        "cacheRead": usage["cache_read"],
        "messageCount": usage["message_count"],
        "model": usage["model"],
    }
    if partial:
        tokens_dict["partial"] = True

    # CHAT_LOG.md 작성 (메타데이터 포함)
    phase_dir = cm_dir(project_root, user, topic) / f"Phase_{current_phase:02d}"
    chat_log_path = phase_dir / "CHAT_LOG.md"
    metadata = {"durationSeconds": duration, "tokens": tokens_dict}
    stats = write_chat_log(jsonl, chat_log_path, phase_started_at, topic,
                           current_phase, metadata=metadata)

    # state 업데이트
    phase_obj["endedAt"] = ended_at
    phase_obj["trigger"] = trigger
    rel_path = str(chat_log_path.relative_to(project_root)).replace("\\", "/")
    phase_obj["files"]["chatLog"] = rel_path
    phase_obj["durationSeconds"] = duration
    phase_obj["tokens"] = tokens_dict

    new_phase_started = None
    session_summary = None
    if end_session:
        state["active"] = False
        state["endedAt"] = ended_at
        session_summary = recompute_session_summary(state)
        state["sessionSummary"] = session_summary
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
            "sessionId": current_session_id,
            "durationSeconds": None,
            "tokens": None,
        })
        # 새 Phase 폴더 미리
        (cm_dir(project_root, user, topic) / f"Phase_{next_phase:02d}").mkdir(parents=True, exist_ok=True)

    write_state(project_root, user, topic, state)

    response_tokens = {
        "input": usage["input"],
        "output": usage["output"],
        "cache_creation": usage["cache_creation"],
        "cache_read": usage["cache_read"],
        "message_count": usage["message_count"],
        "model": usage["model"],
        "partial": partial,
    }

    denom = usage["cache_read"] + usage["cache_creation"] + usage["input"]
    cache_hit_ratio = round(usage["cache_read"] / denom * 100, 1) if denom > 0 else 0.0
    tpm = round((usage["input"] + usage["output"] + usage["cache_creation"]) / (duration / 60)) if duration > 0 else 0

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
        "duration_seconds": duration,
        "duration_human": format_duration(duration),
        "tokens": response_tokens,
        "cache_hit_ratio": cache_hit_ratio,
        "tokens_per_minute": tpm,
        "session_summary": session_summary,
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
# Subcommand: stats
# ============================================================

def scan_all_topics(project_root: Path) -> list:
    """.hs/*/CM/*/CM_STATE.json 전부 스캔.

    Returns: list of (user, topic, state_dict). 손상/누락 silent skip.
    """
    cm_root = project_root / ".hs"
    results = []
    if not cm_root.exists() or not cm_root.is_dir():
        return results
    for user_dir in cm_root.iterdir():
        if not user_dir.is_dir():
            continue
        cm_subdir = user_dir / "CM"
        if not cm_subdir.exists() or not cm_subdir.is_dir():
            continue
        for topic_dir in cm_subdir.iterdir():
            if not topic_dir.is_dir():
                continue
            state_path = topic_dir / "CM_STATE.json"
            if not state_path.exists():
                continue
            try:
                with open(state_path, "r", encoding="utf-8") as f:
                    state = json.load(f)
                results.append((user_dir.name, topic_dir.name, state))
            except (json.JSONDecodeError, OSError):
                continue
    return results


def topic_summary(user: str, topic: str, state: dict) -> dict:
    """토픽 1개 정규화. sessionSummary 우선, 미존재 시 recompute."""
    summary = state.get("sessionSummary")
    if summary is None:
        summary = recompute_session_summary(state)

    phases_raw = state.get("phases") or []
    legacy_count = 0
    phase_records = []
    for p in phases_raw:
        tk = p.get("tokens")
        if tk is None:
            legacy_count += 1
            tk = {"input": 0, "output": 0, "cacheCreation": 0, "cacheRead": 0,
                  "messageCount": 0, "model": None}
        phase_records.append({
            "phase": p.get("phase"),
            "started_at": p.get("startedAt"),
            "ended_at": p.get("endedAt"),
            "duration_seconds": p.get("durationSeconds") or 0,
            "tokens": {
                "input": tk.get("input", 0) or 0,
                "output": tk.get("output", 0) or 0,
                "cacheCreation": tk.get("cacheCreation", 0) or 0,
                "cacheRead": tk.get("cacheRead", 0) or 0,
            },
        })

    return {
        "user": user,
        "topic": topic,
        "active": state.get("active", False),
        "started_at": state.get("startedAt"),
        "ended_at": state.get("endedAt"),
        "phase_count": summary.get("phaseCount", 0),
        "completed_phases": summary.get("completedPhases", 0),
        "duration_seconds": summary.get("totalDurationSeconds", 0),
        "tokens": summary.get("totalTokens", {
            "input": 0, "output": 0, "cacheCreation": 0, "cacheRead": 0
        }),
        "models": summary.get("models", []),
        "legacy_phases": legacy_count,
        "phases": phase_records,
    }


def _date_part(iso_str):
    """ISO timestamp → 'YYYY-MM-DD' 부분. 실패 시 None."""
    if not iso_str:
        return None
    dt = parse_iso(iso_str)
    if dt is None:
        return None
    return dt.strftime("%Y-%m-%d")


def apply_filters(topics: list, *, user=None, topic_pattern=None,
                  since=None, until=None,
                  active_only=False, ended_only=False) -> list:
    """필터 적용. since/until 은 topic.started_at 일자 기준."""
    out = []
    for t in topics:
        if user and t["user"] != user:
            continue
        if topic_pattern and topic_pattern not in t["topic"]:
            continue
        started_date = _date_part(t["started_at"])
        if since:
            if started_date is None or started_date < since:
                continue
        if until:
            if started_date is None or started_date > until:
                continue
        if active_only and not t["active"]:
            continue
        if ended_only and t["active"]:
            continue
        out.append(t)
    return out


def _billed_tokens(tokens: dict) -> int:
    """청구 토큰 합 (input + output + cacheCreation). cacheRead 별도."""
    return (tokens.get("input", 0) or 0) + (tokens.get("output", 0) or 0) + (tokens.get("cacheCreation", 0) or 0)


def aggregate_per_user(topics: list) -> list:
    """사용자별 합산."""
    by_user = {}
    for t in topics:
        u = t["user"]
        if u not in by_user:
            by_user[u] = {
                "user": u,
                "topic_count": 0,
                "phase_count": 0,
                "completed_phases": 0,
                "duration_seconds": 0,
                "tokens": {"input": 0, "output": 0, "cacheCreation": 0, "cacheRead": 0},
                "models": set(),
                "legacy_phases": 0,
            }
        agg = by_user[u]
        agg["topic_count"] += 1
        agg["phase_count"] += t["phase_count"]
        agg["completed_phases"] += t["completed_phases"]
        agg["duration_seconds"] += t["duration_seconds"]
        for k in ("input", "output", "cacheCreation", "cacheRead"):
            agg["tokens"][k] += t["tokens"].get(k, 0) or 0
        for m in t["models"]:
            agg["models"].add(m)
        agg["legacy_phases"] += t["legacy_phases"]
    out = []
    for u in sorted(by_user.keys()):
        v = by_user[u]
        v["models"] = sorted(v["models"])
        out.append(v)
    return out


def aggregate_grand_total(topics: list) -> dict:
    """전체 합산."""
    users = set()
    phase_count = 0
    completed_phases = 0
    duration = 0
    tokens = {"input": 0, "output": 0, "cacheCreation": 0, "cacheRead": 0}
    models = set()
    legacy_count = 0
    for t in topics:
        users.add(t["user"])
        phase_count += t["phase_count"]
        completed_phases += t["completed_phases"]
        duration += t["duration_seconds"]
        for k in ("input", "output", "cacheCreation", "cacheRead"):
            tokens[k] += t["tokens"].get(k, 0) or 0
        for m in t["models"]:
            models.add(m)
        legacy_count += t["legacy_phases"]
    return {
        "user_count": len(users),
        "topic_count": len(topics),
        "phase_count": phase_count,
        "completed_phases": completed_phases,
        "duration_seconds": duration,
        "tokens": tokens,
        "models": sorted(models),
        "legacy_phases": legacy_count,
    }


def sort_topics(topics: list, sort_by: str) -> list:
    """sort_by: tokens / duration / phases / started / user."""
    keys = {
        "tokens": lambda t: -_billed_tokens(t["tokens"]),
        "duration": lambda t: -t["duration_seconds"],
        "phases": lambda t: -t["phase_count"],
        "started": lambda t: t["started_at"] or "",
        "user": lambda t: (t["user"], t["topic"]),
    }
    return sorted(topics, key=keys.get(sort_by, keys["tokens"]))


def daily_token_series(topics: list) -> list:
    """phase.startedAt 일자별로 청구 토큰(input+output+cacheCreation) binning.

    Returns: sorted list of {"date": "YYYY-MM-DD", "billed": int, "cache_read": int}
    """
    by_date = {}
    for t in topics:
        for p in t["phases"]:
            d = _date_part(p["started_at"])
            if d is None:
                continue
            if d not in by_date:
                by_date[d] = {"billed": 0, "cache_read": 0}
            by_date[d]["billed"] += _billed_tokens(p["tokens"])
            by_date[d]["cache_read"] += p["tokens"].get("cacheRead", 0) or 0
    return [{"date": d, **by_date[d]} for d in sorted(by_date.keys())]


# ============================================================
# Mermaid chart renderers
# ============================================================

def _escape_mermaid_label(s) -> str:
    """Mermaid 라벨 안전화."""
    return str(s).replace('"', "'").replace("\n", " ")


def mermaid_pie(title: str, items: list) -> str:
    """items: [(label, value), ...]. value <= 0 인 항목은 스킵."""
    items = [(l, v) for l, v in items if v and v > 0]
    if not items:
        return ""
    lines = ["```mermaid", f"pie showData title {_escape_mermaid_label(title)}"]
    for label, value in items:
        lines.append(f'    "{_escape_mermaid_label(label)}" : {int(value)}')
    lines.append("```")
    return "\n".join(lines)


def mermaid_xy_bar(title: str, x_axis: list, y_label: str, values: list) -> str:
    """xychart-beta bar."""
    if not x_axis or not values:
        return ""
    x_str = "[" + ", ".join(f'"{_escape_mermaid_label(x)}"' for x in x_axis) + "]"
    v_str = "[" + ", ".join(str(int(v)) for v in values) + "]"
    return "\n".join([
        "```mermaid",
        "xychart-beta",
        f'    title "{_escape_mermaid_label(title)}"',
        f"    x-axis {x_str}",
        f'    y-axis "{_escape_mermaid_label(y_label)}"',
        f"    bar {v_str}",
        "```",
    ])


def mermaid_xy_line(title: str, x_axis: list, y_label: str, values: list) -> str:
    """xychart-beta line."""
    if not x_axis or not values:
        return ""
    x_str = "[" + ", ".join(f'"{_escape_mermaid_label(x)}"' for x in x_axis) + "]"
    v_str = "[" + ", ".join(str(int(v)) for v in values) + "]"
    return "\n".join([
        "```mermaid",
        "xychart-beta",
        f'    title "{_escape_mermaid_label(title)}"',
        f"    x-axis {x_str}",
        f'    y-axis "{_escape_mermaid_label(y_label)}"',
        f"    line {v_str}",
        "```",
    ])


# ============================================================
# Markdown report builder
# ============================================================

DEFAULT_CHARTS = ["users-pie", "topics-bar", "daily-line", "models-pie"]
ALL_CHARTS = list(DEFAULT_CHARTS)


def _resolve_charts(charts_arg: str) -> list:
    """--charts 인자 파싱."""
    if charts_arg in (None, "", "all"):
        return list(DEFAULT_CHARTS)
    if charts_arg == "none":
        return []
    requested = [c.strip() for c in charts_arg.split(",") if c.strip()]
    return [c for c in requested if c in ALL_CHARTS]


def build_report_markdown(scope: dict, topics: list, users: list,
                          grand_total: dict, charts: list,
                          generated_at: str) -> str:
    """완성된 마크다운 (Mermaid 포함)."""
    lines = []
    lines.append(f"# CL 사용량 리포트 ({generated_at} UTC)")
    lines.append("")

    # 적용 필터
    f = scope.get("filters", {})
    lines.append("## 적용 필터")
    lines.append(f"- 기간: {f.get('since') or '전체'} ~ {f.get('until') or '현재'}")
    lines.append(f"- 사용자: {f.get('user') or '전체'}")
    lines.append(f"- 토픽 패턴: {f.get('topic') or '전체'}")
    lines.append(f"- 활성/종료: " + (
        "활성만" if f.get("active_only") else
        "종료만" if f.get("ended_only") else "전체"
    ))
    lines.append(f"- 그룹: {scope.get('by')} / 정렬: {scope.get('sort')}"
                 + (f" / Top {scope.get('top')}" if scope.get('top') else ""))
    lines.append("")

    # 전체 합계
    gt = grand_total
    gt_tk = gt["tokens"]
    gt_billed = _billed_tokens(gt_tk)
    gt_denom = gt_billed + gt_tk["cacheRead"]
    gt_hit = (gt_tk["cacheRead"] / gt_denom * 100) if gt_denom > 0 else 0.0
    lines.append("## 전체 합계")
    lines.append(f"- 사용자 {gt['user_count']}명 / 토픽 {gt['topic_count']}개 / "
                 f"Phase {gt['phase_count']}개 (완료 {gt['completed_phases']})")
    lines.append(f"- 총 작업 시간: {format_duration(gt['duration_seconds'])} "
                 f"({gt['duration_seconds']:,}초)")
    lines.append(f"- 청구 토큰 합 (input+output+cacheCreation): {gt_billed:,}")
    lines.append(f"  - 입력: {gt_tk['input']:,} / 출력: {gt_tk['output']:,} "
                 f"/ 캐시 생성: {gt_tk['cacheCreation']:,}")
    lines.append(f"- 캐시 읽기: {gt_tk['cacheRead']:,} (1/10 단가)")
    lines.append(f"- 평균 캐시 적중률: {gt_hit:.1f}%")
    lines.append(f"- 사용 모델: {', '.join(gt['models']) if gt['models'] else '(없음)'}")
    if gt.get("legacy_phases", 0) > 0:
        lines.append(f"- ⚠️ Legacy phase {gt['legacy_phases']}개 (토큰 데이터 없음, 0으로 합산)")
    lines.append("")

    # 사용자별 토큰 점유 (pie)
    if "users-pie" in charts and len(users) > 0:
        lines.append("## 사용자별 청구 토큰 점유")
        items = [(u["user"], _billed_tokens(u["tokens"])) for u in users]
        chart = mermaid_pie("Users (billed tokens)", items)
        if chart:
            lines.append(chart)
        lines.append("")
        lines.append("| 사용자 | 토픽 | Phase | 작업시간 | 청구 토큰 | 캐시 읽기 |")
        lines.append("|--------|------|-------|----------|-----------|-----------|")
        for u in users:
            billed = _billed_tokens(u["tokens"])
            lines.append(f"| {u['user']} | {u['topic_count']} | {u['phase_count']} | "
                         f"{format_duration(u['duration_seconds'])} | "
                         f"{billed:,} | {u['tokens']['cacheRead']:,} |")
        lines.append("")

    # 토픽별 청구 토큰 Top N (bar)
    if "topics-bar" in charts and len(topics) > 0:
        top_n = min(10, len(topics))
        top_topics = sorted(topics, key=lambda t: -_billed_tokens(t["tokens"]))[:top_n]
        lines.append(f"## 토픽별 청구 토큰 Top {top_n}")
        x = [t["topic"] for t in top_topics]
        v = [_billed_tokens(t["tokens"]) for t in top_topics]
        chart = mermaid_xy_bar("Topics by billed tokens", x, "tokens", v)
        if chart:
            lines.append(chart)
        lines.append("")

    # 일자별 토큰 추이 (line)
    if "daily-line" in charts:
        series = daily_token_series(topics)
        if series:
            lines.append("## 일자별 청구 토큰 추이")
            chart = mermaid_xy_line(
                "Daily billed tokens",
                [s["date"] for s in series],
                "tokens",
                [s["billed"] for s in series],
            )
            if chart:
                lines.append(chart)
            lines.append("")

    # 모델별 점유 (pie)
    if "models-pie" in charts and len(topics) > 0:
        per_model = {}
        for t in topics:
            models = t["models"] or ["unknown"]
            billed = _billed_tokens(t["tokens"])
            share = billed / len(models) if models else 0
            for m in models:
                per_model[m] = per_model.get(m, 0) + share
        items = [(m, int(v)) for m, v in per_model.items()]
        if items:
            lines.append("## 모델별 청구 토큰 점유 (토픽 모델 균등 분배)")
            chart = mermaid_pie("Models", items)
            if chart:
                lines.append(chart)
            lines.append("")

    # 토픽별 상세 표
    lines.append("## 토픽별 상세")
    lines.append("| 토픽 | 사용자 | 상태 | Phase | 시간 | 입력 | 출력 | 캐시생성 | 캐시읽기 | 적중률 | 모델 |")
    lines.append("|------|--------|------|-------|------|------|------|----------|----------|--------|------|")
    for t in topics:
        tk = t["tokens"]
        billed = _billed_tokens(tk)
        denom = billed + tk["cacheRead"]
        hit = (tk["cacheRead"] / denom * 100) if denom > 0 else 0.0
        status = "활성" if t["active"] else "종료"
        models = ", ".join(t["models"]) if t["models"] else "-"
        lines.append(f"| {t['topic']} | {t['user']} | {status} | "
                     f"{t['completed_phases']}/{t['phase_count']} | "
                     f"{format_duration(t['duration_seconds'])} | "
                     f"{tk['input']:,} | {tk['output']:,} | "
                     f"{tk['cacheCreation']:,} | {tk['cacheRead']:,} | "
                     f"{hit:.1f}% | {models} |")
    lines.append("")
    lines.append("---")
    lines.append(f"*리포트 생성: {generated_at} UTC by cm_state.py stats*")
    lines.append("")

    return "\n".join(lines)


def _maybe_register_obsidian_junction(project_root: Path, subfolder: str,
                                      name_suffix: str) -> None:
    """OBSIDIAN_VAULT 환경변수 + Windows + register_vault.ps1 모두 갖춰지면 junction 등록 시도.

    부가 기능. 실패는 silent — stats 본 동작에 영향 없음.
    """
    if os.environ.get("OBSIDIAN_VAULT") is None:
        return
    if sys.platform != "win32":
        return
    register_script = Path.home() / ".claude" / "register_vault.ps1"
    if not register_script.exists():
        return
    try:
        subprocess.run(
            [
                "powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
                "-File", str(register_script),
                "-ProjectRoot", str(project_root),
                "-Subfolder", subfolder,
                "-NameSuffix", name_suffix,
            ],
            check=False,
            capture_output=True,
            timeout=15,
        )
    except (subprocess.SubprocessError, OSError, FileNotFoundError):
        pass


def cmd_stats(args):
    """stats 서브커맨드 진입점."""
    project_root = Path.cwd()

    # 1. 스캔
    raw = scan_all_topics(project_root)
    topics_all = [topic_summary(u, t, s) for (u, t, s) in raw]

    # 2. 필터
    topics = apply_filters(
        topics_all,
        user=args.user,
        topic_pattern=args.topic,
        since=args.since,
        until=args.until,
        active_only=args.active_only,
        ended_only=args.ended_only,
    )

    # 3. 정렬
    sort_by = args.sort or "tokens"
    topics_sorted = sort_topics(topics, sort_by)

    # 4. Top N
    if args.top is not None and args.top > 0:
        topics_sorted = topics_sorted[:args.top]

    # 5. 집계
    users = aggregate_per_user(topics_sorted)
    grand_total = aggregate_grand_total(topics_sorted)

    scope = {
        "filters": {
            "user": args.user,
            "topic": args.topic,
            "since": args.since,
            "until": args.until,
            "active_only": args.active_only,
            "ended_only": args.ended_only,
        },
        "by": args.by or "topic",
        "sort": sort_by,
        "top": args.top,
    }

    # 6. 응답 토픽 (phases 큼 — 응답에서 제거, daily 계산만 사용 후)
    response_topics = []
    for t in topics_sorted:
        copy = {k: v for k, v in t.items() if k != "phases"}
        response_topics.append(copy)

    response = {
        "ok": True,
        "scope": scope,
        "topics": response_topics,
        "users": users,
        "grand_total": grand_total,
        "report": None,
    }

    # 7. 리포트 (옵션)
    if args.report is not None:
        charts = _resolve_charts(args.charts)
        # 생성 시각
        generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        # 경로 결정
        if args.report == "<auto>" or not args.report:
            user_info = detect_user(project_root)
            stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H%M%S")
            report_path = (project_root / "cl-reports" / user_info["user"] /
                           f"CL_USAGE_{stamp}.md")
        else:
            report_path = Path(args.report)
            if not report_path.is_absolute():
                report_path = project_root / report_path

        md = build_report_markdown(scope, topics_sorted, users, grand_total,
                                   charts, generated_at)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        with open(report_path, "w", encoding="utf-8", newline="\n") as f:
            f.write(md)

        # Obsidian junction 자동 등록 시도 (silent fail)
        _maybe_register_obsidian_junction(project_root, "cl-reports", "-cl")

        try:
            rel = str(report_path.relative_to(project_root)).replace("\\", "/")
        except ValueError:
            rel = str(report_path)

        response["report"] = {
            "written": True,
            "path": rel,
            "absolute_path": str(report_path),
            "size_bytes": report_path.stat().st_size,
            "charts_included": charts,
            "generated_at": generated_at,
        }

    emit(ok({k: v for k, v in response.items() if k != "ok"}))


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

    p = subs.add_parser("stats", help="누적 사용량 집계 + 옵션 마크다운 리포트")
    p.add_argument("--user", help="특정 사용자 한정 (생략 시 전체)")
    p.add_argument("--topic", help="토픽 이름 부분 일치 패턴")
    p.add_argument("--since", help="시작 일자 YYYY-MM-DD (topic.startedAt 기준)")
    p.add_argument("--until", help="종료 일자 YYYY-MM-DD (topic.startedAt 기준)")
    p.add_argument("--by", choices=["topic", "user", "user-topic"], default="topic")
    p.add_argument("--sort", choices=["tokens", "duration", "phases", "started", "user"],
                   default="tokens")
    p.add_argument("--top", type=int, default=None)
    p.add_argument("--active-only", action="store_true", dest="active_only")
    p.add_argument("--ended-only", action="store_true", dest="ended_only")
    p.add_argument("--report", nargs="?", const="<auto>", default=None,
                   help="마크다운 리포트 생성. 경로 생략 시 cl-reports/<user>/")
    p.add_argument("--charts", default="all",
                   help="포함 차트: users-pie,topics-bar,daily-line,models-pie,all,none")
    p.set_defaults(fn=cmd_stats)

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
