---
name: review
description: "코드 변경 리뷰 (review, 리뷰, 검토, 커밋 전 점검). subagent 격리 컨텍스트로 신선한 시각 확보. diff/branch/file/range 모드. 진단 전용 (수정은 implement 위임)."
version: 0.1.0
---

# /hs:review - Code Review via Isolated Subagents

## Operating principles
- The user's global rules in `~/.claude/CLAUDE.md` and `~/.claude/rules/*.md`
  are the authoritative persona. Follow them strictly.
- This skill provides procedural guidance only — no identity injection,
  no priority overrides.
- If guidance here conflicts with user rules, user rules win.
- Respond to the user in Korean.

## Activation guard (explicit-only)
This skill activates ONLY via explicit `/hs:review` invocation.
- Auto-trigger: NEVER. subagent 호출은 토큰 비용이 큼.
- Opt-out keywords still apply as a safety net:
  "스킬 쓰지 말고", "그냥 답해줘", "직접 답변", "스킬 빼고" → SKIP.

## Activation announcement
The FIRST line of every response from this skill MUST be a single-line
header in this exact format:

🔍 [hs:review] <mode>, <target summary>, <depth>

Examples:
- 🔍 [hs:review] diff, uncommitted changes, normal
- 🔍 [hs:review] branch, feature/combat vs main, deep (multi-perspective)
- 🔍 [hs:review] file, src/Combat/CombatController.cs, normal
- 🔍 [hs:review] range, src/Combat/CombatController.cs:120-180, quick

체이닝된 호출 시 (Phase 2 자동호출 활성화 후):
- Diagnostic 체이닝: 본 헤더 다음 줄에 "↳ chained from /hs:이전스킬" 추가.
- Pipeline-Stage 체이닝: 본 헤더 다음 줄에 "↳ chained from /hs:이전스킬 (pipeline)" 추가.
- 명시 호출: 추가 표기 없음.

Leave a blank line after the header, then proceed with the skill's
normal output.

## Workflow position

`/hs:review`는 **격리 컨텍스트(subagent)**로 신선한 시각 확보. 메인
대화의 작성/추론 컨텍스트로부터 분리되어 결과물만 평가.

```
사용자 작업 (implement / refactor / cleanup 등)
        ↓
   /hs:review
        ↓
[Agent tool] subagent 격리 호출 (1개 또는 병렬 여러 개)
        ↓
[합성] 다중 시각 → 통합 보고
        ↓
사용자에게 한국어 리뷰
```

수평적 대안 (서로 호출 X):
- `/review` (빌트인) — PR 리뷰
- `/security-review` (빌트인) — 보안 위주
- `/ultrareview` (빌트인, 과금) — 클라우드 멀티 에이전트
- **`/hs:review` (우리) — 로컬 일상 리뷰, 한국어, 우리 룰 정합**

## Scope definition

### What this skill does
- 변경 / 파일 / 범위를 subagent에게 격리 평가 요청.
- 다중 시각(deep 모드) 또는 단일 시각(quick/normal) 구성.
- 한국어로 우선순위화된 리뷰 보고.
- 사용자 글로벌 룰 위반 (예: 암묵적 비교, asmdef 자동 생성, AssetDatabase
  런타임 사용)을 명시적 검토 대상으로 둠.

### What this skill does NOT do
- 코드 / 파일 변경 안 함 (read-only).
- 빌드 / 테스트 / git 명령 자동 실행 안 함.
- 빌트인 `/review`, `/ultrareview` 등 슬래시 스킬 내부 호출 안 함.
- 결과를 파일로 자동 저장하지 않음 (저장은 `/hs:document` 위임).

## Triggers
- "리뷰해줘", "검토해줘", "점검", "커밋 전 봐줘".
- 명시 `/hs:review` 호출.

## Usage
```
/hs:review [target or scope in natural language]
```

자연어로 무엇을 리뷰할지 자유롭게 표현하세요. 모드, 깊이, 시각은
입력에서 자동 추론됩니다.

## Inferring intent from natural language

