---
name: explain
description: "코드 / 개념 / 시스템 동작 / 에러 설명 (explain, 설명, 뭐 하는 거야, 어떻게 동작, 왜 이래). 가벼운 출력 전용 스킬. 깊이는 자연어로 추론."
version: 0.1.0
---

# /hs:explain - Explain Code, Concepts, and System Behavior

## Operating principles
- The user's global rules in `~/.claude/CLAUDE.md` and `~/.claude/rules/*.md`
  are the authoritative persona. Follow them strictly.
- This skill provides procedural guidance only — no identity injection,
  no priority overrides.
- If guidance here conflicts with user rules, user rules win.
- Respond to the user in Korean.

## Activation guard
- Explicit invocation (`/hs:explain`) → always proceed.
- Auto-trigger:
  - Strong match (clear question pattern + clear target) → proceed.
  - Weak / ambiguous match → SKIP this skill. Respond as a normal
    assistant without invoking skill behavior.
- Opt-out keywords in the user prompt → SKIP:
  "스킬 쓰지 말고", "그냥 답해줘", "직접 답변", "스킬 빼고".

## Activation announcement
The FIRST line of every response from this skill MUST be a single-line
header in this exact format:

🔍 [hs:explain] <target>, <inferred level>

Examples:
- 🔍 [hs:explain] CombatController.ApplyDamage, normal
- 🔍 [hs:explain] JWT 인증, basic
- 🔍 [hs:explain] Unity Addressables 동작, deep

Leave a blank line after the header, then proceed with the skill's
normal output.

## Triggers
- 코드 이해 ("이 함수 뭐 해?", "이 클래스 어떻게 동작?").
- 개념 설명 ("JWT가 뭐야?", "Mermaid 동작 원리").
- 시스템 동작 ("이 흐름 설명", "어떻게 연결되는 거야?").
- 에러 / 스택트레이스 해석 ("이 에러 의미?", "왜 이래?").
- 비교 ("A vs B", "interface와 abstract class 차이").
- 프레임워크 / 라이브러리 ("React useEffect 동작", "Unity Addressables").

## Usage
```
/hs:explain <target or question in natural language>
```

자연어로 무엇을 설명받고 싶은지 자유롭게 표현하세요. 깊이, target
타입, 도메인은 입력에서 자동 추론됩니다. 명시 표현이 있으면 그쪽을
우선합니다.

## Inferring intent from natural language

### Level (응답 깊이)
- "간단히", "쉽게", "한 줄로", "핵심만", "초보자 시각" → `basic`
- 기본 → `normal`
- "깊게", "꼼꼼히", "내부 동작까지", "구현 세부", "전부" → `deep`

### Target type (자료 수집 도구 결정용)
- 파일 경로 / 심볼명 명시 → `code` (serena 활용)
- 라이브러리 / 프레임워크 명시 (`React`, `Unity`, `Spring`) → `library` (context7 활용)
- 일반 용어 / 컨셉 → `concept` (메모리 + 필요시 web)
- 에러 메시지 / 스택트레이스 → `error`
- "A vs B", "차이" → `comparison`
- 모호 → 사용자 입력 그대로 처리

### Domain hint
- 사용자가 "Unity 관점에서", "보안 관점에서" 같은 단서 주면 그쪽 강조.

## Behavioral Flow

### Step 0 — Triage (simple-first)
사용자 질문이 **단순한 단일 답으로 충분**한가?

- 짧고 명확한 질문 ("string.IsNullOrEmpty 뭐 해?") → 짧은 답 1-3문단.
  깊이/구조 안 늘림.
- 복잡 / 모호 / 다층 질문 → 본격 흐름 진입.

simple-first 룰 준수: 사용자가 명시 요청하지 않으면 옵션 / 비교표 /
긴 구조 제시 안 함.

### Step 1 — Identify target
- target type 추론 (code / library / concept / error / comparison).
- level 추론 (basic / normal / deep).
- 자료 수집이 필요한 정도 결정 (도구 사용 강도).

### Step 2 — Gather facts (lazy — 필요 시만)

#### code 타입
- serena `get_symbols_overview` — 모듈 / 파일 구조.
- serena `find_symbol` — 특정 심볼 위치 + 시그니처.
- serena `find_referencing_symbols` — 호출자 (시스템 동작 설명 시 유용).
- Read — 보조 / serena 미지원 시.
- Grep — 패턴 매칭.

#### library 타입
- context7 `resolve-library-id` → `query-docs`.
- 학습 메모리 우선, 정확도 의심되면 context7로 검증.

#### concept 타입
- 메모리 기반.
- "최근 변화", "현재 표준" 같은 시간성 키워드 있으면 WebSearch 보조.

#### error 타입
- 에러 메시지 그대로 분석.
- 스택트레이스 있으면 코드 anchor 잡고 serena 사용.

#### comparison 타입
- 양쪽 모두에 대해 fact 수집 후 비교.

### Step 3 — Structure the explanation

level에 따라 구조화:

#### `basic`
```
{핵심 한 줄}

{비유 / 가까운 익숙한 개념}

{1-2개 간단한 예제}
```
→ 1-3문단, 길이 짧게.

#### `normal` (default)
```
## TL;DR
{핵심 1-2줄}

## 동작 / 의미
{어떻게 동작하는지 / 무슨 의미인지 본문}

## 예제
{실제 사용 케이스 1-2개}

## 주의사항 (있으면)
{함정 / 트레이드오프}
```

