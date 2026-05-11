---
name: context-status
description: "현재 세션 컨텍스트 / 토큰 사용량 측정 (context-status, 컨텍스트 사용량, 얼마나 찼지, 토큰). JSONL 파싱 기반 정확 측정. read-only."
version: 0.1.0
---

# /hs:context-status - Session Context Usage Inquiry

## Operating principles
- The user's global rules in `~/.claude/CLAUDE.md` and `~/.claude/rules/*.md`
  are the authoritative persona. Follow them strictly.
- This skill provides procedural guidance only — no identity injection,
  no priority overrides.
- If guidance here conflicts with user rules, user rules win.
- Respond to the user in Korean.

## Activation guard (explicit-only)
This skill activates ONLY via explicit `/hs:context-status` invocation.
- Auto-trigger: NEVER. 사용자가 컨텍스트 상황을 묻고 싶을 때 명시 호출.
- Opt-out keywords still apply as a safety net:
  "스킬 쓰지 말고", "그냥 답해줘", "직접 답변", "스킬 빼고" → SKIP.

## Activation announcement
The FIRST line of every response from this skill MUST be a single-line
header in this exact format:

🔍 [hs:context-status] <usage_percent>% (<method>)

Examples:
- 🔍 [hs:context-status] 64.0% (jsonl_parse)
- 🔍 [hs:context-status] N/A (fallback)

체이닝된 호출 시 (Phase 2 자동호출 활성화 후):
- Diagnostic 체이닝: 본 헤더 다음 줄에 "↳ chained from /hs:이전스킬" 추가.
- Pipeline-Stage 체이닝: 본 헤더 다음 줄에 "↳ chained from /hs:이전스킬 (pipeline)" 추가.
- 명시 호출: 추가 표기 없음.

Leave a blank line after the header, then proceed with the skill's
normal output.

## Triggers
- "컨텍스트 얼마나 찼지", "지금 사용량", "토큰 얼마나 썼지".
- 수동으로 cl-save 결정 전 확인.
- 명시 `/hs:context-status` 호출.

## Usage
```
/hs:context-status
```

(인자 없음. 현재 cwd 기준 세션 측정.)

## Behavioral Flow

### Step 1 — Invoke context_usage.py

```bash
python {PLUGIN_ROOT}/scripts/context_usage.py
```

`{PLUGIN_ROOT}` 1회 탐색 (다른 hs와 동일 패턴):
```bash
find ~/.claude/plugins -path "*hs/scripts/context_usage.py" 2>/dev/null | head -1
```

### Step 2 — Parse JSON

응답 예시 (정상):
```json
{
  "ok": true,
  "method": "jsonl_parse",
  "session_id": "...",
  "model": "claude-opus-4-7",
  "context_limit": 1000000,
  "tokens": {
    "input": ..., "cache_creation": ..., "cache_read": ...,
    "total_context": 640233, "output_last_turn": ...
  },
  "usage_percent": 64.0,
  "near_limit": false,
  "message_count": 642
}
```

응답 예시 (fallback):
```json
{
  "ok": true,
  "method": "fallback_estimate",
  "fallback_reason": "...",
  "fallback_notice": "정확한 측정 불가 — JSONL 파싱 실패..."
}
```

### Step 3 — Render Korean report

#### 정상 측정 (`method: jsonl_parse`)

```
📊 컨텍스트 사용량

진행률: {bar 20칸} {percent}%
- 사용: {total_context:,} / {context_limit:,} 토큰
- 모델: {model}
- 메시지 수: {message_count}

토큰 분해:
- 신규 입력: {input:,}
- 캐시 생성: {cache_creation:,}
- 캐시 읽기: {cache_read:,}
- 직전 출력: {output_last_turn:,}

{if near_limit (>=80%)}
⚠️ 80% 임계 도달 — /hs:cl-save 또는 /compact 권장.
{end}

세션: {session_id}
```

**진행률 바**: 20칸, `█`/`░`. 다른 hs 스킬과 일관.

#### Fallback (`method: fallback_estimate`)

```
⚠️ 컨텍스트 측정 불가 — 추정 모드

이유: {fallback_reason}

가능한 원인:
- Claude Code JSONL 포맷 변경
- 세션 디렉토리 위치 변경
- 현재 세션 신규 (메시지 부족)

대처:
- 잠시 후 재시도 (메시지 누적 후)
- 직접 확인: ~/.claude/projects/<프로젝트키>/ 폴더 확인
```

### Step 4 — Suggest action

| 상태 | 안내 |
|------|------|
| `usage_percent < 50%` | "여유 있음, 계속 작업 가능" |
| `50% ≤ percent < 80%` | "보통 사용량, 곧 점검 권장" |
| `percent ≥ 80%` (`near_limit`) | "임계 도달 — `/hs:cl-save` 후 `/compact` 강력 권장" |
| fallback | 측정 불가 안내만 |

## Output policy

**모든 출력 끝에 표준 `## Skill Output Metadata` appendix 의무** — Collected Facts (3-5 fact) + Next Skill Hints. 다음 스킬이 fact 재수집 회피 + 체이닝 시그널 명시 (HSPOLICY_DESIGN 의 "Fact 공유 — Output appendix 강제 규약" 절 참조). **직전 스킬의 appendix 가 있으면 본 스킬 입력으로 우선 사용** — 같은 fact 재수집 회피.
- 대화 전용. 파일 저장 안 함.
- 어떤 상태도 변경하지 않음 (read-only).

## Tool coordination
- **Bash** — `context_usage.py` 호출.

## Boundaries

**Will:**
- 현재 세션 컨텍스트 / 토큰 사용량 정확 측정 (JSONL 기반).
- 측정 실패 시 fallback으로 명시.
- 임계 도달 시 후속 액션 안내.

**Will Not:**
- 어떤 상태도 변경 (read-only).
- /compact 또는 cl-save 자동 호출.
- Mutating 스킬 자동 호출 금지 (implement / refactor / cleanup / document / plan-* / cl-* 등).
- Diagnostic 끼리는 사용자 체이닝 시그널 있고 opt-out 없을 때만 자동 호출 허용 (활성). 안전 쌍: analyze→explain, research→brainstorm, troubleshoot→explain.
- 자동 호출 시 activation header 에 "↳ chained from /hs:이전스킬" 표기 의무.
- fallback 모드에서 추정치를 단정으로 표현.

## Examples

### 기본 조회
```
/hs:context-status
```
→ 진행률 바 + 토큰 분해 + 안내.

### 임계 근접 시
```
/hs:context-status
```
→ 84% 표시 + "/hs:cl-save 후 /compact 권장" 강조.

### 측정 실패 시 (예: JSONL 미발견)
```
/hs:context-status
```
→ "추정 모드" 명시 + 원인 추정.

## Next Step
사용자 결정. 보통:
- 컨텍스트 여유 → 작업 계속
- 임계 도달 → `/hs:cl-save` (대화 기록) → `/compact`
- CM 세션 시작하려면 → `/hs:cl-start "주제"`

This skill takes no further action automatically.
