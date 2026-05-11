---
name: plan-tasks
description: "Phase의 태스크 조회 / 개별 완료 처리 (plan-tasks, 태스크, 1번 완료, task 끝). 조회 모드 / 완료 모드 두 가지."
version: 0.1.0
---

# /hs:plan-tasks - Task Inquiry and Completion

## Operating principles
- The user's global rules in `~/.claude/CLAUDE.md` and `~/.claude/rules/*.md`
  are the authoritative persona. Follow them strictly.
- This skill provides procedural guidance only — no identity injection,
  no priority overrides.
- If guidance here conflicts with user rules, user rules win.
- Respond to the user in Korean.

## Activation guard (explicit-only)
This skill activates ONLY via explicit `/hs:plan-tasks` invocation.
- Auto-trigger: NEVER.
- Opt-out keywords still apply as a safety net:
  "스킬 쓰지 말고", "그냥 답해줘", "직접 답변", "스킬 빼고" → SKIP.

## Activation announcement
The FIRST line of every response from this skill MUST be a single-line
header in this exact format:

🔍 [hs:plan-tasks] <phase_id>[, complete <index>]

Examples:
- 🔍 [hs:plan-tasks] Phase 1-1
- 🔍 [hs:plan-tasks] Phase 1-1, complete 3

체이닝된 호출 시 (Phase 2 자동호출 활성화 후):
- Diagnostic 체이닝: 본 헤더 다음 줄에 "↳ chained from /hs:이전스킬" 추가.
- Pipeline-Stage 체이닝: 본 헤더 다음 줄에 "↳ chained from /hs:이전스킬 (pipeline)" 추가.
- 명시 호출: 추가 표기 없음.

Leave a blank line after the header, then proceed with the skill's
normal output.

## Workflow position
plan family의 태스크 단위 관리. Phase는 plan-start/complete로,
**태스크는 plan-tasks**로 다룸.

자동 실행(plan-run)이나 implement 흐름에서는 LLM이 태스크 완료를
자동 추론하므로 plan-tasks 호출 빈도는 낮음. 다만:
- 자동 추론이 틀렸을 때 교정
- 명시적으로 태스크 보고 싶을 때
- hs:implement 안 거치고 직접 코드 수정한 후 동기화

## Triggers
- "Phase X-Y 태스크 보여줘", "1번 태스크 끝났어", "task 3 완료".
- 명시 `/hs:plan-tasks <phase_id>` 호출.

## Usage
```
/hs:plan-tasks <phase_id> [--complete <index>]
```

자연어 추론:
- 첫 인자 = phase_id (필수).
- "1번 완료", "task N 끝" → `--complete N`.
- 인덱스 없이 호출 → 조회 모드.

## Behavioral Flow

### Step 1 — Invoke plan_state.py tasks
조회 모드:
```bash
python {PLUGIN_ROOT}/scripts/plan_state.py tasks <phase_id>
```

완료 모드:
```bash
python {PLUGIN_ROOT}/scripts/plan_state.py tasks <phase_id> --complete <index>
```

### Step 2 — Parse JSON

### Step 3 — Handle errors
- `plan_not_found`, `phase_not_found` → 한국어 안내.
- `task_index_invalid` → "인덱스 {idx} 무효. 범위: 1~{max}."
- `phase_status_invalid` (이미 완료된 태스크 재완료 시) → 안내.

### Step 4 — Render result

**조회 모드**:
```
📋 Phase {phase_id} 태스크 (Phase 상태: {phase_status_kr})

진행률: {bar} {percent}% ({completed}/{total})

{각 task에 대해}
{icon} [{index}] {name}
{end}
```

**Task icon 매핑**:
| status | icon |
|--------|------|
| completed | ✅ |
| pending | ⏳ |
| in_progress | 🔄 (현재는 안 씀, 향후 확장 대비) |

**완료 모드**:
```
✅ 태스크 완료: [{index}] {name}

Phase {phase_id} 진행률: {bar} {percent}% ({completed}/{total})

{if phase_complete_ready}
🎉 Phase의 모든 태스크 완료됨.
다음: /hs:plan-complete {phase_id} 로 Phase 종결.
{else}
남은 태스크: {total - completed}개
{end}
```

### Step 5 — Suggest next action
- 조회 모드 → "특정 태스크 완료: /hs:plan-tasks {phase_id} --complete N"
- 완료 모드 + phase_complete_ready → "/hs:plan-complete {phase_id}" 강조
- 완료 모드 + 미완료 남음 → "다음 태스크 작업 또는 추가 완료 처리"

## Tool coordination
- **Bash** — `plan_state.py tasks` 호출.

## Boundaries

**Will:**
- 명시된 Phase의 태스크 조회 또는 개별 완료 처리.
- Phase 모든 태스크 완료 시 plan-complete 안내.

**Will Not:**
- Phase 자체 상태 변경 안 함 (별도 plan-complete 필요).
- 이미 완료된 태스크 재처리 안 함.
- 인덱스 외 방식으로 태스크 식별 안 함 (이름 매칭 등 미지원).
- Mutating 스킬 자동 호출 금지 (implement / refactor / cleanup / document / plan-* / cl-* 등).
- Diagnostic 끼리는 사용자 체이닝 시그널 있고 opt-out 없을 때만 자동 호출 허용 (활성). 안전 쌍: analyze→explain, research→brainstorm, troubleshoot→explain.
- 자동 호출 시 activation header 에 "↳ chained from /hs:이전스킬" 표기 의무.

## Examples

### 조회
```
/hs:plan-tasks Phase 1-2
```
→ Phase 1-2 태스크 목록 + 진행률.

### 개별 완료
```
/hs:plan-tasks Phase 1-2 --complete 3
```
또는 자연어:
```
/hs:plan-tasks Phase 1-2 3번 완료
```
→ 3번 태스크 완료 처리.

### 모든 태스크 완료 후 Phase 완료
```
/hs:plan-tasks Phase 1-2 4번 완료
```
→ phase_complete_ready: true → "/hs:plan-complete Phase 1-2 권장" 안내.

## Next Step
- Phase 종결 → `/hs:plan-complete <phase_id>`
- 다음 태스크 작업 → 직접 코드 작업 후 `/hs:plan-tasks --complete N`
- 진행 확인 → `/hs:plan-status`
