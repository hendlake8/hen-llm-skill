---
name: plan-start
description: "Phase 실행 시작 (plan-start, 시작, 이거 진행). 의존성 검증 후 Phase 상태 in_progress + /hs:implement 워크플로우로 핸드오프."
version: 0.1.0
---

# /hs:plan-start - Begin Phase Execution

## Operating principles
- The user's global rules in `~/.claude/CLAUDE.md` and `~/.claude/rules/*.md`
  are the authoritative persona. Follow them strictly.
- This skill provides procedural guidance only — no identity injection,
  no priority overrides.
- If guidance here conflicts with user rules, user rules win.
- Respond to the user in Korean.

## Activation guard (explicit-only)
This skill activates ONLY via explicit `/hs:plan-start` invocation.
- Auto-trigger: NEVER. 단, `/hs:plan-run` 오케스트레이션 내부에서
  스크립트 동작이 호출되는 것은 별개.
- Opt-out keywords still apply as a safety net:
  "스킬 쓰지 말고", "그냥 답해줘", "직접 답변", "스킬 빼고" → SKIP.

## Activation announcement
The FIRST line of every response from this skill MUST be a single-line
header in this exact format:

🔍 [hs:plan-start] <phase_id>[, resumed]

Examples:
- 🔍 [hs:plan-start] Phase 1-1
- 🔍 [hs:plan-start] Phase 1-2, resumed

체이닝된 호출 시 (Phase 2 자동호출 활성화 후):
- Diagnostic 체이닝: 본 헤더 다음 줄에 "↳ chained from /hs:이전스킬" 추가.
- Pipeline-Stage 체이닝: 본 헤더 다음 줄에 "↳ chained from /hs:이전스킬 (pipeline)" 추가.
- 명시 호출: 추가 표기 없음.

Leave a blank line after the header, then proceed with the skill's
normal output.

## Workflow position

`plan-start`는 plan family의 **실행 진입점**:

```
plan-load → plan-start → (implement 워크플로우로 진입) → plan-complete
                ↓
            scripts/plan_state.py start
                ↓
            Phase 상태 in_progress 마킹
                ↓
            태스크 목록을 implement 컨텍스트로 전달
```

수동 모드와 자동 모드(`/hs:plan-run`) 모두 같은 진입점 사용.
auto_run.active 플래그에 따라 implement skill의 Step 3 (pre-flight
approval) 동작이 분기됨 — 자동 모드면 일괄 승인된 상태로 간주, skip.

## Triggers
- "Phase X-Y 시작", "이거 진행해줘", "이 Phase 작업하자".
- 일시정지 후 재개: "이어서", "다시 시작".
- 명시 `/hs:plan-start <phase_id>` 호출.

## Usage
```
/hs:plan-start <phase_id>
```

자연어 추론: phase_id는 명시 권장. 모호하면 plan-status로 다음 추천
phase 확인 후 사용자에게 물어보기.

## Behavioral Flow

### Step 1 — Invoke plan_state.py start
```bash
python {PLUGIN_ROOT}/scripts/plan_state.py start <phase_id>
```

### Step 2 — Parse JSON

### Step 3 — Handle errors
- `plan_not_found` → "활성 plan 없음. /hs:plan-load 먼저."
- `plan_already_completed` → "plan 완료됨. /hs:plan-redesign 또는 새 plan-load 필요."
- `phase_not_found` → "Phase 없음. /hs:plan-status로 확인."
- `phase_status_invalid` (이미 진행 중 / 이미 완료) → 상태 안내.
- `another_phase_in_progress` → "다른 Phase 진행 중: {id}. plan-pause 또는 plan-complete 후 시작."
- `dependencies_not_met` → 한국어 안내:
  ```
  ❌ 선행 Phase 미완료:
  {각 blocking 항목}
  - Phase {id}: {status_kr} ({tasks_remaining}개 미완료)
  {end}

  💡 먼저 진행: /hs:plan-start {first_blocking_id}
  ```

### Step 4 — Render success + show tasks

```
🚀 Phase {phase_id} 시작: {phase_name}
{if resumed_from_pause}
   (일시정지에서 재개됨)
{end}
시작 시각: {started_at}

📋 태스크 목록:
{각 task에 대해}
{icon} [{index}] {name}
{end}
```

### Step 5 — Hand off to implement workflow

