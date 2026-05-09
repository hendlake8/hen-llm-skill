---
name: cl-save
description: "현재 CM Phase 수동 저장 (cl-save, 저장, 기록 저장). CHAT_LOG.md 생성 + Phase 자동 증가."
version: 0.1.0
---

# /hs:cl-save - Save Current Phase Chat Log

## Operating principles
- The user's global rules in `~/.claude/CLAUDE.md` and `~/.claude/rules/*.md`
  are the authoritative persona. Follow them strictly.
- This skill provides procedural guidance only — no identity injection,
  no priority overrides.
- If guidance here conflicts with user rules, user rules win.
- Respond to the user in Korean.

## Activation guard (explicit-only)
This skill activates ONLY via explicit `/hs:cl-save` invocation.
- Auto-trigger: NEVER.
- Opt-out keywords still apply as a safety net:
  "스킬 쓰지 말고", "그냥 답해줘", "직접 답변", "스킬 빼고" → SKIP.

## Activation announcement
The FIRST line of every response from this skill MUST be a single-line
header in this exact format:

🔍 [hs:cl-save] <topic>, Phase {NN}

Example:
- 🔍 [hs:cl-save] API 리팩토링, Phase 02

Leave a blank line after the header, then proceed with the skill's
normal output.

## Workflow position

CM family에서 **현재 Phase의 대화 기록을 CHAT_LOG.md로 저장** + Phase
번호 자동 증가. 보통 `/compact` 직전에 호출.

```
... Phase N 작업 ...
/hs:context-status      (선택적 점검)
/hs:cl-save             ← 여기 (Phase N 저장, Phase N+1 자동 시작)
/compact                (사용자 직접)
... Phase N+1 작업 ...
```

## Triggers
- "기록 저장", "지금까지 저장", "compact 전에 저장".
- 명시 `/hs:cl-save` 호출.

## Usage
```
/hs:cl-save [topic]
```

자연어 추론:
- 인자 생략 → 현재 활성 토픽 자동 식별.
- 명시 → 그 토픽 (단, 보통 활성 토픽 1개라 생략이 자연스러움).

## Behavioral Flow

### Step 1 — Invoke cm_state.py save

```bash
python {PLUGIN_ROOT}/scripts/cm_state.py save [topic]
```

### Step 2 — Parse JSON

### Step 3 — Handle errors

| code | 한국어 안내 |
|------|----------|
| `no_active_session` | "활성 CM 세션 없음. /hs:cl-start로 먼저 시작." |
| `topic_not_found` | "토픽 '{topic}' 없음. /hs:cl-list로 확인." |
| `session_inactive` | "토픽 비활성 상태. 새로 시작하려면 /hs:cl-start." |
| `state_corrupt` | "상태 파일 손상. 수동 정리 필요: .hs/{user}/CM/{topic}/" |
| `session_not_found` | "Claude Code 세션 JSONL 없음. 환경 점검 필요." |

### Step 4 — Render success

```
✅ Phase {saved_phase:02d} 저장 완료

- 토픽: {topic}
- 사용자: {user}
- 파일: {chat_log_path}
- 메시지 수: {messages_written}
- 크기: {file_size_bytes:,} bytes

🔄 Phase {next_phase:02d} 자동 시작됨
- 시작 시각: {next_phase_started_at}

💡 다음 단계:
- /compact 입력 권장 (컨텍스트 정리)
- 작업 계속 → 다음 Phase에서 자동 추적
- 종료 시 → /hs:cl-end
```

### Step 5 — Output policy
- 파일 생성은 스크립트가 atomic 처리.
- `/compact`는 사용자가 직접 입력 (스킬이 안 함).
- 다른 스킬 자동 호출 안 함.

## Tool coordination
- **Bash** — `cm_state.py save` 호출.

## Boundaries

**Will:**
- 현재 Phase의 대화 기록을 CHAT_LOG.md로 저장.
- 저장 후 Phase 번호 자동 증가 + 새 Phase 시작 시각 기록.
- 사용자 활성 토픽 자동 식별 (인자 생략 가능).

**Will Not:**
- `/compact` 자동 입력 안 함 (사용자 직접).
- BRIEF / REPORT 생성 안 함 (옵션 C — cl만).
- 활성 세션 없으면 강제로 만들지 않음.
- 다른 스킬 자동 호출.

## Examples

### 활성 세션 자동 저장
```
/hs:cl-save
```
→ 현재 활성 토픽의 현재 Phase 저장 + 다음 Phase 자동 시작.

### 명시적 토픽
```
/hs:cl-save "API 리팩토링"
```
→ 해당 토픽 저장 (다른 활성 세션과 다른 토픽은 거의 없는 케이스).

## Next Step
- `/compact` 입력 (사용자 직접) — 컨텍스트 정리
- 작업 계속 → 다음 Phase에서 자동 기록
- 작업 종료 → `/hs:cl-end`
- 진행 확인 → `/hs:context-status`
