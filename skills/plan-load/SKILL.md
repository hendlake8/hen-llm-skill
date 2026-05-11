---
name: plan-load
description: "PLAN.md 파일 파싱 후 plan 등록 (plan-load, 등록, 시작할 PLAN). 같은 명령으로 재 load = 활성 plan 전환 효과."
version: 0.1.0
---

# /hs:plan-load - Parse PLAN.md and Register

## Operating principles
- The user's global rules in `~/.claude/CLAUDE.md` and `~/.claude/rules/*.md`
  are the authoritative persona. Follow them strictly.
- This skill provides procedural guidance only — no identity injection,
  no priority overrides.
- If guidance here conflicts with user rules, user rules win.
- Respond to the user in Korean.

## Activation guard (explicit-only)
This skill activates ONLY via explicit `/hs:plan-load` invocation.
- Auto-trigger: NEVER. 파일 등록 = 사용자 의도 명확해야 함.
- Opt-out keywords still apply as a safety net:
  "스킬 쓰지 말고", "그냥 답해줘", "직접 답변", "스킬 빼고" → SKIP.

## Activation announcement
The FIRST line of every response from this skill MUST be a single-line
header in this exact format:

🔍 [hs:plan-load] <plan name> ← <PLAN.md path>

Examples:
- 🔍 [hs:plan-load] Combat ← Docs/DEVELOPMENT/Dev/Combat/COMBAT_PLAN.md
- 🔍 [hs:plan-load] StockApp ← /tmp/stock_plan.md

체이닝된 호출 시 (Phase 2 자동호출 활성화 후):
- Diagnostic 체이닝: 본 헤더 다음 줄에 "↳ chained from /hs:이전스킬" 추가.
- Pipeline-Stage 체이닝: 본 헤더 다음 줄에 "↳ chained from /hs:이전스킬 (pipeline)" 추가.
- 명시 호출: 추가 표기 없음.

Leave a blank line after the header, then proceed with the skill's
normal output.

## Workflow position

`plan-load`는 **plan family의 진입점**. 마크다운 PLAN을 시스템에
등록해서 이후 plan-* 명령들이 추적 가능하게 만듦.

```
workflow → /hs:document → *_PLAN.md 저장
                              ↓
                          plan-load 등록 ← (여기)
                              ↓
                          plan-start / plan-run / plan-status / ...
```

같은 명령으로 다른 PLAN.md를 load하면 **자동으로 current_plan 전환**
(plan-switch 역할 통합).

## Triggers
- "이 PLAN 등록해줘", "/PLAN.md 시작하자", "plan 불러와".
- 명시 `/hs:plan-load <path>` 호출.

## Usage
```
/hs:plan-load <PLAN.md path> [plan_name]
```

자연어 추론:
- 첫 인자 = PLAN.md 파일 경로 (필수).
- 둘째 인자 (선택) = plan 이름 override. 생략 시 자동 추론.
- "Combat plan으로 등록", "{name} 이름으로" → plan_name 명시.

## Plan name 자동 추론

다음 우선순위:
1. **사용자가 명시 지정** → 그것 사용.
2. **사용자 글로벌 룰의 Doc 구조 패턴**:
   `Docs/DEVELOPMENT/Dev/{시스템명}/...` → `{시스템명}` 추출.
3. **파일 basename**:
   `COMBAT_PLAN.md` → `_PLAN` 접미사 제거 → 첫 글자만 대문자 유지하거나
   원본 보존 (예: "COMBAT" 또는 "Combat" — 사용자 시스템명 컨벤션 따름).
4. **PLAN.md의 H1 (`# {제목}`)**: 한국어 제목이면 영어 안전 식별자로 변환
   (예: "전투 시스템 구현 계획서" → "Combat" — 단, 이건 LLM 추론).
5. 모든 시도 실패 시 → 사용자에게 묻기.

## Behavioral Flow

### Step 1 — Read PLAN.md
```
Read <path>
```

파일 없음 → "PLAN.md 파일 없음: {path}. 경로 확인."

### Step 2 — Parse markdown into JSON

LLM이 파싱:

#### 2a. "## 구현 순서" 헤더 찾기

지원 변형:
- `## 구현 순서`
- `## N. 구현 순서` (N = 숫자)
- `## Implementation Order`
- `## Implementation`

찾지 못함 → 에러:
```
❌ "## 구현 순서" 섹션 못 찾음.

지원 형식:
- ## 구현 순서
- ## N. 구현 순서
- ## Implementation Order

PLAN.md 구조 확인 후 재시도.
```

#### 2b. Phase 추출

"## 구현 순서" 섹션 안에서 `### Phase X-Y: 이름` 패턴 찾기:
- 패턴: `^### Phase (\d+)-(\d+): (.+?)(?:\s*\(.*\))?$`
- "(환경)" 같은 부연은 이름에서 제거하거나 그대로 보존
  (스크립트는 `Phase X-Y: 이름` 형식 기대).

Phase 0개 → 에러:
```
❌ Phase 항목 못 찾음.

지원 형식: ### Phase X-Y: 이름

PLAN.md에 Phase 섹션 추가 후 재시도.
```

#### 2c. Phase별 태스크 추출

각 Phase 헤더 다음, 다음 Phase 헤더 또는 섹션 끝 사이에서:
- **권장 형식**: `- 태스크` 단순 bullet (현 표준).
- **Backward compat**: `- [ ] 태스크`, `- [x] 태스크` 도 인식 (기존 PLAN.md 호환).
  단 PLAN.md 의 체크 표시는 *초기 status 만* 결정 — 진행 추적은 progress.yaml 단독.