이 단계가 핵심. plan-start는 **`/hs:implement` 스킬의 행동 양식으로
즉시 진입**. 사용자에게 명시적으로 알림:

```
🔄 implement 워크플로우 진입

이제 위 태스크들을 순차적으로 구현합니다.
- 코드 변경 시 /hs:implement의 원칙 적용
  (사용자 글로벌 룰 준수, 코드 컨벤션 준수, 변경 사전 승인 등)
- auto_run 활성 시 사전 승인은 일괄 승인으로 간주됨 (skip)
- 태스크 단위 진행은 자연스럽게 (LLM 자동 추론 또는 명시 plan-tasks)
```

이후 LLM의 행동:
1. 첫 태스크 분석 (대상 파일 / 변경 범위 / 의존)
2. **auto_run.active 확인** (json 응답 또는 별도 plan_state.py auto-run-status 호출)
3. auto_run.active == false → /hs:implement Step 3 (변경 계획 + 사용자 승인)
4. auto_run.active == true → 승인 skip, 바로 적용
5. 코드 변경 적용
6. 태스크 완료 시 `plan-tasks <phase_id> --complete <idx>` 호출 (LLM 추론)
7. 모든 태스크 완료 시 `plan-complete <phase_id>` 호출 안내 / 자동 호출 (auto_run 시)

### Step 6 — Output policy
- 태스크 작업 진행 상황은 대화로 표시.
- 코드 변경은 implement 흐름에 따름 (Edit/MultiEdit/serena).
- 보고서 파일 자동 저장 안 함.

## Tool coordination
- **Bash** — `plan_state.py start` 호출 + 작업 중 진행 추적
  (plan-tasks --complete, plan-complete).
- **이후 도구는 implement 워크플로우의 도구 사용**:
  - serena (코드 이해/편집 우선)
  - Read / Glob / Grep
  - Edit / MultiEdit / Write
  - 자세한 가이드는 `/hs:implement`의 Tool coordination 참고.

## Boundaries

**Will:**
- 명시된 Phase 시작 (의존성 검증 + status 변경).
- 태스크 목록을 사용자에게 보여주고 implement 워크플로우 진입.
- 일시정지된 Phase 재개 시 태스크 진행 상태 보존.
- auto_run.active 상태에 따라 implement의 사전 승인 동작 분기.

**Will Not:**
- 의존성 미충족 시 강제 시작하지 않음.
- 다른 Phase 진행 중일 때 동시 시작하지 않음
  (먼저 plan-pause 또는 plan-complete).
- 코드 변경을 사용자 룰 위반 방식으로 진행하지 않음
  (글로벌 룰 + implement 원칙 준수).
- plan-complete를 자동으로 호출하지 않음
  (auto_run 모드는 plan-run의 책임).
- 어떤 스킬도 자동으로 호출하지 않음. 사용자 명시 호출만 진입 가능 (Mutating 스킬 — 상태 변경 작업이므로 명시 진입 필수). 단 plan-run 사전 일괄 승인 모드 하에서는 auto_run 흐름이 plan-complete 자동 호출 — 그 경우도 사용자가 plan-run 호출 시점에 일괄 승인한 범위.

## Examples

### 기본 시작
```
/hs:plan-start Phase 1-1
```
→ 의존성 검증 → Phase in_progress → 태스크 목록 → implement 진입.

### 일시정지에서 재개
```
/hs:plan-start Phase 1-2
```
→ 이전 paused 상태 → in_progress 복귀 → 미완료 태스크부터 재개.

### 의존성 미충족
```
/hs:plan-start Phase 2-1
```
→ Phase 1-2 미완료 → 에러 + "먼저 Phase 1-2 진행" 안내.

### 다른 Phase 진행 중
```
/hs:plan-start Phase 1-2
```
→ 이미 Phase 1-1 진행 중 → "plan-pause Phase 1-1 또는
  plan-complete Phase 1-1 후 시작" 안내.

## Next Step
- 작업 중 → 코드 변경 + plan-tasks --complete 추적
- Phase 모든 태스크 완료 시 → `/hs:plan-complete <phase_id>`
- 도중 중단 시 → `/hs:plan-pause`
- 자동 진행 원하면 처음부터 → `/hs:plan-run`

This skill enters the implement workflow but takes no further
action automatically (other than progress tracking). Phase completion
is the user's explicit decision.
