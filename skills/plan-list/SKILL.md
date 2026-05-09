---
name: plan-list
description: "등록된 모든 plan 목록 조회 (plan-list, 목록, 등록된 plan, 어떤 plan들 있어). 활성/완료/대기 표시."
version: 0.1.0
---

# /hs:plan-list - Registered Plans Inquiry

## Operating principles
- The user's global rules in `~/.claude/CLAUDE.md` and `~/.claude/rules/*.md`
  are the authoritative persona. Follow them strictly.
- This skill provides procedural guidance only — no identity injection,
  no priority overrides.
- If guidance here conflicts with user rules, user rules win.
- Respond to the user in Korean.

## Activation guard (explicit-only)
This skill activates ONLY via explicit `/hs:plan-list` invocation.
- Auto-trigger: NEVER. 사용자가 "어떤 plan들 있어" 같은 표현을 써도
  슬래시 명령 없이는 발동하지 않음. 일반 답변 또는 명령 안내.
- Opt-out keywords still apply as a safety net:
  "스킬 쓰지 말고", "그냥 답해줘", "직접 답변", "스킬 빼고" → SKIP.

## Activation announcement
The FIRST line of every response from this skill MUST be a single-line
header in this exact format:

🔍 [hs:plan-list] <plan count>

Examples:
- 🔍 [hs:plan-list] 3개 plan
- 🔍 [hs:plan-list] 등록된 plan 없음

Leave a blank line after the header, then proceed with the skill's
normal output.

## Workflow position
plan family의 read-only 조회 명령. 상태 변경 없음.

## Triggers
- "plan 목록", "어떤 plan 있지", "등록된 거 보여줘".
- 명시 `/hs:plan-list` 호출.

## Usage
```
/hs:plan-list
```

(인자 없음. 모든 plan 표시.)

## Behavioral Flow

### Step 1 — Invoke plan_state.py list
```bash
python {PLUGIN_ROOT}/scripts/plan_state.py list
```

`{PLUGIN_ROOT}` 1회 탐색:
```bash
find ~/.claude/plugins -path "*hs/scripts/plan_state.py" 2>/dev/null | head -1
```

### Step 2 — Parse JSON
응답 형식: `{"ok": true, "current_plan": "...", "plans": [...]}`

### Step 3 — Handle errors
`"ok": false` 시 한국어 안내 후 종료.

### Step 4 — Render Korean report

`plans`가 비어있으면:
```
📚 등록된 plan 없음.

💡 plan 등록: /hs:plan-load <PLAN.md 경로>
```

`plans`가 있으면:
```
📚 등록된 plan 목록 ({N}개)

{plan별로}
{plan icon} {name}{ (활성) if is_current}
   진행률: {bar 20칸} {percent}% ({completed}/{total} Phase)
   plan 상태: {plan_status_kr}
   소스: {source}
   등록일: {registered_at의 날짜 부분}
   {if completed_at} 완료일: {completed_at의 날짜 부분}
   {if auto_run_active} ⚙️ auto-run 진행 중
```

**Plan icon 매핑**:
| 조건 | icon |
|------|------|
| `is_current == true` | 🔵 |
| `plan_status == "completed"` | ✅ |
| `auto_run_active == true` | ⚙️ (아이콘 보강) |
| 그 외 | ⚪ |

(여러 조건 겹치면 우선순위: completed > current > auto-run)

**진행률 바**: 20칸, `█`/`░`.

**plan_status 한국어 매핑**:
| status | text |
|--------|------|
| pending | 대기 |
| in_progress | 진행 중 |
| completed | 완료 |

### Step 5 — Suggest next action
- 활성 plan 있음 → "현재 활성: {name}. 진행 보려면 /hs:plan-status"
- 완료된 plan만 있음 → "정리: /hs:plan-unload <name>"
- plan 0개 → "/hs:plan-load로 등록"

## Tool coordination
- **Bash** — `plan_state.py list` 호출.

## Boundaries

**Will:**
- 등록된 모든 plan을 한 번에 표시.
- 활성/완료/auto-run 상태 시각적 구분.

**Will Not:**
- 어떤 상태도 변경하지 않음.
- 결과를 파일로 저장하지 않음.
- 다른 스킬 자동 호출.

## Examples

### 기본 조회
```
/hs:plan-list
```
→ 모든 plan 요약 표시.

## Next Step
사용자 결정. 보통:
- 활성 plan 진행 → `/hs:plan-status`
- 다른 plan으로 전환 → `/hs:plan-load <path>` (재 load가 switch 역할)
- 정리 → `/hs:plan-unload <name>`