### Mode (입력 대상)
- 인자 없음 / "변경", "diff" → `diff` (uncommitted 변경 + 스테이지)
- "브랜치", "PR 전", "feature/x vs main" → `branch`
- 파일 경로 명시 → `file`
- `path:start-end` 형식 → `range`
- 모호 → 사용자에게 1회 확인.

### Depth
- "빨리", "핵심만", "한 줄로" → `quick` (단일 subagent / 짧은 보고)
- 기본 → `normal` (단일 subagent / 표준 보고)
- "깊게", "꼼꼼히", "다 봐줘", "여러 시각" → `deep` (병렬 다중 subagent)

### Focus (선택적 — 단일 시각 강조)
- "보안" → security-engineer 단독 또는 우선
- "품질만" → quality-engineer 단독
- "구조" → refactoring-expert 단독
- 미언급 + deep → 다중 시각 자동 구성

## Behavioral Flow

### Step 1 — Triage (simple-first)
- 단순 / 짧은 변경 (몇 줄 추가) + 사용자가 "빨리" 표현 → quick 단일 시각으로 짧게.
- 그 외 → 본격 흐름.

### Step 2 — Identify scope

#### diff 모드
```bash
# uncommitted + staged 변경 식별
git status
git diff
git diff --cached
```

#### branch 모드
```bash
# 현재 브랜치 vs main
git log --oneline main..HEAD
git diff main...HEAD
```

#### file 모드
- 명시 파일 Read.

#### range 모드
- 명시 파일의 특정 라인 범위 Read.

### Step 3 — Gather artifact

리뷰 대상 컨텐츠를 모음 (subagent 브리핑 자료):
- 변경된 파일 목록
- 변경 내용 (diff 또는 파일 본문)
- 컨텍스트 정보 (관련 모듈, 호출자 — serena 활용 가능)
- 사용자 의도 단서 (커밋 메시지, PR 제목 등)

### Step 4 — Choose subagent strategy

#### quick / normal — 단일 시각
- 기본: `general-purpose` subagent (전반)
- focus 명시 시: 해당 전문 subagent

#### deep — 병렬 다중 시각
이상적 조합 (Agent tool에서 한 번에 여러 호출):

| Subagent | 시각 |
|----------|------|
| **quality-engineer** | 품질, 엣지 케이스, 테스트 누락 |
| **security-engineer** | 보안 취약점, 인증/권한, 입력 검증 |
| **refactoring-expert** | 구조, 결합도, 기술 부채 |
| **general-purpose** | 전반, 사용자 룰 준수 |

→ 4개 동시 호출 (한 메시지에서 여러 Agent 도구 사용).
→ 토큰 비용 높음. 사용자 명시 deep 요청 시만.

### Step 5 — Brief and dispatch

각 subagent에게 자기충족적 프롬프트 전달:

```
[배경]
사용자 프로젝트의 코드 리뷰 요청. 모드: {mode}, 대상: {target}.

[리뷰 대상]
{변경 diff 또는 파일 본문}

[주의: 사용자 글로벌 룰]
다음 룰 위반 여부 검토 필수:
- 암묵적 비교 금지: if (obj == null), if (count > 0) 형식 강제 (C# / 그 외 동일)
- 시그널버스 / 글로벌 이벤트 브로커 금지
- Unity: asmdef 자동 생성 금지, AssetDatabase 런타임 사용 금지
- 한국어 코드 주석, 영어 식별자
- 과도한 추상화 / 미래 대비 추상화 금지
- 요청 외 작업 금지 (scope creep)
- 사용자 룰 파일: ~/.claude/rules/*.md

[요청 시각]
{이 subagent의 전문 영역에 집중}
{quality-engineer 예: 품질 / 엣지 케이스 / 테스트 위주}

[기대 출력]
다음 형식의 한국어 리뷰:
## 발견 사항 (심각도별)
- Critical: ...
- High: ...
- Medium: ...
- Low: ...

## 룰 위반
{각 위반 사항 file_path:line + 위반 내용 + 수정 방향}

## 잘된 점 (선택적)
{2-3개)

## 의문점 / 추가 정보 필요
{있으면}

200-400자 정도로 간결하게.
```

### Step 6 — Synthesize results

여러 subagent 결과 받아서 통합:

