---
name: cl-start
description: "CM 채팅 로깅 세션 시작 (cl-start, 시작, 기록 시작). 토픽별 폴더 생성 + 사용자 격리 (.hs/{user}/CM/{topic}/)."
version: 0.1.0
---

# /hs:cl-start - Begin Chat Logging Session

## Operating principles
- The user's global rules in `~/.claude/CLAUDE.md` and `~/.claude/rules/*.md`
  are the authoritative persona. Follow them strictly.
- This skill provides procedural guidance only — no identity injection,
  no priority overrides.
- If guidance here conflicts with user rules, user rules win.
- Respond to the user in Korean.

## Activation guard (explicit-only)
This skill activates ONLY via explicit `/hs:cl-start` invocation.
- Auto-trigger: NEVER. 폴더 생성 동반 → 사용자 명시 호출 필수.
- Opt-out keywords still apply as a safety net:
  "스킬 쓰지 말고", "그냥 답해줘", "직접 답변", "스킬 빼고" → SKIP.

## Activation announcement
The FIRST line of every response from this skill MUST be a single-line
header in this exact format:

🔍 [hs:cl-start] <topic> ({user})

Example:
- 🔍 [hs:cl-start] API 리팩토링 (hendlake)

체이닝된 호출 시 (Phase 2 자동호출 활성화 후):
- Diagnostic 체이닝: 본 헤더 다음 줄에 "↳ chained from /hs:이전스킬" 추가.
- Pipeline-Stage 체이닝: 본 헤더 다음 줄에 "↳ chained from /hs:이전스킬 (pipeline)" 추가.
- 명시 호출: 추가 표기 없음.

Leave a blank line after the header, then proceed with the skill's
normal output.

## Workflow position

CM (Chat Logging) family의 진입점. 단일 채널, 수동 통제.

```
/hs:cl-start "주제"     ← 여기 (세션 시작, 폴더 생성)
... 작업 진행 ...
/hs:context-status      (필요 시 사용량 점검)
/hs:cl-save             (수동 저장)
/compact                (사용자 직접 입력)
... 다음 Phase ...
/hs:cl-end              (작업 종료)
```

저장 위치: `.hs/{user}/CM/{topic}/`
- `{user}`: git user.name → OS 사용자 (자동 추출, sanitized)
- `{topic}`: 사용자 명시 토픽명 (sanitized)

## Triggers
- "CM 시작", "기록 시작", "이거 기록하면서 가자".
- 명시 `/hs:cl-start <topic>` 호출.

## Usage
```
/hs:cl-start "<주제명>"
```

토픽명 필수. 한국어 / 영어 / 숫자 / 공백 허용 (sanitization 거침).

## Behavioral Flow

### Step 1 — Invoke cm_state.py start

```bash
python {PLUGIN_ROOT}/scripts/cm_state.py start "<topic>"
```

### Step 2 — Parse JSON

### Step 3 — Handle errors

| code | 한국어 안내 |
|------|----------|
| `invalid_input` | "토픽명 비어있거나 무효함. 의미 있는 이름으로 재시도." |
| `another_session_active` | "이미 활성 CM 세션 있음: '{active_topic}'. 먼저 /hs:cl-end로 종료 후 시작." |
| `already_active` | "토픽 '{topic}' 이미 활성. 추가 동작 불필요." |
| `topic_exists_inactive` | "토픽 '{topic}' 이미 등록됨 (비활성). {hint}" |

### Step 4 — Render success

```
🚀 CM 세션 시작: {topic}

- 사용자: {user} ({user_source})
- 출력 경로: {output_dir}
- Phase: 01
- 세션 ID: {session_id}

{if session_id_warning}
⚠️ {session_id_warning}
{end}

💡 다음 단계:
- 작업 진행 중 컨텍스트 점검: /hs:context-status
- 수동 저장: /hs:cl-save
- 종료: /hs:cl-end
```

### Step 5 — Output policy
- 폴더 / state 파일 생성은 스크립트가 atomic 처리.
- 다른 파일 수정 안 함.

## Tool coordination
- **Bash** — `cm_state.py start` 호출.

## Boundaries

**Will:**
- 토픽별 폴더 생성 (`.hs/{user}/CM/{topic}/`).
- 사용자 격리 (git user.name → OS 사용자).
- 상호 배타 강제 (다른 활성 세션 있으면 거부).
- 세션 ID 자동 추출 (현재 Claude Code 세션).

**Will Not:**
- 다른 활성 세션 무시하고 강제 시작 안 함.
- 기존 비활성 토픽 자동 재활성화 안 함 (사용자 수동 정리 필요).
- 자동 저장 hook 등록 안 함 (옵션 C — 완전 수동).
- 어떤 스킬도 자동으로 호출하지 않음. 사용자 명시 호출만 진입 가능 (Mutating 스킬 — 상태 변경 작업이므로 명시 진입 필수).

## Examples

### 표준 시작
```
/hs:cl-start "API 리팩토링"
```
→ `.hs/hendlake/CM/API 리팩토링/` 폴더 + Phase_01/ + CM_STATE.json 생성.

### 한국어 토픽
```
/hs:cl-start "전투 시스템 R&D"
```
→ 한국어 토픽명 그대로 사용.

### 다른 세션 활성 시
```
/hs:cl-start "새 토픽"
```
→ 에러: "이미 활성 CM 세션 있음. 먼저 /hs:cl-end."

## Next Step
- 작업 진행
- 컨텍스트 점검 → `/hs:context-status`
- 수동 저장 → `/hs:cl-save`
- 종료 → `/hs:cl-end`
