---
name: plan-run
description: "plan 자동 전체 실행 (plan-run, 자동 실행, 끝까지 가, 다 해줘). 사용자 일괄 승인 후 모든 Phase를 끝까지 자동 진행. 실패 즉시 정지."
version: 0.1.0
---

# /hs:plan-run - Auto-Execute Entire Plan

## Operating principles
- The user's global rules in `~/.claude/CLAUDE.md` and `~/.claude/rules/*.md`
  are the authoritative persona. Follow them strictly.
- This skill provides procedural guidance only — no identity injection,
  no priority overrides.
- If guidance here conflicts with user rules, user rules win.
- Respond to the user in Korean.

## Activation guard (explicit-only)
This skill activates ONLY via explicit `/hs:plan-run` invocation.
- Auto-trigger: NEVER. **자동 실행 = 무거운 권한**. 명시 호출 필수.
- Opt-out keywords still apply as a safety net:
  "스킬 쓰지 말고", "그냥 답해줘", "직접 답변", "스킬 빼고" → SKIP.

## Activation announcement
The FIRST line of every response from this skill MUST be a single-line
header in this exact format:

🔍 [hs:plan-run] <plan name>, <starting from phase>

Examples:
- 🔍 [hs:plan-run] Combat, Phase 1-1부터 자동 실행
- 🔍 [hs:plan-run] Inventory, Phase 2-2부터 재개

Leave a blank line after the header, then proceed with the skill's
normal output.

## Workflow position

`plan-run`은 **plan family의 자동 오케스트레이션 명령**.

```
plan-run 호출
  ↓
[승인 단계] 시작 시 일괄 승인
  ↓
[루프]
  plan_state.py auto-run-start          → auto_run.active = true
  plan_state.py status                  → 다음 Phase 식별
  plan_state.py start <phase>           → Phase in_progress
  /hs:implement 워크플로우 (Step 3 skip) → 코드 변경
  plan_state.py tasks --complete <i>     → 태스크 완료 추적
  plan_state.py complete <phase>         → Phase 완료 + 후행 해제
  ↑ 다음 Phase 있나? → 반복
  ↓
plan_state.py auto-run-stop --reason completed → auto_run.active = false
종결 보고
```

수동 단계 호출 (`plan-start` / `plan-complete`)와 같은 스크립트
primitives 사용. plan-run은 그 호출들을 자동으로 줄줄이 연결.

## Triggers
- "처음부터 끝까지 자동", "전체 자동 실행", "끝까지 가줘".
- 명시 `/hs:plan-run` 호출.

## Usage
```
/hs:plan-run [plan_name]
```

자연어 추론:
- 인자 생략 → current_plan.
- 플래그 없음 (단순 인터페이스).

## Behavioral Flow

### Step 0 — Prerequisites check

#### 0a. plan 존재 확인
```bash
python {PLUGIN_ROOT}/scripts/plan_state.py status [--plan <name>]
```

에러 시:
- `plan_not_found` → "활성 plan 없음. /hs:plan-load 먼저."
- `plan_already_completed` (status 응답에서 plan_status: completed)
  → "plan 이미 완료. /hs:plan-redesign 또는 새 plan-load."

#### 0b. auto-run 충돌 확인
```bash
python {PLUGIN_ROOT}/scripts/plan_state.py auto-run-status [--plan <name>]
```

응답에 `active: true && stale: false`:
- "이미 자동 실행 중. plan-pause 후 재시도 또는 24시간 후 자동 stale 처리."
- 종료.

응답에 `active: true && stale: true`:
- 자동 정리는 auto-run-start가 처리. 사용자에게 한 줄 알림.

### Step 1 — Compute scope and impact

`status` 응답에서:
- 미완료 Phase 목록 (pending / in_progress / paused / blocked)
- 각 Phase의 태스크 개수 합산
- 시작 위치 (in_progress 있으면 그 Phase, 없으면 다음 pending)

LLM이 PLAN.md / DESIGN.md를 추가로 읽어 **변경 범위 추정** (선택):
- `Read` Phase 이름 / 태스크 이름에서 영향받을 파일 / 모듈 추정.
- 정확하지 않아도 됨 — 사용자에게 대략적 범위 보여주는 용도.

### Step 2 — Bulk approval (필수)

사용자에게 일괄 승인 요청:

```
🤖 plan-run 자동 실행 사전 확인

plan: {name}
시작 위치: Phase {first_phase}
실행 예정: {phases_remaining}개 Phase, {total_tasks}개 태스크

예상 작업 범위:
{LLM이 추정한 영향 영역}
- 영향 모듈: {modules}
- 영향 파일 추정: {files}
- 신규 파일 추정: {N}개

⚙️ 자동 실행 동작:
- 각 Phase의 implement Step 3 (사전 승인) 일괄 면제
- 코드 변경 진행 중 검증/실패 가드는 그대로 작동
- 어느 Phase 실패 시 즉시 정지 (rollback 안 함)
- Phase 간 pause 없음 (끝까지 직진)
- 진행 중 사용자 입력 시 자연스럽게 정지 가능
- 명시 정지: /hs:plan-pause

진행할까요? (yes/no)
```

WAIT for user approval. "yes" / "진행" / "OK" 등 → 진행. 그 외 → 종료.

### Step 3 — Mark auto_run active
```bash
python {PLUGIN_ROOT}/scripts/plan_state.py auto-run-start [--plan <name>]
```

응답에 `first_phase` 명시됨. stale_cleaned: true면 한 줄 알림.

### Step 4 — Main loop