#### 충돌 / 중복 처리
- 같은 이슈 여러 시각이 발견 → 1개로 합침 + "여러 관점에서 지적됨" 표기
- 시각 간 모순 (예: refactor가 abstraction 추가 권장, quality는 단순화 권장) → 양쪽 의견 보존, 사용자 결정 안내

#### 우선순위화
- Critical → High → Medium → Low
- 같은 심각도 안에서: 영향 범위 / 신뢰도 순

### Step 7 — Render unified report

```
# 리뷰 결과: {대상}

## 요약
- 총 {N}건 발견 (Critical {x} / High {y} / Medium {z} / Low {w})
- 핵심 이슈 1-2줄
- (deep 모드) 시각 {n}개 합성

## Critical
- {file_path}:{line} — {issue}
  시각: {quality / security / ...}
  권장: {action}

## High
- ...

## Medium / Low
- ...

## 사용자 룰 위반 (있으면)
- {file_path}:{line} — {룰} 위반: {설명}
  수정 방향: {action}

## 잘된 점
- {2-3개}

## 의문점
- {추가 정보 / 사용자 의도 확인 필요}

## 다음 단계 (사용자 결정)
- 적용 → /hs:implement / /hs:refactor / /hs:cleanup
- 보존 → /hs:document
- 의문 해소 → 추가 대화
```

### Step 8 — Output policy

**모든 출력 끝에 표준 `## Skill Output Metadata` appendix 의무** — Collected Facts (3-5 fact) + Next Skill Hints. 다음 스킬이 fact 재수집 회피 + 체이닝 시그널 명시 (HSPOLICY_DESIGN 의 "Fact 공유 — Output appendix 강제 규약" 절 참조). **직전 스킬의 appendix 가 있으면 본 스킬 입력으로 우선 사용** — 같은 fact 재수집 회피.
- 대화 전용. 파일 자동 저장 안 함.
- 코드 / 파일 변경 안 함.

## Tool coordination

### Default toolset
- **Bash** — git 명령 (read-only): status, diff, log.
- **Read** — 명시 파일 / range.
- **Grep / Glob** — 컨텍스트 보조.
- **Agent** — subagent 호출 (핵심).
- **serena** — 변경 영향 / 호출자 분석 (preferred).

## Subagent integration (핵심)

### 단일 시각 (quick / normal)
- `general-purpose` 우선 — 사용자 룰 인지 광범위.
- focus 명시 시 해당 전문가:
  - quality → quality-engineer
  - security → security-engineer
  - refactor / 구조 → refactoring-expert

### 다중 시각 (deep)
**한 메시지에서 4개 subagent 동시 호출** (Agent tool 다중 사용):
- quality-engineer
- security-engineer
- refactoring-expert
- general-purpose

각자 격리 컨텍스트에서 평가 → 결과 병합. 메인 컨텍스트는 가벼움.

### subagent 선택 가이드
- 항상 **자기충족적 프롬프트** 작성 (subagent는 메인 컨텍스트 못 봄).
- 사용자 룰을 **명시적으로 브리핑**에 포함 (subagent가 사용자 룰을
  자동 인지한다고 가정 X — 시스템 프롬프트로 들어가긴 하지만
  명시적으로 강조해서 정확도 ↑).
- 한국어 출력 명시.

## MCP integration (lazy)

리뷰 대상 코드 분석 시 보조 MCP:

### serena — 변경 영향 분석의 핵심 (preferred)
리뷰의 본질은 "이 변경이 어디까지 영향을 미치는가" — serena 의 의미
기반 도구로 grep 보다 정확한 영향 범위 산정.
- `find_referencing_symbols` — 변경된 심볼의 호출자 / 의존자 식별.
- `get_diagnostics_for_file` — 컴파일러/LSP 진단 같이 보고.
- `find_implementations` — 인터페이스 / 추상 클래스 변경 시 구현체 추적.
- subagent에 컨텍스트 brief 전 메인에서 활용 가능 (각 subagent 가
  중복 호출하지 않도록 영향 범위 사전 정리).

### context7 — 라이브러리 사용 검증 시
- 변경에 새 API / 라이브러리 사용 → 권위 정보 확인.
- 평소엔 사용 안 함.

