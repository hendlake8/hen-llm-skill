---
name: plan-complete
description: "Phase 완료 처리 (plan-complete, 완료, 끝났다, 다음 Phase 풀어줘). 후행 Phase 자동 해제. 마지막 Phase면 plan 전체 완료 마킹."
version: 0.1.0
---

# /hs:plan-complete - Mark Phase Completed

## Operating principles
- The user's global rules in `~/.claude/CLAUDE.md` and `~/.claude/rules/*.md`
  are the authoritative persona. Follow them strictly.
- This skill provides procedural guidance only — no identity injection,
  no priority overrides.
- If guidance here conflicts with user rules, user rules win.
- Respond to the user in Korean.

## Activation guard (explicit-only)
This skill activates ONLY via explicit `/hs:plan-complete` invocation.
- Auto-trigger: NEVER. 단, `/hs:plan-run` 오케스트레이션에서 이
  스크립트 동작이 자동 호출되는 것은 별개 (스킬이 아니라 스크립트
  레벨 호출이기 때문).
- Opt-out keywords still apply as a safety net:
  "스킬 쓰지 말고", "그냥 답해줘", "직접 답변", "스킬 빼고" → SKIP.

## Activation announcement
The FIRST line of every response from this skill MUST be a single-line
header in this exact format:

🔍 [hs:plan-complete] <phase_id>

Example:
- 🔍 [hs:plan-complete] Phase 1-2

체이닝된 호출 시 (Phase 2 자동호출 활성화 후):
- Diagnostic 체이닝: 본 헤더 다음 줄에 "↳ chained from /hs:이전스킬" 추가.
- Pipeline-Stage 체이닝: 본 헤더 다음 줄에 "↳ chained from /hs:이전스킬 (pipeline)" 추가.
- 명시 호출: 추가 표기 없음.

Leave a blank line after the header, then proceed with the skill's
normal output.

## Workflow position

`plan-complete`는 Phase의 모든 작업이 끝났음을 기록하고:
- 모든 태스크를 completed로 일괄 처리
- 후행 Phase 중 차단(blocked)된 것들 해제 (의존성 만족 시 pending으로)
- 마지막 Phase면 plan 전체 `plan_status: completed` 마킹 + auto-run 정리

## Triggers
- "Phase X-Y 완료", "이거 끝났어", "다음 Phase 풀어줘".
- 명시 `/hs:plan-complete <phase_id>` 호출.

## Usage
```
/hs:plan-complete <phase_id>
```

자연어 추론: phase_id는 명시 필수. 모호하면 묻기.

## Behavioral Flow

### Step 1 — Invoke plan_state.py complete
```bash
python {PLUGIN_ROOT}/scripts/plan_state.py complete <phase_id>
```

### Step 2 — Parse JSON

### Step 3 — Handle errors
- `plan_not_found` → 한국어 안내.
- `phase_not_found` → "Phase '{phase_id}' 없음. /hs:plan-status로 확인."
- `phase_status_invalid` → 현재 status 안내. (예: pending이면 plan-start 먼저)

### Step 4 — Render result

응답 주요 필드:
- `released_phases` — 차단 해제된 Phase 목록
- `is_plan_completed` — 마지막 Phase 완료로 plan 전체 종결 여부
- `progress` — 전체 진행률
- `next_suggested` — 다음 권장 Phase

**일반 완료**:
```
✅ Phase {phase_id} 완료: {phase_name}

진행률: {bar} {percent}% ({completed}/{total} Phase)

{if released_phases not empty}
🔓 다음 Phase 해제됨:
{각 released_phases에 대해}
- Phase {id}: blocked → pending
{end}

다음 추천: /hs:plan-start {next_suggested}
```

**plan 전체 종결 (`is_plan_completed: true`)**:
```
🎉 Phase {phase_id} 완료: {phase_name}

진행률: ████████████████████ 100% ({total}/{total} Phase)

🎉 plan 전체 완료!

총 Phase: {total}개
완료 시각: {completed_at}

다음 단계 (사용자 결정):
- 보관: 그대로 둠 (별도 작업 불필요)
- 정리: /hs:plan-unload {plan name}
- 재작업: PLAN.md 수정 후 /hs:plan-redesign
```

### Step 5 — Output policy
- 결과는 대화로만.
- 파일 자동 저장 안 함.

## Tool coordination
- **Bash** — `plan_state.py complete` 호출.

## Boundaries

**Will:**
- 명시된 Phase의 모든 태스크를 completed 일괄 처리.
- 후행 Phase 중 차단 해제 가능한 것 자동 처리.
- 마지막 Phase면 plan 전체 completed + auto-run 정리.

**Will Not:**
- pending 상태 Phase에 대해 호출 거부 (먼저 plan-start 필요).
- in_progress가 아닌데 강제로 완료 처리하지 않음
  (paused는 허용, 그 외는 거부).
- 어떤 스킬도 자동으로 호출하지 않음. 사용자 명시 호출만 진입 가능 (Mutating 스킬 — 상태 변경 작업이므로 명시 진입 필수).
- 파일 자동 저장 안 함.

## Examples

### Phase 완료
```
/hs:plan-complete Phase 1-1
```
→ Phase 1-1 완료 + Phase 1-2 차단 해제 (있으면).

### 마지막 Phase 완료
```
/hs:plan-complete Phase 3-2
```
→ plan 전체 종결 메시지 표시.

## Next Step
- 다음 Phase 시작 → `/hs:plan-start <next_suggested>`
- 자동 진행 → `/hs:plan-run`
- 종결된 plan 정리 → `/hs:plan-unload <name>`
- 진행 확인 → `/hs:plan-status`