```
loop:
  current_phase = first_phase (initial)
  
  while current_phase exists:
    1. plan_state.py start <current_phase>
       → 실패 시 break (실패 정지 정책)
    
    2. /hs:implement 워크플로우 진입
       (auto_run.active=true 이므로 Step 3 skip)
       
       a. 첫 태스크 분석 (대상 / 변경 범위)
       b. 코드 변경 적용 (Edit / Write / serena)
       c. 검증 (syntax, diagnostics)
       d. plan_state.py tasks <phase> --complete <i>
       e. 다음 태스크 반복 (모두 완료 때까지)
       
       어떤 단계든 실패 시 → break
    
    3. plan_state.py complete <current_phase>
       → released_phases 확인, next_suggested 받음
    
    4. is_plan_completed: true 면 break (정상 종료)
    
    5. current_phase = next_suggested
       null이면 break (더 진행할 Phase 없음)

종료:
  plan_state.py auto-run-stop --reason {completed|failed}
```

### Step 5 — Per-phase observability

각 Phase 시작/완료 시 짧은 진행 보고:

```
[Phase 1-1 시작] 데이터 모델 정의
- 태스크 3개

  → src/Combat/Player.cs 신규 (50라인)
  → src/Combat/Inventory.cs 신규 (30라인)
  → src/Combat/SaveData.cs 신규 (45라인)
  ✓ 태스크 1/3 완료
  ✓ 태스크 2/3 완료
  ✓ 태스크 3/3 완료

[Phase 1-1 완료] (35초)
🔓 해제: Phase 1-2

[Phase 1-2 시작] 코어 로직
...
```

→ 사용자가 무슨 일이 일어나는지 따라갈 수 있음.

### Step 6 — Failure handling

어느 단계든 에러 발생 시:

1. 즉시 정지 (다음 Phase 시작 안 함).
2. `plan_state.py auto-run-stop --reason failed`.
3. 사용자에게 명확한 보고:

```
❌ plan-run 정지 (Phase {phase_id}에서 실패)

실패 시점: {step}
에러: {error message}

지금까지 완료:
- Phase: {completed} / {total}
- 태스크: {tasks_completed}

마지막 Phase 상태: {phase_status}

💡 다음 단계 (사용자 결정):
- 원인 분석 후 수동 재시도: /hs:plan-start {phase}
- 상태 되돌리기: /hs:plan-rollback {phase}
- 현황 확인: /hs:plan-status
```

### Step 7 — Successful completion

마지막 Phase까지 정상 완료:

```
🎉 plan-run 완료

plan: {name}
총 Phase: {total}개 (모두 완료)
총 태스크: {tasks_total}개
소요: {duration}

📁 상태 보존: .hs/PlanTask/{name}/progress.yaml
   (이력 / 진행 기록 그대로 보관됨)

다음 단계 (사용자 결정):
- 보관: 그대로 둠 (별도 작업 불필요)
- 정리: /hs:plan-unload {name}
- 재작업: PLAN.md 수정 후 /hs:plan-redesign
```

### Step 8 — User interrupt during run

사용자가 진행 중에 무언가 입력 / Ctrl+C 등으로 끊으면:
- 현재 진행 중인 Phase의 코드 변경은 abort 가능 (처리 중 단계라면)
- `auto_run.active`를 정리하기 위해 사용자에게 plan-pause 권장
- 또는 다음 응답에서 자동으로 plan_state.py auto-run-stop --reason paused 호출

→ 명시 정지: `/hs:plan-pause`

## Tool coordination
- **Bash** — `plan_state.py` 호출 (status, auto-run-*, start, tasks, complete).
- **Read / Glob / Grep / serena** — 코드 이해 (implement 흐름).
- **Write / Edit / MultiEdit / serena** — 코드 변경 (implement 흐름).
- 도구 사용 가이드는 implement.md의 Tool coordination + MCP integration 참고.

## Boundaries

**Will:**
- 시작 시 일괄 승인 받은 후 자동으로 모든 Phase 실행.
- 각 Phase 시작/태스크 완료/Phase 완료 자동 추적 (progress.yaml).
- 실패 시 즉시 정지 + auto_run 정리.
- Phase 간 pause 없이 끝까지 직진.
- 사용자 인터럽트 시 자연스럽게 정지 가능.
- 정상 완료 / 실패 / 인터럽트 모두 종결 메시지로 명확히 보고.

**Will Not:**
- 사전 일괄 승인 없이 자동 실행 시작하지 않음.
- 실패 후 자동 rollback / 자동 재시도 하지 않음
  (사용자가 plan-rollback / plan-start로 명시 처리).
- 매 Phase 마다 사용자에게 추가 승인 요청하지 않음
  (그건 수동 plan-start의 역할).
- progress.yaml 직접 편집 금지 (스크립트 경유).
- plan-run을 다른 plan에 자동 전이하지 않음.
- 페르소나 주입 / 사용자 룰 무시.

## Examples

### 표준 자동 실행
```
/hs:plan-run
```
→ current_plan에 대해 일괄 승인 → 자동 진행.

### 특정 plan 자동 실행
```
/hs:plan-run Inventory
```
→ Inventory plan 자동 진행.

### 일시정지 후 재개 (자동)
```
/hs:plan-pause
... (일시정지됨)
/hs:plan-run
```
→ paused 상태 복구하며 이어서 자동 진행.

### 자동 실행 중 인터럽트
```
사용자 입력 / 다른 명령
```
→ LLM이 자연스럽게 정지. plan-pause 권장 안내.

### 실패 후 재시도
```
/hs:plan-run
... (Phase 1-3에서 실패)
사용자가 코드 / PLAN 수정 후
/hs:plan-run
```
→ in_progress인 Phase 1-3부터 재개.

## Next Step
- 자동 실행 결과 확인 → `/hs:plan-status`
- 정리 → `/hs:plan-unload`
- 부분 롤백 → `/hs:plan-rollback`
- 새 작업 → `/hs:plan-redesign` 또는 새 plan-load
