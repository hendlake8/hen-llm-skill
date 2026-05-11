---
name: plan-status
description: "활성 plan의 진행 현황 조회 (plan status, 현황, 진행률, 어디까지 했지, 다음 작업). 다음 작업 안내 자동 포함 (plan-next 흡수)."
version: 0.1.0
---

# /hs:plan-status - Plan Progress Inquiry

## Operating principles
- The user's global rules in `~/.claude/CLAUDE.md` and `~/.claude/rules/*.md`
  are the authoritative persona. Follow them strictly.
- This skill provides procedural guidance only — no identity injection,
  no priority overrides.
- If guidance here conflicts with user rules, user rules win.
- Respond to the user in Korean.

## Activation guard (explicit-only)
This skill activates ONLY via explicit `/hs:plan-status` invocation.
- Auto-trigger: NEVER. Even if the user mentions "plan 진행 상황",
  "어디까지 했지" etc. without invoking the slash command, do NOT
  activate. Respond as a normal assistant or suggest the command.
- Opt-out keywords still apply as a safety net:
  "스킬 쓰지 말고", "그냥 답해줘", "직접 답변", "스킬 빼고" → SKIP.

## Activation announcement
The FIRST line of every response from this skill MUST be a single-line
header in this exact format:

🔍 [hs:plan-status] <plan name>[, --detail]

Examples:
- 🔍 [hs:plan-status] Combat
- 🔍 [hs:plan-status] Combat, --detail
- 🔍 [hs:plan-status] (no active plan)

체이닝된 호출 시 (Phase 2 자동호출 활성화 후):
- Diagnostic 체이닝: 본 헤더 다음 줄에 "↳ chained from /hs:이전스킬" 추가.
- Pipeline-Stage 체이닝: 본 헤더 다음 줄에 "↳ chained from /hs:이전스킬 (pipeline)" 추가.
- 명시 호출: 추가 표기 없음.

Leave a blank line after the header, then proceed with the skill's
normal output.

## Workflow position

This skill is part of the `plan` family. The chain:

```
brainstorm → design → workflow → /hs:document → /hs:plan-load → ... → implement
                                                  ↓
                                              plan-* family
                                              (start / pause / complete /
                                               rollback / tasks / status / etc.)
```

`plan-status` is the read-only inquiry. It does NOT change state.

## Scope definition

### What this skill does
- Read the current plan's `progress.yaml` via `plan_state.py status`.
- Render a Korean-language progress report (overall percent, phase list,
  current phase, next suggested action, auto-run state).
- Suggest the next concrete `/hs:plan-*` command based on state.

### What this skill does NOT do
- Modify any state.
- Save reports to files (use `/hs:document` if user wants persistence).
- Trigger other skills.

## Triggers
- Plan progress inquiries ("plan 어디까지 했지", "현황", "진행률").
- "다음 뭐 해야 해?" — answered automatically (plan-next 흡수).
- Explicit `/hs:plan-status` invocation.

## Usage
```
/hs:plan-status [plan_name] [--detail]
```

자연어 추론:
- `[plan_name]` 생략 → `state.yaml`의 `current_plan` 사용. 명시 시 그 plan 대상.
- "자세히", "디테일", "태스크까지" → `--detail` 추론.

## Inferring intent from natural language

### Plan target
- 인자에 plan 이름 명시 → 그 plan.
- 생략 → `current_plan`. 없으면 단일 plan 폴더가 있으면 그걸로 자동.
- 둘 다 안 되면 에러 (plan_not_found).

### Detail level
- "자세히", "태스크까지", "디테일", "전부" → `--detail` 추가.
- 기본 → Phase 단위 요약만.

## Behavioral Flow

### Step 1 — Invoke plan_state.py status
Use Bash to call the script:

```bash
python {PLUGIN_ROOT}/scripts/plan_state.py status [--plan <name>] [--detail]
```

`{PLUGIN_ROOT}` resolution:
- 일반적으로 `~/.claude/plugins/.../hs/` 경로.
- 알 수 없는 경우 1회 탐색:
  ```bash
  find ~/.claude/plugins -path "*hs/scripts/plan_state.py" 2>/dev/null | head -1
  ```
  결과를 그 세션 동안 재사용.

### Step 2 — Parse JSON
Script always returns `{"ok": true|false, ...}` JSON to stdout.

### Step 3 — Handle errors
If `"ok": false`:
- `plan_not_found` → 사용자에게 한국어로 안내. plan-load 또는 plan-list 권장.
- 기타 에러 → `code` + `message`를 한국어 친화적으로 전달.
- 종료. 더 진행하지 않음.

