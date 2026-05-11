---
name: plan-redesign
description: "PLAN.md 변경 시 plan 재동기화 (plan-redesign, 재설계, 동기화). 진행 상태 보존하며 새 PLAN과 머지."
version: 0.1.0
---

# /hs:plan-redesign - Resync Plan with Modified PLAN.md

## Operating principles
- The user's global rules in `~/.claude/CLAUDE.md` and `~/.claude/rules/*.md`
  are the authoritative persona. Follow them strictly.
- This skill provides procedural guidance only — no identity injection,
  no priority overrides.
- If guidance here conflicts with user rules, user rules win.
- Respond to the user in Korean.

## Activation guard (explicit-only)
This skill activates ONLY via explicit `/hs:plan-redesign` invocation.
- Auto-trigger: NEVER. 진행 상태 보존이 핵심 — 신중한 호출.
- Opt-out keywords still apply as a safety net:
  "스킬 쓰지 말고", "그냥 답해줘", "직접 답변", "스킬 빼고" → SKIP.

## Activation announcement
The FIRST line of every response from this skill MUST be a single-line
header in this exact format:

🔍 [hs:plan-redesign] <plan name>[, preview]

Examples:
- 🔍 [hs:plan-redesign] Combat
- 🔍 [hs:plan-redesign] Combat, preview

체이닝된 호출 시 (Phase 2 자동호출 활성화 후):
- Diagnostic 체이닝: 본 헤더 다음 줄에 "↳ chained from /hs:이전스킬" 추가.
- Pipeline-Stage 체이닝: 본 헤더 다음 줄에 "↳ chained from /hs:이전스킬 (pipeline)" 추가.
- 명시 호출: 추가 표기 없음.

Leave a blank line after the header, then proceed with the skill's
normal output.

## Workflow position

PLAN.md를 사용자가 수정한 후 plan 시스템과 다시 정합 맞추기:

```
사용자가 PLAN.md 수정 (Phase 추가/삭제/태스크 변경 등)
              ↓
       /hs:plan-redesign
              ↓
    1. 새 PLAN.md 파싱
    2. 기존 progress.yaml 상태 확인
    3. 지능적 머지 (진행 상태 보존)
    4. atomic 적용
```

핵심 원칙: **진행 상태(completed phase, completed task)는 절대 잃지 않음**.
새 Phase 추가는 pending, 삭제된 Phase는 history에 남기고 제거.

## Triggers
- "PLAN.md 수정했어, 동기화해줘", "재설계", "plan 갱신".
- 명시 `/hs:plan-redesign` 호출.

## Usage
```
/hs:plan-redesign [plan_name] [--preview]
```

자연어 추론:
- 인자 생략 → current_plan.
- "미리보기", "변경사항만" → `--preview` (실제 적용 안 함).

## Behavioral Flow

### Step 1 — Check source change
```bash
python {PLUGIN_ROOT}/scripts/plan_state.py check-source [--plan <name>]
```

응답: `{"changed": true|false, "stored_hash": "...", "current_hash": "..."}`

### Step 2 — Handle "no change" case
`changed: false` → 변경 사항 없음 안내:
```
ℹ️ source 변경 사항 없음.

PLAN.md 마지막 동기화 이후 변경 없음.
PLAN.md 수정 후 재시도하세요.
```
→ 종료.

### Step 3 — Read both: current state + new source

#### 3a. 현재 progress.yaml 읽기

`.hs/PlanTask/{name}/progress.yaml` 직접 read:
```
Read .hs/PlanTask/{name}/progress.yaml
```

기존 phases 배열 + 각 phase의 status / tasks status 보존 대상.

#### 3b. 새 source PLAN.md 읽기 + 파싱

plan-load의 마크다운 파싱 로직 그대로 적용 (Step 2 of plan-load).

새 Phase 구조 추출:
```json
{
  "phases": [
    {"id": "Phase 1-1", "name": "...", "tasks": [{"name": "..."}]},
    ...
  ]
}
```

### Step 4 — Intelligent merge (LLM 판단)

기존과 새 Phase를 비교:

#### 4a. 매핑 분류

각 새 Phase에 대해:
- **유지** — 기존에도 같은 ID 존재 → 기존 status / tasks 보존
- **추가** — 기존에 없는 ID → status: pending으로 신규
- **변경** — 같은 ID, 이름 / 태스크가 다름 → 기존 status는 보존하되
  태스크 항목별 머지

각 기존 Phase에 대해 (새에 없으면):
- **삭제** — 새에 없는 ID → 삭제 대상

#### 4b. 태스크 머지 규칙