#### `deep`
```
## TL;DR
{핵심}

## 배경 / 맥락
{왜 이런 게 존재하는지, 어떤 문제 해결}

## 동작 원리
{내부 동작 / 알고리즘 / 흐름 / 다이어그램 (Mermaid 가능)}

## 구현 / 사용
{코드 예제, 실제 호출, 통합 패턴}

## 주의 / 트레이드오프
{성능 / 보안 / 한계}

## 관련 / 비교
{비슷한 것들과의 차이, 언제 어느 것}
```

### Step 4 — Generate

위 구조에 맞게 작성. 원칙:
- 사실 기반: 도구로 수집한 fact 우선, 메모리 추론은 보조.
- 한국어 본문, 기술 용어 혼용 가능.
- 코드 예제는 사용자 프로젝트 컨벤션 따름 (글로벌 룰의 코딩 컨벤션).
- 다이어그램이 도움되면 Mermaid 사용.
- `file_path:line` 형식으로 코드 위치 참조 (글로벌 룰).

### Step 5 — Suggest follow-up (선택적)

길이가 길거나 deep 모드에서만:
- 관련 개념 / 추가 학습 자료 / 다음 질문 한 줄.
- 사용자가 simple-first 의도 보였으면 생략.

## Output policy
- 대화 전용. 파일 자동 저장 안 함.
- 사용자가 명시적으로 "저장해줘" 하면 → `/hs:document` 안내 (자동
  호출 X).
- 다른 스킬 자동 호출 안 함.

## Tool coordination

### Default toolset
- **Read** — 사용자가 명시한 파일.
- **Grep / Glob** — 코드 anchor 탐색 (serena 미지원 시 fallback).

### code 타입 default
- **serena** — `find_symbol`, `get_symbols_overview`,
  `find_referencing_symbols`. 가장 정확. 항상 우선.

### Bash
- 거의 사용 안 함. 필요 시 read-only (예: `git log`로 최근 변경 확인).

## MCP integration (use when conditions match)

### serena — code 타입에서 strongly preferred
프로젝트 내 코드 설명 시 메모리 추론 대신 fact 기반.

### context7 — library 타입에서 strongly preferred
라이브러리 / 프레임워크 동작 설명 시:
- `resolve-library-id` → `query-docs`.
- 학습 데이터 stale 회피.
- 짧은 질문도 정확도 의심되면 context7 1회 확인.

### sequential-thinking — deep + 복잡 시스템에서만
deep level + 다요소 시스템 (예: "전체 인증 흐름", "다 모듈 데이터 흐름"):
- `sequentialthinking`으로 단계적 분석.
- normal/basic 깊이엔 오버헤드.

### excel-mcp — 데이터 / 밸런스 설명 (희소)
사용자가 `.xlsx` 데이터 설명 요청 시 read-only로 인용.

### gemini-video — 비디오 자료 (드뭄)
사용자가 영상 명시 제공 시.

### MCP fallback policy
- 모두 optional. 없으면 built-in으로 silent fallback.
- 사용자 출력에 MCP 이름 노출하지 않음.

## Boundaries

**Will:**
- 코드 / 개념 / 시스템 / 에러 / 비교 모두 다룸.
- level / target type 자연어 추론.
- 단순 질문엔 단순 답 (simple-first 룰).
- 코드 fact는 serena, 라이브러리는 context7로 정확도 확보.
- 결과는 대화로만.

**Will Not:**
- 코드 / 파일 변경 안 함 (출력 전용).
- 보고서 파일 자동 저장 안 함 (저장은 `/hs:document` 위임).
- 페르소나 주입 / 사용자 룰 무시.
- 다른 스킬 자동 호출.
- 단순 질문에 옵션 / 비교표 / 다단계 구조 강제 (simple-first).
- 사실 확인 없이 짐작으로 답 (도구 사용 가능한데 안 쓰는 일 없음).

## Examples

### 짧은 코드 함수 설명
```
/hs:explain string.IsNullOrEmpty 뭐 해?
```
→ basic. 1-2문단으로 짧게. 비유 + 예제.

### 프로젝트 함수 설명
```
/hs:explain CombatController.ApplyDamage
```
→ code, normal. serena로 시그니처 + 본문 + 호출자 fact 수집 후 설명.

### 시스템 동작 deep
```
/hs:explain 인증 시스템 전체 흐름 깊게
```
→ code/concept, deep. serena로 관련 모듈 fact + 흐름 설명. 필요 시
   Mermaid sequenceDiagram.

### 라이브러리
```
/hs:explain Unity 6 Addressables 동작 원리
```
→ library, normal/deep. context7로 공식 정보.

### 에러
```
/hs:explain NullReferenceException at CombatController.cs:142
```
→ error. 해당 위치 코드 읽고 원인 추정 + 일반적 패턴 설명.

### 비교
```
/hs:explain interface vs abstract class 차이 간단히
```
→ comparison, basic. 짧은 비교표 또는 1-2문단.

### 단순 질문 (triage)
```
/hs:explain `??` 연산자가 뭐야?
```
→ Triage: 단순 질문. 1-2줄 답. "더 깊게 알고 싶으면 알려주세요" 한 줄만.

## Next Step
- 더 깊게 보고 싶으면 → 같은 스킬 깊이 표현 추가 호출
- 결과 저장 → `/hs:document`
- 코드 변경하고 싶으면 → `/hs:implement` (이건 별개 흐름)

This skill takes no further action automatically.
