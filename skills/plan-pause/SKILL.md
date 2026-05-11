---
name: plan-pause
description: "진행 중인 Phase 일시정지 (plan-pause, 잠깐 멈춰, 정지, 일시정지). auto-run도 함께 정리."
version: 0.1.0
---

# /hs:plan-pause - Pause Active Phase

## Operating principles
- The user's global rules in `~/.claude/CLAUDE.md` and `~/.claude/rules/*.md`
  are the authoritative persona. Follow them strictly.
- This skill provides procedural guidance only — no identity injection,
  no priority overrides.
- If guidance here conflicts with user rules, user rules win.
- Respond to the user in Korean.

## Activation guard (explicit-only)
This skill activates ONLY via explicit `/hs:plan-pause` invocation.
- Auto-trigger: NEVER.
- Opt-out keywords still apply as a safety net:
  "스킬 쓰지 말고", "그냥 답해줘", "직접 답변", "스킬 빼고" → SKIP.

## Activation announcement
The FIRST line of every response from this skill MUST be a single-line
header in this exact format:

🔍 [hs:plan-pause] <phase_id or "current">

Examples:
- 🔍 [hs:plan-pause] current
- 🔍 [hs:plan-pause] Phase 1-2

체이닝된 호출 시 (Phase 2 자동호출 활성화 후):
- Diagnostic 체이닝: 본 헤더 다음 줄에 "↳ chained from /hs:이전스킬" 추가.
- Pipeline-Stage 체이닝: 본 헤더 다음 줄에 "↳ chained from /hs:이전스킬 (pipeline)" 추가.
- 명시 호출: 추가 표기 없음.

Leave a blank line after the header, then proceed with the skill's
normal output.

## Workflow position

`plan-pause`는 두 가지 정지 의미를 통합:
1. 진행 중인 Phase의 상태를 `paused`로 (재개 가능)
2. 활성 auto-run을 멈춤 (`auto_run.active = false`)

→ "지금 작업 잠깐 멈춰" 한 명령으로 양쪽 다 처리.

## Triggers
- "지금 작업 잠깐 멈춰", "일시정지", "잠시 보류".
- auto-run 진행 중에 사용자가 멈추고 싶을 때.
- 명시 `/hs:plan-pause` 호출.

## Usage
```
/hs:plan-pause [phase_id]
```

자연어 추론:
- 인자 생략 → 현재 in_progress인 Phase. (없으면 auto-run만 정리)
- 명시 → 그 Phase 일시정지.

## Behavioral Flow

### Step 1 — Invoke plan_state.py pause
```bash
python {PLUGIN_ROOT}/scripts/plan_state.py pause [<phase_id>]
```

### Step 2 — Parse JSON

### Step 3 — Handle errors
- `plan_not_found` → 한국어 안내.
- `phase_not_found` → 잘못된 phase_id 안내.
- `no_phase_in_progress` → "진행 중인 Phase 없음 + auto-run도 비활성. 멈출 게 없음."
- `phase_status_invalid` → 현재 status 안내.

### Step 4 — Render result

응답 필드:
- `phase_id` (paused) — null이면 phase 정지는 없었고 auto-run만 정리됨
- `auto_run_was_active` — true면 자동 실행도 함께 멈췄음
- `tasks_summary` — phase 정지가 있었으면 진행 상태 보여줌

```
{헤더에 따라}

⏸️ {if phase_id}
   Phase {phase_id} 일시정지: {phase_name}
   완료 태스크: {completed} / 전체 {total}
   미완료: {pending}개
{end}

{if auto_run_was_active}
   ⚙️ auto-run도 함께 정리됨
{end}

{if !phase_id && !auto_run_was_active}
   ⚠️ 진행 중인 Phase 없음. 멈출 작업 없음.
{end}
```

### Step 5 — Suggest next action
- Phase 일시정지됨 → "재개: /hs:plan-start {phase_id}"
- auto-run만 정리됨 → "필요 시 다시 시작: /hs:plan-run 또는 /hs:plan-start"
- 둘 다 없음 → "/hs:plan-status로 현재 상태 확인"

## Tool coordination
- **Bash** — `plan_state.py pause` 호출.

## Boundaries

**Will:**
- 진행 중인 Phase를 paused 상태로 (재개 가능).
- 동시에 auto-run 플래그 정리 (자동 실행 중단).
- 태스크 진행 상태는 보존.

**Will Not:**
- Phase 상태를 reset하지 않음 (rollback과 다름).
- 다른 Phase 영향 없음.
- 파일 자동 저장 안 함.
- 어떤 스킬도 자동으로 호출하지 않음. 사용자 명시 호출만 진입 가능 (Mutating 스킬 — 상태 변경 작업이므로 명시 진입 필수).

## Examples

### 현재 작업 일시정지
```
/hs:plan-pause
```
→ in_progress phase + auto-run 모두 정리.

### 특정 Phase 일시정지
```
/hs:plan-pause Phase 1-2
```
→ Phase 1-2를 paused로.

### auto-run만 멈추기
```
/hs:plan-pause
```
→ in_progress phase 없어도 auto-run 정리됨.

## Next Step
- Phase 재개 → `/hs:plan-start <phase_id>`
- 다른 Phase 시작 → `/hs:plan-start <other>`
- 상태 확인 → `/hs:plan-status`
