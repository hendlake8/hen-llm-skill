#!/usr/bin/env python3
"""
plan_state.py — Plan state management for /hs:plan-* skills.

Single-file CLI with subcommands. JSON to stdout. Exit codes:
    0 success
    1 internal error
    2 validation error (recoverable; check error.code)
    3 yaml corruption
    4 missing dependency / fs error

State files (relative to current working directory):
    .hs/state.yaml                     — global state (current_plan)
    .hs/PlanTask/{name}/progress.yaml  — per-plan state

See SKILL.md files for usage from each /hs:plan-* skill.
"""

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

# Force UTF-8 for stdin/stdout regardless of platform default (Windows cp949 etc.)
if hasattr(sys.stdin, "reconfigure"):
    sys.stdin.reconfigure(encoding="utf-8")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

try:
    import yaml
except ImportError:
    print(json.dumps({
        "ok": False,
        "code": "missing_dependency",
        "message": "PyYAML이 설치되어 있지 않습니다. 'pip install pyyaml' 실행 후 재시도.",
        "details": {"package": "pyyaml"},
    }, ensure_ascii=False))
    sys.exit(4)


# Add scripts/ to path for _user import
sys.path.insert(0, str(Path(__file__).parent))
from _user import detect_user

# ============================================================
# Constants
# ============================================================

# 경로 구조: .hs/{user}/PlanTask/state.yaml + .hs/{user}/PlanTask/{plan}/progress.yaml
SCHEMA_VERSION = "1.0"

ROLLBACKABLE_STATUSES = {"completed", "in_progress", "paused"}
AUTO_RUN_STALE_HOURS = 24
PHASE_ID_PATTERN = re.compile(r"^Phase\s+(\d+)-(\d+)$")


# ============================================================
# Generic helpers
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


def is_stale(started_at_iso, hours=AUTO_RUN_STALE_HOURS):
    dt = parse_iso(started_at_iso)
    if dt is None:
        return bool(started_at_iso)  # unparseable but present → treat as stale
    return datetime.now(timezone.utc) - dt > timedelta(hours=hours)