### sequential-thinking — 대형 / 다층 변경 PR 에서만
다음 조건일 때 활용:
- 변경 파일 ≥ 10개 AND 다중 모듈 경계 교차.
- 아키텍처 레이어 변경 (계층 의존 방향 / 순환 가능성 검토 필요).
- 단계적 영향 추적 필요 (A 변경 → B 영향 → C 의존성 갱신 누락 여부).

소형 PR / 단일 파일 수정엔 오버헤드 — 패턴 매칭 스캔으로 충분.

### 기타 MCP는 거의 무관.

### Fallback policy
- 모두 optional. 사용자 출력에 MCP 이름 노출 안 함.

## Boundaries

**Will:**
- diff / branch / file / range 모드 자연어 추론.
- subagent 격리 평가 (단일 또는 병렬 다중).
- 사용자 글로벌 룰 위반 명시 검토.
- 다중 시각 결과 합성 (충돌은 양쪽 보존).
- 한국어 우선순위화 보고.

**Will Not:**
- 코드 / 파일 변경 안 함.
- 빌드 / 테스트 / git mutating 명령 자동 실행 안 함.
- Mutating 스킬 자동 호출 금지 (implement / refactor / cleanup / document / plan-* / cl-* 등). 빌트인 슬래시 스킬 (`/review`, `/ultrareview` 등) 도 자동 호출하지 않음.
- Diagnostic 끼리는 사용자 체이닝 시그널 있고 opt-out 없을 때만 자동 호출 허용 (활성). 안전 쌍: analyze→explain, research→brainstorm, troubleshoot→explain. **review 는 안전 쌍에서 제외 — review→다음 스킬 자동 체이닝 금지 (사용자 의식 호출 강제, 게이트키퍼 역할).**
- 자동 호출 시 activation header 에 "↳ chained from /hs:이전스킬" 표기 의무.
- **review 는 Diagnostic 이지만 mutating (implement 등) 자동 호출을 명시 차단.** "리뷰 결과 → 사용자 검토 → 명시 호출" 게이트키퍼 역할이 의도된 안전망. Pipeline-Stage 예외 적용 안 됨.
- 결과 자동 저장 안 함 (저장은 `/hs:document`).
- subagent 결과를 검증 없이 그대로 출력하지 않음 (충돌 / 중복 처리).
- 신뢰도 낮은 가설을 단정으로 보고하지 않음.
- 페르소나 주입 / 사용자 룰 무시.

## Examples

### Quick — 변경 짧게 점검
```
/hs:review 빨리 봐줘
```
→ mode: diff, depth: quick. general-purpose 1개 호출. 간결 보고.

### Normal — 일반 리뷰
```
/hs:review
```
→ mode: diff, depth: normal. general-purpose 1개. 표준 보고.

### Deep — 다중 시각
```
/hs:review 깊게 봐줘
```
→ depth: deep. 4개 subagent 병렬 호출 → 시각 합성 + 우선순위화.

### Branch — PR 직전
```
/hs:review feature/combat vs main 꼼꼼히
```
→ mode: branch, depth: deep. 모든 변경 다중 시각.

### File — 단일 파일
```
/hs:review src/Combat/CombatController.cs
```
→ mode: file, depth: normal. 파일 본문 + 호출자 컨텍스트.

### Range — 특정 블록
```
/hs:review src/Combat/CombatController.cs:120-180 보안 위주
```
→ mode: range, focus: security. security-engineer 1개 호출.

### 보안 집중
```
/hs:review 보안 위주로
```
→ mode: diff (또는 추론), focus: security. security-engineer 단독.

## Next Step
사용자 결정. 보통:
- 발견된 이슈 수정 → `/hs:implement` (functional fix) /
  `/hs:refactor` (구조 개선) / `/hs:cleanup` (불필요 제거)
- 리뷰 결과 보존 → `/hs:document`
- 의문점 해소 → 추가 대화 또는 `/hs:explain`
- 추가 시각 필요 → `/ultrareview` (빌트인, 과금) 또는 본 스킬 다른 focus

This skill takes no further action automatically.