- `[x]` 또는 `[X]` → 완료된 태스크로 처리.
- 빈 줄 / 일반 텍스트 / 코드 블록은 무시.

#### 2d. Build JSON

```json
{
  "name": "{plan_name}",
  "phases": [
    {
      "id": "Phase 1-1",
      "name": "이름",
      "tasks": [
        {"name": "태스크1", "status": "pending"},
        {"name": "태스크2", "status": "completed"}
      ]
    },
    ...
  ]
}
```

- `status`는 마크다운에서 추론한 값. 명시 안 된 경우 스크립트가
  default `pending`으로 채움.
- `depends_on` 명시는 안 함 (스크립트가 X-Y 패턴으로 자동 부여).

### Step 3 — Invoke plan_state.py register

stdin으로 JSON 전달:

```bash
echo '<json>' | python {PLUGIN_ROOT}/scripts/plan_state.py register --source <path>
```

또는 임시 파일 방식:
```bash
cat /tmp/parsed.json | python {PLUGIN_ROOT}/scripts/plan_state.py register --source <path>
```

Windows 환경에서 stdin pipe가 인코딩 문제 일으킬 수 있으므로
임시 파일 → `<` redirect 권장.

### Step 4 — Parse JSON response

### Step 5 — Handle errors

- `source_file_not_found` → "source 파일 없음: {path}".
- `plan_already_exists` →
  ```
  ⚠️ plan '{name}' 이미 등록됨.

  옵션:
  1. PLAN.md가 변경됐다면 → /hs:plan-redesign
  2. 기존 plan 정리 후 재등록 → /hs:plan-unload {name} 후 다시 plan-load
  3. 다른 이름으로 등록 → /hs:plan-load <path> <new_name>
  ```
- `invalid_input` → JSON 형식 문제. 파싱 단계 다시 검토.

### Step 6 — Render success

```
📋 plan 등록 완료: {name}

📄 소스: {source}
📊 Phase 수: {phases}개
📋 태스크 수: {tasks}개
✅ 활성 plan으로 설정됨

Phase 구조:
{각 phase 요약}
- Phase {id}: {name} ({task count}개 task)
{end}

💡 다음 단계:
- 진행 시작 (수동): /hs:plan-start Phase 1-1
- 자동 전체 실행: /hs:plan-run
- 현황 확인: /hs:plan-status
```

### Step 7 — Output policy
- 등록 완료 후 새로 만든 파일들 (.hs/PlanTask/{name}/progress.yaml,
  .hs/state.yaml)은 **스크립트가 atomic 생성** — LLM이 별도 손대지 않음.
- 보고서 파일 자동 저장 안 함.

## Tool coordination
- **Read** — PLAN.md 파일 읽기.
- **Bash** — `plan_state.py register` 호출 (stdin pipe).
- **Write** — 임시 JSON 파일 저장 (Windows 인코딩 안전 처리).

## Boundaries

**Will:**
- PLAN.md 마크다운 파싱 (사용자 룰의 PLAN 형식 + 변형 허용).
- 자동으로 plan name 추론 (Doc 구조 / 파일명 / H1 우선순위).
- 의존성 그래프 자동 생성 (X-Y 패턴 → 스크립트 책임).
- 등록 시 자동으로 current_plan 전환.

**Will Not:**
- 이미 등록된 plan을 silent overwrite 하지 않음
  (`plan_already_exists` 에러 → 사용자 결정 받기).
- PLAN.md 형식이 깨졌으면 추측해서 진행하지 않음
  (명확한 에러로 사용자에게 수정 요청).
- progress.yaml 직접 편집 금지 (스크립트 통해서만).
- 어떤 스킬도 자동으로 호출하지 않음. 사용자 명시 호출만 진입 가능 (Mutating 스킬 — 상태 변경 작업이므로 명시 진입 필수).

## Examples

### 표준 경로
```
/hs:plan-load Docs/DEVELOPMENT/Dev/Combat/COMBAT_PLAN.md
```
→ plan_name = "Combat" (디렉토리에서 추론).

### 명시 이름
```
/hs:plan-load /tmp/stock_plan.md StockAnalyzer
```
→ plan_name = "StockAnalyzer".

### 자연어 + 이름
```
/hs:plan-load Docs/.../INVENTORY_PLAN.md "인벤토리 시스템" 이름으로
```
→ plan_name = "Inventory" (한국어 이름 → 영어 안전 식별자 추론).
   또는 사용자에게 영어 이름 한 번 물어봄.

### 이미 등록된 plan 재 load (활성 전환 의도)
```
/hs:plan-load Docs/.../COMBAT_PLAN.md
```
→ `plan_already_exists` → 사용자에게 옵션 제시:
   - source 변경됐으면 plan-redesign
   - 단순 활성 전환은 다른 명령 권장? — 아쉽게도 직접 명령 없음.
     **답**: 등록된 plan에 대해 `current_plan`만 갱신하고 싶으면
     명시적으로 `set-current` 제공 필요. 현재는 plan-load 동일 경로
     재호출 시 자동 처리하지 않음 (안전 우선).

## Next Step
- 진행 시작 → `/hs:plan-start <phase_id>` (보통 Phase 1-1)
- 자동 전체 실행 → `/hs:plan-run`
- 현황 확인 → `/hs:plan-status`
- 다른 plan 등록 → 같은 명령으로 다른 path