같은 Phase 내에서 새 태스크 vs 기존 태스크:
- **동일 이름** → 기존 status (completed 등) 보존
- **새 태스크 추가** → status: pending
- **기존에 있던 태스크가 새에 없음** → 삭제
  (단, completed였다면 history 노트 추가 권장)

#### 4c. 충돌 / 모호 경우 사용자 확인

- 진행 중(in_progress)인 Phase가 새 PLAN에서 삭제 → **위험**.
  사용자에게 확인:
  ```
  ⚠️ 진행 중 Phase 영향
  - Phase {id} (in_progress) 가 새 PLAN에서 사라졌습니다.
  - 진행 상황: 태스크 {N}개 완료 / {M}개 미완료
  계속하시겠습니까? (yes/no)
  ```
- completed Phase 삭제 시도 → 경고:
  ```
  ⚠️ 완료된 Phase 삭제: {id}
  history에 기록되며 삭제됩니다.
  ```

### Step 5 — Preview mode

`--preview` 인자 시 머지 결과를 보여만 주고 종료:

```
🔍 변경 사항 미리보기: {plan_name}

추가될 Phase ({N}개):
- Phase {id}: {name} ({tasks}개 task)

삭제될 Phase ({M}개):
- Phase {id}: {name} ({status_kr}, {completed_tasks}/{total_tasks})

수정될 Phase ({K}개):
- Phase {id}:
  태스크 {추가/삭제/변경}: ...

⚠️ 주의 사항:
- 진행 상태 보존됨: completed phase {N}개, completed task {M}개
- 진행 중 Phase 영향: ...

💡 적용: /hs:plan-redesign (--preview 빼고)
```

→ 종료. 실제 적용 안 함.

### Step 6 — Apply (preview 아닐 때)

머지된 phases 배열을 JSON으로 빌드 → stdin으로 스크립트 전달:

```json
{
  "phases": [
    {
      "id": "Phase 1-1",
      "name": "...",
      "status": "completed",            ← 보존
      "depends_on": [],
      "started_at": "...",              ← 보존
      "completed_at": "...",            ← 보존
      "paused_at": null,
      "tasks": [
        {"name": "...", "status": "completed"}  ← 태스크별 보존
      ]
    },
    ...
  ]
}
```

```bash
python {PLUGIN_ROOT}/scripts/plan_state.py apply-redesign [--plan <name>] < merged.json
```

스크립트가:
- phases 배열 교체
- revision +1
- source_hash 갱신
- plan_status 재계산
- history 추가

### Step 7 — Render apply result

```
✅ plan 재설계 완료: {plan_name}

리비전: {old_revision} → {new_revision}
Phase 수: {old_count} → {new_count}

적용된 변경:
- 추가: {added}개 Phase
- 삭제: {removed}개 Phase
- 수정: {modified}개 Phase
- 보존된 진행: completed phase {kept_completed}개, completed task {kept_tasks}개

plan 상태: {plan_status_kr}

💡 현황 확인: /hs:plan-status
```

### Step 8 — Output policy
- 적용은 atomic (스크립트 내부).
- 보고서 파일 자동 저장 안 함.

## Tool coordination
- **Read** — progress.yaml + 새 PLAN.md 읽기.
- **Bash** — `plan_state.py check-source` + `apply-redesign` 호출.
- **Write** — 임시 머지 JSON 파일 (stdin pipe 안전 처리용).

## Boundaries

**Will:**
- 진행 상태 (completed phase / completed task) **무조건 보존**.
- 위험한 변경(진행 중 Phase 삭제 등) 사용자 확인 받음.
- preview 모드로 변경 사항 미리 확인.
- atomic 적용.

**Will Not:**
- 진행 상태를 silent하게 잃지 않음.
- source 변경 없는데 강제 적용하지 않음.
- 사용자 확인 없이 위험 변경 진행하지 않음.
- progress.yaml 직접 편집 금지 (스크립트 통해서만).
- 어떤 스킬도 자동으로 호출하지 않음. 사용자 명시 호출만 진입 가능 (Mutating 스킬 — 상태 변경 작업이므로 명시 진입 필수).

## Examples

### 일반 재설계 (preview)
```
/hs:plan-redesign 미리보기
```
→ 변경 사항만 표시 + 적용 안 함.

### 적용
```
/hs:plan-redesign
```
→ 머지 + 적용 + 진행 상태 보존.

### 진행 중 Phase 삭제 시
```
/hs:plan-redesign
```
→ 경고 + 사용자 확인 → yes일 때만 진행.

## Next Step
- 변경 적용 후 → `/hs:plan-status`로 새 구조 확인
- 추가 작업 → `/hs:plan-start <phase>` 또는 `/hs:plan-run`
- 미리보기 후 적용 → `/hs:plan-redesign` (--preview 없이)
