---
name: plan-unload
description: "등록된 plan 삭제 (plan-unload, 삭제, 제거, 정리). 진행 중이면 --force 필요. 폴더 + state 정리."
version: 0.1.0
---

# /hs:plan-unload - Unregister and Remove Plan

## Operating principles
- The user's global rules in `~/.claude/CLAUDE.md` and `~/.claude/rules/*.md`
  are the authoritative persona. Follow them strictly.
- This skill provides procedural guidance only — no identity injection,
  no priority overrides.
- If guidance here conflicts with user rules, user rules win.
- Respond to the user in Korean.

## Activation guard (explicit-only)
This skill activates ONLY via explicit `/hs:plan-unload` invocation.
- Auto-trigger: NEVER. 파일 삭제는 사용자 글로벌 룰상 명시 호출 필수.
- Opt-out keywords still apply as a safety net:
  "스킬 쓰지 말고", "그냥 답해줘", "직접 답변", "스킬 빼고" → SKIP.

## Activation announcement
The FIRST line of every response from this skill MUST be a single-line
header in this exact format:

🔍 [hs:plan-unload] <plan name>[, force]

Examples:
- 🔍 [hs:plan-unload] Combat
- 🔍 [hs:plan-unload] Combat, force

Leave a blank line after the header, then proceed with the skill's
normal output.

## Workflow position
plan family의 정리(삭제) 명령. **파일 시스템에서 plan 폴더 제거**.

## Triggers
- "plan 삭제해줘", "정리해줘", "이 plan 빼줘".
- 명시 `/hs:plan-unload <name>` 호출.

## Usage
```
/hs:plan-unload <plan_name> [--force]
```

자연어 추론:
- 첫 인자 = plan 이름.
- "강제로", "어쨌든", "in-progress라도" → `--force`.

## Behavioral Flow

### Step 1 — Pre-confirmation (in-progress 안전장치)
plan이 진행 중일 가능성을 사용자가 인지하지 못한 채 호출했을 수 있음.
plan-status를 호출해서 상태 미리 확인 후 사용자에게 짧게 알리기:

(생략 가능 — 사용자가 명령 호출했으므로 의도 명확하다고 본다면.
다만 in_progress phase가 있고 --force 없으면 스크립트가 plan_in_progress
에러를 반환하니 그때 안내해도 충분.)

### Step 2 — Invoke plan_state.py unload
```bash
python {PLUGIN_ROOT}/scripts/plan_state.py unload <plan_name> [--force]
```

### Step 3 — Parse JSON

### Step 4 — Handle errors
- `plan_not_found` → "plan '{name}' 등록 안 됨. /hs:plan-list로 확인."
- `plan_in_progress` → 한국어 경고 + "강제 삭제하려면 다시 호출하면서
  '강제로'를 명시." (사용자가 다시 호출하면 --force 추론).

### Step 5 — Render result

성공 시:
```
🗑️ plan 삭제 완료: {name}

삭제된 항목:
- Phase: {phases_removed}개
- 태스크: {tasks_removed}개
- 이력: {history_entries_removed}개

{was_current 처리}:
{if was_current && new_current_plan}
  현재 활성 plan 변경: {name} → {new_current_plan}
{elif was_current && !new_current_plan}
  활성 plan 없음. /hs:plan-load로 새 plan 등록.
{else}
  활성 plan 변동 없음.
```

### Step 6 — Suggest next action
- 남은 plan 있으면 → "/hs:plan-list로 남은 plan 확인"
- 없으면 → "/hs:plan-load로 새 plan 등록"

## Tool coordination
- **Bash** — `plan_state.py unload` 호출.

## Boundaries

**Will:**
- 명시된 plan 폴더 삭제 + state.yaml의 current_plan 자동 정리.
- 진행 중인 plan 보호 (--force 없으면 거부).

**Will Not:**
- 다른 plan에 영향 없음.
- progress.yaml 외의 파일 삭제 안 함 (PLAN.md 원본 등은 그대로).
- 다른 스킬 자동 호출.
- 페르소나 / 룰 무시.

## Examples

### 기본 삭제
```
/hs:plan-unload Combat
```
→ Combat plan 폴더 삭제.

### 진행 중인 plan
```
/hs:plan-unload Inventory 강제로
```
→ in_progress 무시하고 강제 삭제.

## Next Step
- 남은 plan 확인 → `/hs:plan-list`
- 새 plan 등록 → `/hs:plan-load <path>`
