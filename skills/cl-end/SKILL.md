---
name: cl-end
description: "CM 채팅 로깅 세션 종료 (cl-end, 종료, 끝, 마무리). 마지막 Phase 저장 + active=false."
version: 0.1.0
---

# /hs:cl-end - End Chat Logging Session

## Operating principles
- The user's global rules in `~/.claude/CLAUDE.md` and `~/.claude/rules/*.md`
  are the authoritative persona. Follow them strictly.
- This skill provides procedural guidance only — no identity injection,
  no priority overrides.
- If guidance here conflicts with user rules, user rules win.
- Respond to the user in Korean.

## Activation guard (explicit-only)
This skill activates ONLY via explicit `/hs:cl-end` invocation.
- Auto-trigger: NEVER.
- Opt-out keywords still apply as a safety net:
  "스킬 쓰지 말고", "그냥 답해줘", "직접 답변", "스킬 빼고" → SKIP.

## Activation announcement
The FIRST line of every response from this skill MUST be a single-line
header in this exact format:

🔍 [hs:cl-end] <topic>, Phase {NN} (final)

Example:
- 🔍 [hs:cl-end] API 리팩토링, Phase 03 (final)

Leave a blank line after the header, then proceed with the skill's
normal output.

## Workflow position

CM 세션 종결. 마지막 Phase 저장 + state의 active=false. 이후 같은
토픽으로 다시 시작하려면 별도 토픽 / 수동 정리 필요.

```
... 작업 진행 ...
/hs:cl-save         (중간 저장, 여러 번 가능)
... 더 작업 ...
/hs:cl-end          ← 여기 (마지막 Phase 저장 + 종료)
```

## Triggers
- "기록 종료", "CM 끝", "마무리".
- 명시 `/hs:cl-end` 호출.

## Usage
```
/hs:cl-end [topic]
```

자연어 추론:
- 인자 생략 → 현재 활성 토픽.
- 명시 → 그 토픽.

## Behavioral Flow

### Step 1 — Invoke cm_state.py end

```bash
python {PLUGIN_ROOT}/scripts/cm_state.py end [topic]
```

### Step 2 — Parse JSON

### Step 3 — Handle errors

| code | 한국어 안내 |
|------|----------|
| `no_active_session` | "활성 CM 세션 없음. 종료할 세션 없음." |
| `topic_not_found` | "토픽 없음." |
| `session_inactive` | "세션 이미 비활성." |
| `session_not_found` | "Claude Code 세션 JSONL 없음. 환경 점검 필요." |

### Step 4 — Render success

```
🏁 CM 세션 종료: {topic}

- 사용자: {user}
- 마지막 Phase: {saved_phase:02d}
- 마지막 파일: {chat_log_path}
- 메시지 수: {messages_written}
- 크기: {file_size_bytes:,} bytes
- 종료 시각: {ended_at}
- 마지막 Phase 작업 시간: {duration_human}

📊 마지막 Phase 토큰 (모델: {tokens.model})
- 입력: {tokens.input:,} / 출력: {tokens.output:,}
- 캐시 생성: {tokens.cache_creation:,} / 캐시 읽기: {tokens.cache_read:,}

📈 세션 누적 (session_summary)
- 총 작업 시간: {session_summary.totalDurationSeconds}초
  ({session_summary.totalDurationSeconds → format_duration})
- Phase 수: {session_summary.phaseCount} (완료 {session_summary.completedPhases})
- 총 토큰:
  - 입력: {session_summary.totalTokens.input:,}
  - 출력: {session_summary.totalTokens.output:,}
  - 캐시 생성: {session_summary.totalTokens.cacheCreation:,}
  - 캐시 읽기: {session_summary.totalTokens.cacheRead:,}
- 사용 모델: {session_summary.models join ", "}

📁 보존된 기록:
.hs/{user}/CM/{topic}/
├── CM_STATE.json
├── Phase_01/CHAT_LOG.md
├── Phase_02/CHAT_LOG.md
└── Phase_{saved_phase:02d}/CHAT_LOG.md

💡 다음 단계 (사용자 결정):
- 새 세션 시작 → /hs:cl-start "다른 주제"
- 기록 검토 → 위 폴더 직접 열어보기
- 정리 → 폴더 수동 삭제 (필요 시)
```

**렌더링 주의**:
- `session_summary.totalDurationSeconds` 는 초 단위 정수. 사람 읽기용으로 "1시간 5분 30초" 식 변환 (cm_state.format_duration 과 동일 규칙).
- `tokens.model` 이 `"mixed"` 면 그대로 노출.
- `tokens.partial == true` 이면 모델명 옆에 "— partial" 표시.
- `models` 가 빈 배열이면 "(미측정)" 표시.

### Step 5 — Output policy
- 마지막 Phase의 CHAT_LOG.md 작성 + active=false.
- 폴더 / 기존 파일 삭제 안 함 (보존).
- 다른 스킬 자동 호출 안 함.

## Tool coordination
- **Bash** — `cm_state.py end` 호출.

## Boundaries

**Will:**
- 마지막 Phase의 대화 기록 저장.
- 세션 active=false 마킹 (이후 cl-save / cl-end 호출 불가).
- 활성 토픽 자동 식별 (인자 생략 가능).

**Will Not:**
- 폴더 / 파일 자동 삭제 안 함 (보존이 default).
- `/compact` 자동 입력 안 함.
- 종료 후 다른 세션 자동 시작 안 함.
- 다른 스킬 자동 호출.

## Examples

### 활성 세션 종료
```
/hs:cl-end
```
→ 활성 토픽의 마지막 Phase 저장 + 종료.

### 명시적 토픽 종료
```
/hs:cl-end "API 리팩토링"
```
→ 해당 토픽 종료.

## Next Step
- 새 작업 시작 → `/hs:cl-start "새 주제"`
- 기존 기록 검토 → `.hs/{user}/CM/{topic}/` 직접 확인
- (선택) 폴더 정리 → 수동 삭제

This skill takes no further action automatically.