def file_hash(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return f"sha256:{h.hexdigest()}"


def atomic_write_yaml(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        yaml.safe_dump(
            data, f,
            allow_unicode=True,
            sort_keys=False,
            default_flow_style=False,
        )
    tmp.replace(path)


def read_yaml(path: Path):
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    except yaml.YAMLError as e:
        emit(err("state_yaml_corrupt", f"yaml 파싱 실패: {path}", {"error": str(e)}), exit_code=3)


# ============================================================
# Path helpers (user-aware)
# ============================================================

_USER_INFO_CACHE = None


def _get_user_info():
    """현재 cwd 기준 user 정보 (1회 캐시)."""
    global _USER_INFO_CACHE
    if _USER_INFO_CACHE is None:
        _USER_INFO_CACHE = detect_user(Path.cwd())
    return _USER_INFO_CACHE


def get_plan_task_dir() -> Path:
    """.hs/{user}/PlanTask/ 반환."""
    return Path(".hs") / _get_user_info()["user"] / "PlanTask"


def get_state_file() -> Path:
    """.hs/{user}/PlanTask/state.yaml 반환."""
    return get_plan_task_dir() / "state.yaml"


# ============================================================
# State accessors
# ============================================================

def read_global_state() -> dict:
    data = read_yaml(get_state_file())
    if data is None:
        return {"version": SCHEMA_VERSION, "current_plan": None, "updated_at": None}
    return data


def write_global_state(state: dict) -> None:
    state["version"] = SCHEMA_VERSION
    state["updated_at"] = now_iso()
    atomic_write_yaml(get_state_file(), state)


def get_progress_path(plan_name: str) -> Path:
    return get_plan_task_dir() / plan_name / "progress.yaml"


def list_plan_names() -> list:
    plan_task_dir = get_plan_task_dir()
    if not plan_task_dir.exists():
        return []
    return sorted([
        e.name for e in plan_task_dir.iterdir()
        if e.is_dir() and (e / "progress.yaml").exists()
    ])


def read_plan(name: str):
    return read_yaml(get_progress_path(name))


def write_plan(name: str, data: dict) -> None:
    atomic_write_yaml(get_progress_path(name), data)


def resolve_plan(plan_arg) -> str:
    """Determine target plan: explicit arg → current_plan → only-plan fallback."""
    if plan_arg:
        return plan_arg
    state = read_global_state()
    if state.get("current_plan"):
        return state["current_plan"]
    plans = list_plan_names()
    if len(plans) == 1:
        return plans[0]
    return None


# ============================================================
# Response helpers
# ============================================================

def ok(payload: dict) -> dict:
    return {"ok": True, **payload}


def err(code: str, message: str, details=None) -> dict:
    return {"ok": False, "code": code, "message": message, "details": details or {}}


def emit(response: dict, exit_code=None) -> None:
    print(json.dumps(response, ensure_ascii=False, indent=2))
    if exit_code is None:
        exit_code = 0 if response.get("ok") else 2
    sys.exit(exit_code)


# ============================================================
# Phase / dependency utilities
# ============================================================

def find_phase(plan: dict, phase_id: str):
    for p in plan.get("phases", []):
        if p["id"] == phase_id:
            return p
    return None


def get_in_progress_phase(plan: dict):
    for p in plan.get("phases", []):
        if p["status"] == "in_progress":
            return p
    return None


def deps_complete(plan: dict, phase: dict):
    """Return (all_complete: bool, blocking: list)."""
    blocking = []
    for dep_id in phase.get("depends_on", []):
        dep = find_phase(plan, dep_id)
        if dep is None or dep["status"] != "completed":
            tasks_remaining = (
                sum(1 for t in dep.get("tasks", []) if t["status"] != "completed")
                if dep else 0
            )
            blocking.append({
                "id": dep_id,
                "status": dep["status"] if dep else "missing",
                "tasks_remaining": tasks_remaining,
            })
    return (len(blocking) == 0, blocking)


def progress_summary(plan: dict) -> dict:
    phases = plan.get("phases", [])
    total = len(phases)
    counts = {"completed": 0, "in_progress": 0, "pending": 0, "paused": 0, "blocked": 0}
    for p in phases:
        counts[p["status"]] = counts.get(p["status"], 0) + 1
    percent = round(counts["completed"] / total * 100, 1) if total else 0
    return {"total": total, **counts, "percent": percent}


def add_history(plan: dict, action: str, details=None) -> None:
    plan.setdefault("history", []).append({
        "action": action,
        "date": now_iso(),
        "details": details or {},
    })


def update_plan_status(plan: dict) -> None:
    """Recompute plan_status from phase states."""
    phases = plan.get("phases", [])
    if not phases:
        plan["plan_status"] = "pending"
        return
    statuses = {p["status"] for p in phases}
    was_completed = plan.get("plan_status") == "completed"
    if statuses == {"completed"}:
        plan["plan_status"] = "completed"
        if not was_completed:
            plan["completed_at"] = now_iso()
    elif {"in_progress", "paused", "completed"} & statuses:
        plan["plan_status"] = "in_progress"
        if was_completed:
            plan["completed_at"] = None
    else:
        plan["plan_status"] = "pending"
        if was_completed:
            plan["completed_at"] = None


def release_dependents(plan: dict, completed_phase_id: str) -> list:
    """Move blocked phases to pending if all their deps now complete."""
    changes = []
    for p in plan.get("phases", []):
        if completed_phase_id in p.get("depends_on", []) and p["status"] == "blocked":
            ok_deps, _ = deps_complete(plan, p)
            if ok_deps:
                changes.append({
                    "id": p["id"],
                    "status_before": "blocked",
                    "status_after": "pending",
                })
                p["status"] = "pending"
    return changes


def compute_cascade(plan: dict, phase_id: str) -> list:
    """Compute which downstream phases would be blocked by rolling back phase_id."""
    cascade = []
    visited = set()
    queue = [phase_id]
    while queue:
        current = queue.pop(0)
        if current in visited:
            continue
        visited.add(current)
        for p in plan.get("phases", []):
            if current in p.get("depends_on", []) and p["id"] not in visited:
                if p["status"] in ("in_progress", "completed", "pending", "paused"):
                    cascade.append({
                        "id": p["id"],
                        "status_before": p["status"],
                        "status_after": "blocked",
                    })
                queue.append(p["id"])
    return cascade


# ============================================================
# Subcommand: register (load helper)
# ============================================================

def cmd_register(args):
    try:
        data = json.loads(sys.stdin.read())
    except json.JSONDecodeError as e:
        emit(err("invalid_input", f"stdin JSON 파싱 실패: {e}"))

    name = data.get("name")
    if not name:
        emit(err("invalid_input", "'name' 필드 필수."))

    source_path = Path(args.source)
    if not source_path.exists():
        emit(err("source_file_not_found", f"source 파일 없음: {args.source}",
                 {"source": args.source}))

    progress_path = get_progress_path(name)
    if progress_path.exists():
        emit(err("plan_already_exists",
                 f"plan '{name}' 이미 등록됨. plan-redesign 또는 plan-unload 후 재등록.",
                 {"name": name}))

    phases = data.get("phases", [])
    for p in phases:
        p.setdefault("status", "pending")
        p.setdefault("depends_on", [])
        p.setdefault("started_at", None)
        p.setdefault("completed_at", None)
        p.setdefault("paused_at", None)
        for t in p.get("tasks", []):
            t.setdefault("status", "pending")

    # Auto-derive depends_on from Phase X-Y pattern when not specified
    for p in phases:
        if p["depends_on"]:
            continue
        m = PHASE_ID_PATTERN.match(p["id"])
        if not m:
            continue
        x, y = int(m.group(1)), int(m.group(2))
        if y > 1:
            prev_id = f"Phase {x}-{y-1}"
            if any(pp["id"] == prev_id for pp in phases):
                p["depends_on"].append(prev_id)
        elif x > 1:
            prev_group = []
            for pp in phases:
                pm = PHASE_ID_PATTERN.match(pp["id"])
                if pm and int(pm.group(1)) == x - 1:
                    prev_group.append(pp["id"])
            p["depends_on"].extend(prev_group)

    plan_data = {
        "version": SCHEMA_VERSION,
        "name": name,
        "plan_status": "pending",
        "source": str(args.source),
        "source_hash": file_hash(source_path),
        "registered_at": now_iso(),
        "completed_at": None,
        "revision": 1,
        "auto_run": {"active": False, "started_at": None, "current_phase": None},
        "phases": phases,
        "history": [{
            "action": "plan_registered",
            "date": now_iso(),
            "details": {"source": str(args.source), "phase_count": len(phases)},
        }],
    }
    write_plan(name, plan_data)

    state = read_global_state()
    state["current_plan"] = name
    write_global_state(state)

    emit(ok({
        "registered": name,
        "phases": len(phases),
        "tasks": sum(len(p.get("tasks", [])) for p in phases),
        "current_plan_set": True,
    }))


# ============================================================
# Subcommand: list
# ============================================================

def cmd_list(args):
    state = read_global_state()
    plans_info = []
    for name in list_plan_names():
        plan = read_plan(name)
        if plan is None:
            continue
        plans_info.append({
            "name": name,
            "plan_status": plan.get("plan_status", "pending"),
            "source": plan.get("source"),
            "registered_at": plan.get("registered_at"),
            "completed_at": plan.get("completed_at"),
            "is_current": name == state.get("current_plan"),
            "progress": progress_summary(plan),
            "auto_run_active": plan.get("auto_run", {}).get("active", False),
        })
    emit(ok({"current_plan": state.get("current_plan"), "plans": plans_info}))


# ============================================================
# Subcommand: unload
# ============================================================

def cmd_unload(args):
    name = args.plan_name
    plan = read_plan(name)
    if plan is None:
        emit(err("plan_not_found", f"plan '{name}' 없음.", {"name": name}))

    in_progress = get_in_progress_phase(plan)
    if in_progress and not args.force:
        emit(err("plan_in_progress",
                 f"plan '{name}'에 진행 중인 Phase 있음. --force로 강제 삭제 가능.",
                 {"name": name, "in_progress_phase": in_progress["id"]}))

    phase_count = len(plan.get("phases", []))
    task_count = sum(len(p.get("tasks", [])) for p in plan.get("phases", []))
    history_count = len(plan.get("history", []))

    shutil.rmtree(get_plan_task_dir() / name)

    state = read_global_state()
    was_current = state.get("current_plan") == name
    new_current = None
    if was_current:
        remaining = list_plan_names()
        new_current = remaining[0] if remaining else None
        state["current_plan"] = new_current
        write_global_state(state)

    emit(ok({
        "removed": name,
        "was_current": was_current,
        "new_current_plan": new_current,
        "phases_removed": phase_count,
        "tasks_removed": task_count,
        "history_entries_removed": history_count,
    }))


# ============================================================
# Subcommand: start
# ============================================================

def cmd_start(args):
    plan_name = resolve_plan(args.plan)
    if not plan_name:
        emit(err("plan_not_found", "활성 plan 없음. plan-load 먼저 실행."))

    plan = read_plan(plan_name)
    if plan is None:
        emit(err("plan_not_found", f"plan '{plan_name}' 없음.", {"name": plan_name}))

    if plan.get("plan_status") == "completed":
        emit(err("plan_already_completed",
                 f"plan '{plan_name}' 이미 완료. plan-redesign / plan-unload 권장.",
                 {"name": plan_name}))

    phase = find_phase(plan, args.phase_id)
    if phase is None:
        emit(err("phase_not_found", f"Phase '{args.phase_id}' 없음.",
                 {"phase_id": args.phase_id,
                  "available": [p["id"] for p in plan.get("phases", [])]}))

    if phase["status"] == "in_progress":
        emit(err("phase_status_invalid",
                 f"Phase '{args.phase_id}' 이미 진행 중.",
                 {"phase_id": args.phase_id, "current_status": "in_progress"}))
    if phase["status"] == "completed":
        emit(err("phase_status_invalid",
                 f"Phase '{args.phase_id}' 이미 완료됨.",
                 {"phase_id": args.phase_id, "current_status": "completed"}))
    if phase["status"] not in ("pending", "paused"):
        emit(err("phase_status_invalid",
                 f"Phase '{args.phase_id}' status '{phase['status']}'에서 시작 불가.",
                 {"phase_id": args.phase_id, "current_status": phase["status"]}))

    other_in_progress = get_in_progress_phase(plan)
    if other_in_progress and other_in_progress["id"] != args.phase_id:
        emit(err("another_phase_in_progress",
                 f"다른 Phase 진행 중: {other_in_progress['id']}. plan-pause 또는 plan-complete 후 시작.",
                 {"in_progress_phase": other_in_progress["id"]}))

    if phase["status"] == "pending":
        deps_ok, blocking = deps_complete(plan, phase)
        if not deps_ok:
            emit(err("dependencies_not_met",
                     f"선행 Phase 미완료: {[b['id'] for b in blocking]}",
                     {"phase_id": args.phase_id, "blocking": blocking}))

    was_paused = phase["status"] == "paused"
    phase["status"] = "in_progress"
    if not was_paused:
        phase["started_at"] = now_iso()
    phase["paused_at"] = None

    update_plan_status(plan)
    add_history(plan, "phase_started",
                {"phase_id": args.phase_id, "resumed_from_pause": was_paused})
    write_plan(plan_name, plan)

    emit(ok({
        "plan": plan_name,
        "phase_id": args.phase_id,
        "phase_name": phase.get("name"),
        "status": "in_progress",
        "started_at": phase["started_at"],
        "resumed_from_pause": was_paused,
        "tasks": [
            {"index": i + 1, "name": t["name"], "status": t["status"]}
            for i, t in enumerate(phase.get("tasks", []))
        ],
    }))


# ============================================================
# Subcommand: pause
# ============================================================

def cmd_pause(args):
    plan_name = resolve_plan(args.plan)
    if not plan_name:
        emit(err("plan_not_found", "활성 plan 없음."))

    plan = read_plan(plan_name)
    if plan is None:
        emit(err("plan_not_found", f"plan '{plan_name}' 없음.", {"name": plan_name}))

    auto_run = plan.setdefault("auto_run", {"active": False})
    auto_run_was_active = auto_run.get("active", False)

    if args.phase_id:
        phase = find_phase(plan, args.phase_id)
        if phase is None:
            emit(err("phase_not_found", f"Phase '{args.phase_id}' 없음.",
                     {"phase_id": args.phase_id}))
    else:
        phase = get_in_progress_phase(plan)
        # Allow stopping auto_run even when no phase is currently in_progress
        if phase is None and not auto_run_was_active:
            emit(err("no_phase_in_progress",
                     "진행 중인 Phase 없음 (auto-run도 비활성)."))

    paused_phase_id = None
    if phase is not None:
        if phase["status"] != "in_progress":
            emit(err("phase_status_invalid",
                     f"Phase '{phase['id']}' status '{phase['status']}'에서 일시정지 불가.",
                     {"phase_id": phase["id"], "current_status": phase["status"]}))
        phase["status"] = "paused"
        phase["paused_at"] = now_iso()
        paused_phase_id = phase["id"]

    if auto_run_was_active:
        auto_run["active"] = False
        auto_run["current_phase"] = None

    update_plan_status(plan)
    add_history(plan, "phase_paused", {
        "phase_id": paused_phase_id,
        "auto_run_stopped": auto_run_was_active,
    })
    write_plan(plan_name, plan)

    summary = None
    if phase is not None:
        tasks = phase.get("tasks", [])
        summary = {
            "completed": sum(1 for t in tasks if t["status"] == "completed"),
            "pending": sum(1 for t in tasks if t["status"] != "completed"),
            "total": len(tasks),
        }

    emit(ok({
        "plan": plan_name,
        "phase_id": paused_phase_id,
        "phase_name": phase.get("name") if phase else None,
        "status": "paused" if phase else None,
        "paused_at": phase["paused_at"] if phase else None,
        "tasks_summary": summary,
        "auto_run_was_active": auto_run_was_active,
    }))


# ============================================================
# Subcommand: complete
# ============================================================

def cmd_complete(args):
    plan_name = resolve_plan(args.plan)
    if not plan_name:
        emit(err("plan_not_found", "활성 plan 없음."))

    plan = read_plan(plan_name)
    if plan is None:
        emit(err("plan_not_found", f"plan '{plan_name}' 없음.", {"name": plan_name}))

    phase = find_phase(plan, args.phase_id)
    if phase is None:
        emit(err("phase_not_found", f"Phase '{args.phase_id}' 없음.",
                 {"phase_id": args.phase_id}))

    if phase["status"] not in ("in_progress", "paused"):
        emit(err("phase_status_invalid",
                 f"Phase '{args.phase_id}' status '{phase['status']}'에서 완료 불가.",
                 {"phase_id": args.phase_id, "current_status": phase["status"]}))

    for t in phase.get("tasks", []):
        t["status"] = "completed"
    phase["status"] = "completed"
    phase["completed_at"] = now_iso()
    phase["paused_at"] = None

    released = release_dependents(plan, args.phase_id)

    was_complete_status = plan.get("plan_status") == "completed"
    update_plan_status(plan)
    is_plan_completed_now = (
        plan.get("plan_status") == "completed" and not was_complete_status
    )

    if is_plan_completed_now:
        auto_run = plan.setdefault("auto_run", {})
        if auto_run.get("active"):
            auto_run["active"] = False
            auto_run["current_phase"] = None
        add_history(plan, "plan_completed", {
            "phase_count": len(plan.get("phases", [])),
            "task_count": sum(len(p.get("tasks", [])) for p in plan.get("phases", [])),
        })

    add_history(plan, "phase_completed", {
        "phase_id": args.phase_id,
        "released": [r["id"] for r in released],
    })
    write_plan(plan_name, plan)

    next_suggested = None
    for p in plan.get("phases", []):
        if p["status"] == "pending":
            ok_deps, _ = deps_complete(plan, p)
            if ok_deps:
                next_suggested = p["id"]
                break

    emit(ok({
        "plan": plan_name,
        "phase_id": args.phase_id,
        "phase_name": phase.get("name"),
        "status": "completed",
        "completed_at": phase["completed_at"],
        "released_phases": released,
        "plan_status": plan.get("plan_status"),
        "is_plan_completed": is_plan_completed_now,
        "progress": progress_summary(plan),
        "next_suggested": next_suggested,
    }))


# ============================================================
# Subcommand: rollback
# ============================================================

def cmd_rollback(args):
    plan_name = resolve_plan(args.plan)
    if not plan_name:
        emit(err("plan_not_found", "활성 plan 없음."))

    plan = read_plan(plan_name)
    if plan is None:
        emit(err("plan_not_found", f"plan '{plan_name}' 없음.", {"name": plan_name}))

    phase = find_phase(plan, args.phase_id)
    if phase is None:
        emit(err("phase_not_found", f"Phase '{args.phase_id}' 없음.",
                 {"phase_id": args.phase_id}))

    if phase["status"] not in ROLLBACKABLE_STATUSES:
        emit(err("phase_status_invalid",
                 f"Phase '{args.phase_id}' status '{phase['status']}'에서 롤백 불가.",
                 {"phase_id": args.phase_id, "current_status": phase["status"]}))

    target_status = args.to
    cascade = compute_cascade(plan, args.phase_id)

    if cascade and not args.confirm_cascade:
        print(json.dumps({
            "ok": True,
            "preview": True,
            "phase_id": args.phase_id,
            "current_status": phase["status"],
            "target_status": target_status,
            "cascade_impact": cascade,
            "requires_confirm": True,
            "message": "연쇄 영향 있음. --confirm-cascade로 재실행하면 적용.",
        }, ensure_ascii=False, indent=2))
        sys.exit(0)

    old_status = phase["status"]
    phase["status"] = target_status
    if target_status == "pending":
        phase["started_at"] = None
        phase["completed_at"] = None
        phase["paused_at"] = None
        for t in phase.get("tasks", []):
            t["status"] = "pending"

    for change in cascade:
        cp = find_phase(plan, change["id"])
        if cp:
            cp["status"] = "blocked"

    update_plan_status(plan)

    auto_run = plan.setdefault("auto_run", {})
    if auto_run.get("active"):
        auto_run["active"] = False
        auto_run["current_phase"] = None

    add_history(plan, "phase_rollback", {
        "phase_id": args.phase_id,
        "from_status": old_status,
        "to_status": target_status,
        "cascade": [c["id"] for c in cascade],
    })
    write_plan(plan_name, plan)

    emit(ok({
        "preview": False,
        "plan": plan_name,
        "phase_id": args.phase_id,
        "status_before": old_status,
        "status_after": target_status,
        "cascaded_phases": cascade,
        "plan_status": plan.get("plan_status"),
    }))


# ============================================================
# Subcommand: tasks
# ============================================================

def cmd_tasks(args):
    plan_name = resolve_plan(args.plan)
    if not plan_name:
        emit(err("plan_not_found", "활성 plan 없음."))

    plan = read_plan(plan_name)
    if plan is None:
        emit(err("plan_not_found", f"plan '{plan_name}' 없음.", {"name": plan_name}))

    phase = find_phase(plan, args.phase_id)
    if phase is None:
        emit(err("phase_not_found", f"Phase '{args.phase_id}' 없음.",
                 {"phase_id": args.phase_id}))

    tasks = phase.get("tasks", [])
    total = len(tasks)

    if args.complete is not None:
        idx = args.complete
        if idx < 1 or idx > total:
            emit(err("task_index_invalid",
                     f"태스크 인덱스 '{idx}' 무효. 범위: 1~{total}.",
                     {"index": idx, "valid_range": [1, total]}))
        target = tasks[idx - 1]
        if target["status"] == "completed":
            emit(err("phase_status_invalid",
                     f"태스크 [{idx}] 이미 완료됨.",
                     {"index": idx, "name": target["name"]}))
        target["status"] = "completed"
        add_history(plan, "task_completed", {
            "phase_id": args.phase_id,
            "task_index": idx,
            "task_name": target["name"],
        })
        write_plan(plan_name, plan)

        completed = sum(1 for t in tasks if t["status"] == "completed")
        emit(ok({
            "plan": plan_name,
            "phase_id": args.phase_id,
            "completed_task": {"index": idx, "name": target["name"]},
            "progress": {
                "completed": completed,
                "total": total,
                "percent": round(completed / total * 100, 1) if total else 0,
            },
            "phase_complete_ready": completed == total,
        }))

    completed = sum(1 for t in tasks if t["status"] == "completed")
    emit(ok({
        "plan": plan_name,
        "phase_id": args.phase_id,
        "phase_status": phase["status"],
        "tasks": [
            {"index": i + 1, "name": t["name"], "status": t["status"]}
            for i, t in enumerate(tasks)
        ],
        "progress": {
            "completed": completed,
            "total": total,
            "percent": round(completed / total * 100, 1) if total else 0,
        },
    }))


# ============================================================
# Subcommand: status
# ============================================================

def cmd_status(args):
    plan_name = resolve_plan(args.plan)
    if not plan_name:
        emit(err("plan_not_found", "활성 plan 없음. plan-load 먼저 실행."))

    plan = read_plan(plan_name)
    if plan is None:
        emit(err("plan_not_found", f"plan '{plan_name}' 없음.", {"name": plan_name}))

    progress = progress_summary(plan)
    current = get_in_progress_phase(plan)

    next_suggested = None
    if not current:
        for p in plan.get("phases", []):
            if p["status"] == "pending":
                ok_deps, _ = deps_complete(plan, p)
                if ok_deps:
                    next_suggested = p["id"]
                    break

    phases_info = []
    for p in plan.get("phases", []):
        tasks = p.get("tasks", [])
        info = {
            "id": p["id"],
            "name": p.get("name"),
            "status": p["status"],
            "depends_on": p.get("depends_on", []),
            "started_at": p.get("started_at"),
            "completed_at": p.get("completed_at"),
            "paused_at": p.get("paused_at"),
            "tasks_summary": {
                "completed": sum(1 for t in tasks if t["status"] == "completed"),
                "total": len(tasks),
            },
        }
        if args.detail:
            info["tasks"] = [
                {"index": i + 1, "name": t["name"], "status": t["status"]}
                for i, t in enumerate(tasks)
            ]
        phases_info.append(info)

    emit(ok({
        "plan": plan_name,
        "plan_status": plan.get("plan_status"),
        "progress": progress,
        "phases": phases_info,
        "current_phase": ({
            "id": current["id"],
            "name": current.get("name"),
            "tasks_remaining": sum(
                1 for t in current.get("tasks", []) if t["status"] != "completed"
            ),
        } if current else None),
        "next_suggested": next_suggested,
        "auto_run": {
            "active": plan.get("auto_run", {}).get("active", False),
            "started_at": plan.get("auto_run", {}).get("started_at"),
            "current_phase": plan.get("auto_run", {}).get("current_phase"),
        },
    }))


# ============================================================
# Subcommand: check-source
# ============================================================

def cmd_check_source(args):
    plan_name = resolve_plan(args.plan)
    if not plan_name:
        emit(err("plan_not_found", "활성 plan 없음."))

    plan = read_plan(plan_name)
    if plan is None:
        emit(err("plan_not_found", f"plan '{plan_name}' 없음.", {"name": plan_name}))

    source = plan.get("source")
    if not source:
        emit(err("source_file_not_found", "source 정보 없음."))

    source_path = Path(source)
    if not source_path.exists():
        emit(err("source_file_not_found", f"source 파일 없음: {source}",
                 {"source": source}))

    stored_hash = plan.get("source_hash")
    current_hash = file_hash(source_path)
    emit(ok({
        "plan": plan_name,
        "source": source,
        "stored_hash": stored_hash,
        "current_hash": current_hash,
        "changed": stored_hash != current_hash,
    }))


# ============================================================
# Subcommand: apply-redesign
# ============================================================

def cmd_apply_redesign(args):
    plan_name = resolve_plan(args.plan)
    if not plan_name:
        emit(err("plan_not_found", "활성 plan 없음."))

    plan = read_plan(plan_name)
    if plan is None:
        emit(err("plan_not_found", f"plan '{plan_name}' 없음.", {"name": plan_name}))

    try:
        merged = json.loads(sys.stdin.read())
    except json.JSONDecodeError as e:
        emit(err("invalid_input", f"stdin JSON 파싱 실패: {e}"))

    if not isinstance(merged.get("phases"), list):
        emit(err("invalid_input", "merged data에 'phases' 리스트 필요."))

    plan["phases"] = merged["phases"]
    plan["revision"] = plan.get("revision", 1) + 1

    source_path = Path(plan["source"])
    if source_path.exists():
        plan["source_hash"] = file_hash(source_path)

    update_plan_status(plan)
    add_history(plan, "plan_redesigned", {
        "revision": plan["revision"],
        "phase_count": len(merged["phases"]),
    })
    write_plan(plan_name, plan)

    emit(ok({
        "plan": plan_name,
        "revision": plan["revision"],
        "phase_count": len(merged["phases"]),
        "plan_status": plan.get("plan_status"),
    }))


# ============================================================
# Subcommand: impact
# ============================================================

def cmd_impact(args):
    plan_name = resolve_plan(args.plan)
    if not plan_name:
        emit(err("plan_not_found", "활성 plan 없음."))

    plan = read_plan(plan_name)
    if plan is None:
        emit(err("plan_not_found", f"plan '{plan_name}' 없음.", {"name": plan_name}))

    phase = find_phase(plan, args.phase_id)
    if phase is None:
        emit(err("phase_not_found", f"Phase '{args.phase_id}' 없음.",
                 {"phase_id": args.phase_id}))

    upstream = phase.get("depends_on", [])
    direct = [p["id"] for p in plan.get("phases", [])
              if args.phase_id in p.get("depends_on", [])]

    visited = set(direct)
    queue = list(direct)
    while queue:
        current = queue.pop(0)
        for p in plan.get("phases", []):
            if current in p.get("depends_on", []) and p["id"] not in visited:
                visited.add(p["id"])
                queue.append(p["id"])
    indirect = sorted(visited - set(direct))

    response = {
        "plan": plan_name,
        "phase_id": args.phase_id,
        "phase_name": phase.get("name"),
        "current_status": phase["status"],
        "dependencies": {
            "upstream": upstream,
            "downstream_direct": direct,
            "downstream_indirect": indirect,
        },
        "critical_path": bool(direct or indirect),
    }

    if args.action == "complete":
        progress_before = progress_summary(plan)
        simulated_releases = []
        for p in plan.get("phases", []):
            if args.phase_id in p.get("depends_on", []) and p["status"] == "blocked":
                other_deps_met = all(
                    (find_phase(plan, d) and find_phase(plan, d)["status"] == "completed")
                    for d in p["depends_on"] if d != args.phase_id
                )
                if other_deps_met:
                    simulated_releases.append(p["id"])
        added = 0 if phase["status"] == "completed" else 1
        completed_after = progress_before["completed"] + added
        response["simulation"] = {
            "action": "complete",
            "released_phases": simulated_releases,
            "progress_before": progress_before,
            "progress_after_estimate": {
                "completed": completed_after,
                "total": progress_before["total"],
                "percent": round(completed_after / progress_before["total"] * 100, 1)
                           if progress_before["total"] else 0,
            },
        }
    elif args.action == "rollback":
        cascade = compute_cascade(plan, args.phase_id)
        response["simulation"] = {
            "action": "rollback",
            "would_block": [c["id"] for c in cascade],
            "rework_count": len(cascade),
        }
    elif args.action == "delete":
        response["simulation"] = {
            "action": "delete",
            "phases_orphaned": direct + indirect,
            "tasks_lost": len(phase.get("tasks", [])),
            "warning": "삭제 후 의존성 재조정 필요. plan-redesign 권장.",
        }

    emit(ok(response))


# ============================================================
# Subcommand: auto-run-start
# ============================================================

def cmd_auto_run_start(args):
    plan_name = resolve_plan(args.plan)
    if not plan_name:
        emit(err("plan_not_found", "활성 plan 없음."))

    plan = read_plan(plan_name)
    if plan is None:
        emit(err("plan_not_found", f"plan '{plan_name}' 없음.", {"name": plan_name}))

    if plan.get("plan_status") == "completed":
        emit(err("plan_already_completed",
                 f"plan '{plan_name}' 이미 완료. plan-redesign / plan-unload 권장.",
                 {"name": plan_name}))

    auto_run = plan.setdefault("auto_run", {"active": False})
    stale_cleaned = False
    if auto_run.get("active"):
        if is_stale(auto_run.get("started_at")):
            stale_cleaned = True
        else:
            emit(err("auto_run_already_active",
                     f"이미 자동 실행 중 (시작: {auto_run.get('started_at')}). plan-pause 후 재시도.",
                     {"started_at": auto_run.get("started_at"),
                      "current_phase": auto_run.get("current_phase")}))

    first_phase = None
    in_progress = get_in_progress_phase(plan)
    if in_progress:
        first_phase = in_progress["id"]
    else:
        for p in plan.get("phases", []):
            if p["status"] == "pending":
                ok_deps, _ = deps_complete(plan, p)
                if ok_deps:
                    first_phase = p["id"]
                    break

    if not first_phase:
        emit(err("no_runnable_phase",
                 "실행 가능한 Phase 없음. plan-status로 확인.", {}))

    auto_run["active"] = True
    auto_run["started_at"] = now_iso()
    auto_run["current_phase"] = first_phase

    add_history(plan, "auto_run_started",
                {"first_phase": first_phase, "stale_cleaned": stale_cleaned})
    write_plan(plan_name, plan)

    remaining = sum(
        1 for p in plan.get("phases", [])
        if p["status"] in ("pending", "in_progress", "paused", "blocked")
    )

    emit(ok({
        "plan": plan_name,
        "auto_run_started": True,
        "stale_cleaned": stale_cleaned,
        "first_phase": first_phase,
        "phases_remaining": remaining,
    }))


# ============================================================
# Subcommand: auto-run-stop
# ============================================================

def cmd_auto_run_stop(args):
    plan_name = resolve_plan(args.plan)
    if not plan_name:
        emit(err("plan_not_found", "활성 plan 없음."))

    plan = read_plan(plan_name)
    if plan is None:
        emit(err("plan_not_found", f"plan '{plan_name}' 없음.", {"name": plan_name}))

    auto_run = plan.setdefault("auto_run", {"active": False})
    was_active = auto_run.get("active", False)
    auto_run["active"] = False
    auto_run["current_phase"] = None

    add_history(plan, "auto_run_stopped",
                {"reason": args.reason or "unspecified", "was_active": was_active})
    write_plan(plan_name, plan)

    emit(ok({
        "plan": plan_name,
        "stopped": True,
        "was_active": was_active,
        "reason": args.reason,
    }))


# ============================================================
# Subcommand: auto-run-status
# ============================================================

def cmd_auto_run_status(args):
    plan_name = resolve_plan(args.plan)
    if not plan_name:
        emit(err("plan_not_found", "활성 plan 없음."))

    plan = read_plan(plan_name)
    if plan is None:
        emit(err("plan_not_found", f"plan '{plan_name}' 없음.", {"name": plan_name}))

    auto_run = plan.get("auto_run", {})
    active = auto_run.get("active", False)
    started_at = auto_run.get("started_at")
    stale = active and is_stale(started_at)

    emit(ok({
        "plan": plan_name,
        "active": active,
        "started_at": started_at,
        "current_phase": auto_run.get("current_phase"),
        "stale": stale,
    }))


# ============================================================
# Subcommand: current
# ============================================================

def cmd_current(args):
    state = read_global_state()
    name = state.get("current_plan")
    exists = bool(name) and get_progress_path(name).exists()
    emit(ok({
        "current_plan": name,
        "exists": exists,
        "updated_at": state.get("updated_at"),
    }))


# ============================================================
# Subcommand: set-current
# ============================================================

def cmd_set_current(args):
    name = args.plan_name
    if not get_progress_path(name).exists():
        emit(err("plan_not_found", f"plan '{name}' 없음.", {"name": name}))
    state = read_global_state()
    previous = state.get("current_plan")
    state["current_plan"] = name
    write_global_state(state)
    emit(ok({"previous": previous, "current": name}))


# ============================================================
# CLI
# ============================================================

def build_parser():
    parser = argparse.ArgumentParser(prog="plan_state", description="Plan state CLI")
    subs = parser.add_subparsers(dest="command", required=True)

    p = subs.add_parser("register", help="Register a new plan from stdin JSON")
    p.add_argument("--source", required=True)
    p.set_defaults(fn=cmd_register)

    p = subs.add_parser("list")
    p.set_defaults(fn=cmd_list)

    p = subs.add_parser("unload")
    p.add_argument("plan_name")
    p.add_argument("--force", action="store_true")
    p.set_defaults(fn=cmd_unload)

    p = subs.add_parser("start")
    p.add_argument("phase_id")
    p.add_argument("--plan", default=None)
    p.set_defaults(fn=cmd_start)

    p = subs.add_parser("pause")
    p.add_argument("phase_id", nargs="?", default=None)
    p.add_argument("--plan", default=None)
    p.set_defaults(fn=cmd_pause)

    p = subs.add_parser("complete")
    p.add_argument("phase_id")
    p.add_argument("--plan", default=None)
    p.set_defaults(fn=cmd_complete)

    p = subs.add_parser("rollback")
    p.add_argument("phase_id")
    p.add_argument("--to", default="pending", choices=["pending", "in_progress"])
    p.add_argument("--confirm-cascade", action="store_true")
    p.add_argument("--plan", default=None)
    p.set_defaults(fn=cmd_rollback)

    p = subs.add_parser("tasks")
    p.add_argument("phase_id")
    p.add_argument("--complete", type=int, default=None)
    p.add_argument("--plan", default=None)
    p.set_defaults(fn=cmd_tasks)

    p = subs.add_parser("status")
    p.add_argument("--detail", action="store_true")
    p.add_argument("--plan", default=None)
    p.set_defaults(fn=cmd_status)

    p = subs.add_parser("check-source")
    p.add_argument("--plan", default=None)
    p.set_defaults(fn=cmd_check_source)

    p = subs.add_parser("apply-redesign")
    p.add_argument("--plan", default=None)
    p.set_defaults(fn=cmd_apply_redesign)

    p = subs.add_parser("impact")
    p.add_argument("phase_id")
    p.add_argument("--action", choices=["complete", "rollback", "delete"], default=None)
    p.add_argument("--plan", default=None)
    p.set_defaults(fn=cmd_impact)

    p = subs.add_parser("auto-run-start")
    p.add_argument("--plan", default=None)
    p.set_defaults(fn=cmd_auto_run_start)

    p = subs.add_parser("auto-run-stop")
    p.add_argument("--reason", choices=["completed", "failed", "paused"], default=None)
    p.add_argument("--plan", default=None)
    p.set_defaults(fn=cmd_auto_run_stop)

    p = subs.add_parser("auto-run-status")
    p.add_argument("--plan", default=None)
    p.set_defaults(fn=cmd_auto_run_status)

    p = subs.add_parser("current")
    p.set_defaults(fn=cmd_current)

    p = subs.add_parser("set-current")
    p.add_argument("plan_name")
    p.set_defaults(fn=cmd_set_current)

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