### Step 4 — Render Korean report

성공 시 다음 형식으로 출력:

```
📊 {plan name} 진행 현황

진행률: {progress bar 20칸} {percent}% ({completed}/{total} Phase)
plan 상태: {plan_status} (pending / 진행 중 / 완료)

Phase 목록:
{각 Phase에 대해}
{icon} Phase X-Y: {name}    {status_text} ({tasks_summary})
   ↑ depends_on이 있으면 (→ {dep_id} 완료 필요) 같은 부연
```

**진행률 바**:
- 20칸 기준
- 채움: `█` (U+2588)
- 빈칸: `░` (U+2591)
- 예: `██████████░░░░░░░░░░ 50%`

**Status 아이콘 매핑**:
| status | icon | 한국어 |
|--------|------|-------|
| completed | ✅ | 완료 |
| in_progress | 🔄 | 진행 중 |
| pending | ⏳ | 대기 |
| paused | ⏸️ | 일시정지 |
| blocked | 🚫 | 차단 |

**`--detail`인 경우**: 각 Phase 아래에 태스크 리스트도 표시:
```
✅ Phase 1-1: 데이터 모델 (완료, 5/5)
   ├── ✅ Player 클래스
   ├── ✅ Inventory 인터페이스
   └── ✅ Save 데이터 직렬화
🔄 Phase 1-2: 코어 로직 (진행 중, 2/4)
   ├── ✅ ...
   ├── ✅ ...
   ├── 🔄 ... ← 현재 작업
   └── ⏳ ...
```

### Step 5 — Suggest next action (plan-next 흡수)

JSON의 `current_phase`, `next_suggested`, `auto_run.active` 활용:

| 상태 | 안내 |
|------|------|
| `current_phase != null` | "현재 작업: {phase}. 태스크 진행은 /hs:plan-tasks {phase} 또는 완료 시 /hs:plan-complete {phase}" |
| `current_phase == null && next_suggested != null` | "다음 추천: /hs:plan-start {next_suggested}" |
| `plan_status == "completed"` | "🎉 plan 완료. /hs:plan-unload로 정리 또는 새 plan-load." |
| `auto_run.active == true` | 추가로 "⚙️ auto-run 진행 중 (시작: {started_at})" 표시 |

### Step 6 — Output policy
- 결과는 대화로만. 파일 저장 안 함.
- 사용자가 "저장해줘" 명시하면 `/hs:document` 안내.

## Tool coordination
- **Bash** — `plan_state.py status` 호출.
- 그 외 도구 사용 안 함.

## Boundaries

**Will:**
- 현재 plan 진행 현황을 한국어로 깔끔하게 표시.
- 다음 추천 명령 자동 안내 (plan-next 기능 흡수).
- `--detail` 시 태스크 단위까지 표시.

**Will Not:**
- 어떤 상태도 변경하지 않음 (read-only).
- 결과를 파일로 저장하지 않음.
- Mutating 스킬 자동 호출 금지 (implement / refactor / cleanup / document / plan-* / cl-* 등).
- Diagnostic 끼리는 사용자 체이닝 시그널 있고 opt-out 없을 때만 자동 호출 허용 (활성). 안전 쌍: analyze→explain, research→brainstorm, troubleshoot→explain.
- 자동 호출 시 activation header 에 "↳ chained from /hs:이전스킬" 표기 의무.
- 페르소나 주입 / 사용자 룰 무시.

## Examples

### 기본 조회
```
/hs:plan-status
```
→ current_plan의 Phase 단위 진행 현황 + 다음 작업 안내.

### 특정 plan 조회
```
/hs:plan-status Inventory
```
→ Inventory plan의 현황. current_plan 영향 없음.

### 디테일
```
/hs:plan-status 자세히
```
→ 자연어로 `--detail` 추론. 태스크 단위까지 표시.

### plan 없을 때
```
/hs:plan-status
```
→ "plan_not_found" → "활성 plan 없음. /hs:plan-load <PLAN.md> 먼저 실행."

## Next Step
사용자 결정. 보통 다음 중 하나:
- 진행 중인 Phase의 태스크 작업 → `/hs:plan-tasks {phase}`
- Phase 완료 처리 → `/hs:plan-complete {phase}`
- 다음 Phase 시작 → `/hs:plan-start {next_suggested}`
- 자동 실행 → `/hs:plan-run`
- 일시정지 → `/hs:plan-pause`

This skill takes no further action automatically.
