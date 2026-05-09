---
name: plan-rollback
description: "Phase 상태 되돌리기 (plan-rollback, 롤백, 되돌리기, 안 한 걸로). 후행 Phase 차단 cascade 발생 시 사용자 확인 필요."
version: 0.1.0
---

# /hs:plan-rollback - Roll Back Phase State

## Operating principles
- The user's global rules in `~/.claude/CLAUDE.md` and `~/.claude/rules/*.md`
  are the authoritative persona. Follow them strictly.
- This skill provides procedural guidance only — no identity injection,
  no priority overrides.
- If guidance here conflicts with user rules, user rules win.
- Respond to the user in Korean.

## Activation guard (explicit-only)
This skill activates ONLY via explicit `/hs:plan-rollback` invocation.
- Auto-trigger: NEVER. 상태 변경 + cascade 영향 큼.
- Opt-out keywords still apply as a safety net:
  "스킬 쓰지 말고", "그냥 답해줘", "직접 답변", "스킬 빼고" → SKIP.

## Activation announcement
The FIRST line of every response from this skill MUST be a single-line
header in this exact format:

🔍 [hs:plan-rollback] <phase_id> → <target_status>[, with cascade]

Examples:
- 🔍 [hs:plan-rollback] Phase 1-2 → pending
- 🔍 [hs:plan-rollback] Phase 1-1 → pending, with cascade

Leave a blank line after the header, then proceed with the skill's
normal output.

## Workflow position
plan family의 복구 명령. Phase 상태를 이전으로 되돌리기.

롤백 대상 Phase가 다른 Phase의 의존 대상이면 후행 Phase들이
**연쇄적으로 blocked 상태**가 됨 (cascade). 그래서 두 단계 흐름:

1. Preview — 영향 범위 보여주기
2. Confirm — 사용자 승인 후 적용

## Triggers
- "Phase X-Y 롤백", "이거 안 한 걸로", "되돌려줘".
- 명시 `/hs:plan-rollback <phase_id>` 호출.

## Usage
```
/hs:plan-rollback <phase_id> [--to pending|in_progress]
```

자연어 추론:
- 첫 인자 = phase_id.
- "in_progress로", "다시 진행 중으로" → `--to in_progress` (기본은 pending).

## Behavioral Flow

### Step 1 — Initial invoke (preview mode)
첫 호출은 `--confirm-cascade` 없이:

```bash
python {PLUGIN_ROOT}/scripts/plan_state.py rollback <phase_id> [--to <status>]
```

### Step 2 — Parse JSON

응답에 `"preview": true`가 있으면:
- cascade 영향 있음
- 사용자 확인 필요

### Step 3 — Handle preview case

```
⚠️ 연쇄 영향 있음

Phase {phase_id}: {current_status} → {target_status}

영향받는 후행 Phase:
{각 cascade_impact 항목}
- Phase {id}: {status_before} → blocked

총 {N}개 Phase가 차단됨.

진행하시겠습니까?
승인 시 다시 호출: /hs:plan-rollback {phase_id} 강제로
또는 취소: /hs:plan-impact {phase_id} --action rollback 으로 영향 재확인
```

→ 사용자가 다시 호출하면서 "강제로"/"진행" 등을 붙이면 자연어로 `--confirm-cascade` 추론.

### Step 4 — Confirm invoke (with --confirm-cascade)
사용자가 진행 승인하면:

```bash
python {PLUGIN_ROOT}/scripts/plan_state.py rollback <phase_id> [--to <status>] --confirm-cascade
```

### Step 5 — Render confirmed result

```
🔙 Phase 롤백 완료: {phase_id}

상태: {status_before} → {status_after}

{if cascaded_phases not empty}
연쇄 차단된 Phase:
- Phase {id}: {status_before} → blocked
{end}

plan 상태: {plan_status}

⚠️ 차단된 Phase는 선행 Phase 재완료 시 자동 해제됨.
```

### Step 6 — Handle errors
- `plan_not_found`, `phase_not_found` → 한국어 안내.
- `phase_status_invalid` → 현재 status에서 롤백 불가 안내.
- `invalid_input` → --to 값 문제.

### Step 7 — Suggest next action
- "다시 작업 → /hs:plan-start {phase_id}"
- "현재 상황 확인 → /hs:plan-status"

## Tool coordination
- **Bash** — `plan_state.py rollback` 호출 (preview + confirm 두 번).

## Boundaries

**Will:**
- Phase 상태를 pending 또는 in_progress로 되돌림.
- pending으로 되돌릴 시 모든 태스크 status 리셋.
- cascade 영향을 사용자에게 먼저 보여주고 확인 받음.
- auto-run 진행 중이었다면 자동 정리.

**Will Not:**
- cascade 있을 때 사용자 확인 없이 진행하지 않음.
- pending → 더 이전 상태로 롤백 시도하지 않음 (이미 초기).
- 코드 / 파일 변경에 영향 주지 않음 (이건 plan 상태만).
- 다른 스킬 자동 호출.

## Examples

### 단순 롤백 (cascade 없음)
```
/hs:plan-rollback Phase 2-3
```
→ 의존하는 후행 Phase 없으면 즉시 적용.

### Cascade 있는 롤백
```
/hs:plan-rollback Phase 1-1
```
→ 1차: preview 표시 + 영향 범위.
→ 사용자 "강제로 진행" → 2차: 실제 롤백.

### in_progress로 되돌리기
```
/hs:plan-rollback Phase 1-2 진행 중으로
```
→ `--to in_progress`로 호출.

## Next Step
- 재시작 → `/hs:plan-start <phase_id>`
- 상태 확인 → `/hs:plan-status`
- 영향 분석 → `/hs:plan-impact <phase_id>`
