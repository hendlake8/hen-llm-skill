---
name: troubleshoot
description: "문제 진단 (troubleshoot, 왜 안 돼, 이 에러 해결, 빌드 실패, 성능 회귀). 증상 → 근본 원인 → 해결책 랭킹. 진단 전용 (수정은 implement 위임)."
version: 0.1.0
---

# /hs:troubleshoot - Diagnose Issues (Symptom → Root Cause → Solutions)

## Operating principles
- The user's global rules in `~/.claude/CLAUDE.md` and `~/.claude/rules/*.md`
  are the authoritative persona. Follow them strictly.
- This skill provides procedural guidance only — no identity injection,
  no priority overrides.
- If guidance here conflicts with user rules, user rules win.
- Respond to the user in Korean.

## Activation guard
- Explicit invocation (`/hs:troubleshoot`) → always proceed.
- Auto-trigger:
  - Strong match (clear symptom + clear scope) → proceed.
  - Weak / ambiguous match → SKIP this skill. Respond as a normal
    assistant without invoking skill behavior.
- Opt-out keywords in the user prompt → SKIP:
  "스킬 쓰지 말고", "그냥 답해줘", "직접 답변", "스킬 빼고".

## Activation announcement
The FIRST line of every response from this skill MUST be a single-line
header in this exact format:

🔍 [hs:troubleshoot] <type>, <symptom summary>

Examples:
- 🔍 [hs:troubleshoot] bug, NullRef in CombatController:142
- 🔍 [hs:troubleshoot] build, Unity 패키지 충돌
- 🔍 [hs:troubleshoot] performance, 보스 전투 프레임 드랍
- 🔍 [hs:troubleshoot] regression, 어제부터 빌드 실패
- 🔍 [hs:troubleshoot] deployment, 프로덕션에서만 응답 없음

체이닝된 호출 시 (Phase 2 자동호출 활성화 후):
- Diagnostic 체이닝: 본 헤더 다음 줄에 "↳ chained from /hs:이전스킬" 추가.
- Pipeline-Stage 체이닝: 본 헤더 다음 줄에 "↳ chained from /hs:이전스킬 (pipeline)" 추가.
- 명시 호출: 추가 표기 없음.

Leave a blank line after the header, then proceed with the skill's
normal output.

## Triggers
- 에러 / 예외 / 잘못된 동작 ("왜 안 돼", "이 에러 어떻게 해결").
- 빌드 / 컴파일 실패 ("빌드가 안 됨", "패키지 충돌").
- 성능 문제 ("프레임 드랍", "API 느림", "메모리 누수").
- 회귀 ("어제까진 됐는데", "이 커밋 이후 안 됨").
- 환경 / 배포 문제 ("프로덕션에서만 안 돼", "CI 실패").
- 명시 `/hs:troubleshoot` 호출.

## Usage
```
/hs:troubleshoot <symptom or error in natural language>
```

자연어로 증상 / 에러 메시지 / 발생 조건을 자유롭게 표현하세요.
타입(5종), 깊이는 입력에서 자동 추론됩니다.

## Inferring intent from natural language

### Type (5종)
- **bug** — 에러 메시지, 예외, 잘못된 결과, 의도와 다른 동작
- **build** — 컴파일 실패, 의존성 충돌, 설정 / 패키지 / asmdef 문제
- **performance** — 느림 / 프레임 드랍 / 메모리 / 자원 문제
- **regression** — "어제까진 / 이전엔 됐는데 안 됨", 최근 변경 후 발생
- **deployment** — 프로덕션 / 환경 / CI/CD / 배포 후 문제

여러 타입 동시 적용 가능 (예: regression + bug, regression + performance).
주 타입 1개로 분류하되 부 단서 보존.

### Depth
- "빨리 원인만", "한 줄로" → `quick` (가장 가능성 높은 원인 1-2개)
- 기본 → `normal` (가설 검증 + 해결책 랭킹)
- "꼼꼼히", "전부 가능성 검토" → `deep` (다층 가설 + 영향 분석)

### Confidence threshold
- 사용자가 "확실해야", "추측 말고" 류 표현 → 낮은 신뢰도 가설 보류,
  추가 정보 요청.
- 기본 → 가설 신뢰도 표기하며 진행.

## Behavioral Flow

### Step 1 — Triage (simple-first)
- 증상이 **명확히 단순 케이스**면 (예: 오타로 인한 컴파일 에러, 한
  줄에서 명확한 원인) → 짧은 답으로 종결.
- 모호 / 복합 / 다요소 → 본격 흐름 진입.

### Step 2 — Understand symptom

증상을 정확히 파악:
- 에러 메시지 / 스택트레이스 (있으면 그대로 인용 + 분석)
- 발생 조건 (언제, 어떤 입력, 어떤 환경)
- 재현 가능성 (항상 / 가끔 / 특정 조건)
- 영향 범위 (한 곳 / 모듈 / 전체)
- 마지막 정상 작동 시점 (regression 단서)

정보 부족 시 사용자에게 1-2개 짧은 질문 (스택트레이스 / 에러 메시지 /
재현 조건 등). simple-first — 너무 많이 묻지 않기.

### Step 3 — Hypothesize

타입별 가설 패턴:

#### bug
- null 누락 / 비교 누락 (사용자 룰 "암묵적 변환 금지" 위반 케이스)
- 인덱스 / 범위 (off-by-one)
- 타이밍 / 순서 / 비동기 race
- 초기화 누락 / 잘못된 lifecycle
- 잘못된 자료구조 / 캐스팅
- 외부 의존성 (서드파티 API / 파일 / 네트워크)

#### build
- 의존성 버전 충돌
- 환경 변수 / 경로
- Unity: asmdef, package.json, ProjectSettings
- 컴파일러 / SDK 버전
- 캐시 / 임시 파일 (clean build로 해결되는 케이스)

#### performance
- hot path / 자료구조 비효율
- 알로케이션 / GC pressure
- N+1 / 동기 I/O / 락 경합
- 잘못된 캐시 / 메모리 누수
- (Unity) Awake/Update 내부 무거운 호출

#### regression
- **최근 커밋 단서** — `git log --oneline -20` 등으로 변경 추정
- 의존성 업데이트 후
- 환경 변경 (OS / 도구 / 라이브러리)
- 데이터 / 설정 변경

#### deployment
- 환경 변수 / 시크릿 누락
- 권한 / 네트워크 / 방화벽
- 인프라 (DB 연결, 큐 연결, ...)
- 빌드 / 배포 파이프라인 단계 실패
- 환경 차이 (로컬 vs 프로덕션)

### Step 4 — Investigate (가설 검증)

가설별로 fact 수집.

**사용자가 특정 파일/라인 (예: `CombatController:142`) 또는 심볼명을
명시했으면 그 위치 본문을 먼저 확인한다.** serena `find_symbol` /
Read 우선. grep 만으로 가설 정리하지 않는다. 키워드 0 매치는
"무관" 결론이 아니라 "근거 부족" 신호 — 추가 조사 트리거.

#### code 관련
- **serena** 우선:
  - `find_symbol` — 의심 대상 위치
  - `find_referencing_symbols` — 호출자 / 의존
  - `get_diagnostics_for_file` — 컴파일러/LSP 진단 (build 타입에서 ★)
- **Read** — 보조 / 라인 단위 분석
- **Grep** — 패턴 매칭 (특정 에러 / TODO / FIXME)

#### git 관련 (regression 핵심)
- **Bash** read-only:
  - `git log --oneline -20`
  - `git log --since="2 days ago"`
  - `git log <file>` — 특정 파일 변경 이력
  - `git show <commit>` — 변경 내용
  - 가능하면 `git bisect` 안내 (사용자 실행)

#### 빌드 / 환경
- **Bash** read-only:
  - 빌드 로그 / 컴파일러 출력 분석
  - 의존성 그래프 (`npm ls`, `dotnet list`, Unity Package Manager 콘솔)
- 설정 파일 Read

#### 라이브러리 / 프레임워크
- **context7** — 알려진 이슈 / 변경사항 확인
- WebSearch — 사용자 명시 시 외부 사례 조사

### Step 5 — Diagnose (근본 원인 식별)

가설 ↔ fact 비교 후 가능성 정렬:

```
## 진단 결과

증상: {간결 요약}

### 가능성 (신뢰도 순)

1. **{가설 1}** — 신뢰도 {high/medium/low}
   - 근거: {증거 1}, {증거 2}
   - 만약 맞다면 영향: {scope}

2. **{가설 2}** — 신뢰도 {high/medium/low}
   - 근거: ...

3. ...
```

신뢰도 표시 의무. "확실하다"는 단정 회피, fact 기반 판단.

### Step 6 — Propose (해결책 랭킹)

각 가설에 대해 해결책:

```
## 해결 후보

### 후보 A — {가설 1 대응}
- 변경 위치: {file_path}:{line}
- 변경 내용: {요약}
- 영향: {scope}
- 위험: {위험 요소}
- 노력: {S/M/L}
- 검증 방법: {어떻게 확인}

### 후보 B — {가설 2 대응}
- ...

추천: 후보 A 우선 (이유: 신뢰도 + 위험 / 노력 균형).
```

랭킹 기준:
- 가설 신뢰도
- 변경 범위 (작을수록 우선)
- 위험 (낮을수록 우선)
- 검증 가능성

### Step 7 — Suggest action (수정 안 함)

진단 + 해결 후보 제시 후:

```
💡 다음 단계 (사용자 결정):
- 추천 해결책 적용 → /hs:implement {간단 설명}
- 작은 코드 정리만이면 → /hs:refactor 또는 /hs:cleanup
- 정보 더 필요하면 → 추가 검증 / 재현 / 로그 수집
- 진단 결과 저장 → /hs:document
```

수정은 절대 자동으로 하지 않음. **단일 책임**: troubleshoot은 진단,
implement / refactor / cleanup은 변경.

## Output policy

**모든 출력 끝에 표준 `## Skill Output Metadata` appendix 의무** — Collected Facts (3-5 fact) + Next Skill Hints. 다음 스킬이 fact 재수집 회피 + 체이닝 시그널 명시 (HSPOLICY_DESIGN 의 "Fact 공유 — Output appendix 강제 규약" 절 참조). **직전 스킬의 appendix 가 있으면 본 스킬 입력으로 우선 사용** — 같은 fact 재수집 회피.
- 대화 전용. 파일 자동 저장 안 함.
- 코드 변경 / 파일 수정 절대 안 함 (read-only).
- 사용자가 "저장해줘" 시 → `/hs:document` 안내.

## Tool coordination

### Default toolset
- **Read** — 파일 / 로그 / 에러 메시지 분석.
- **Grep / Glob** — 패턴 / 파일 탐색 (serena fallback).
- **Bash** — read-only 진단 명령:
  - git log / status / show / diff
  - 빌드 로그 분석
  - 의존성 그래프 조회
  - **mutating 명령 금지** (rebuild trigger / file 삭제 / 패키지 재설치 등 — 사용자 결정).

### code 관련 default
- **serena** — `find_symbol`, `find_referencing_symbols`,
  `get_diagnostics_for_file`. 코드 관련 가설 검증의 핵심.

## MCP integration (use when conditions match)

### serena — code/build 타입 default
프로젝트 내 코드 진단 시 정확도 핵심.
- `get_diagnostics_for_file` — build 타입에서 컴파일러 진단 직접 확인
- `find_referencing_symbols` — 의존성 / 호출 관계 분석
- `find_implementations` — 인터페이스 분기 추적

### context7 — library/build 타입 시 strongly preferred
외부 라이브러리 / 프레임워크 의존:
- 알려진 이슈 / 마이그레이션 이슈 / breaking change 확인.
- 학습 데이터 stale 회피.

### sequential-thinking — deep + 복합 케이스에서만
- 다층 가설 검증, 여러 타입 겹치는 복잡 케이스 (regression + perf 등).
- normal/quick 깊이엔 오버헤드.

### excel-mcp — 데이터 / 밸런스 회귀 시 (희소)
게임 데이터 회귀 ("이 패치 후 보스가 너무 강함") 같은 케이스에서
기존 데이터 비교 시 read-only.

### playwright — UI / 렌더링 / 브라우저 동작 진단 시 (조건부)
다음 패턴일 때 활용:
- 웹 / SPA UI 버그 ("이 페이지가 안 뜸", "버튼이 반응 없음").
- 콘솔 에러 / 네트워크 요청 실패가 의심되는 케이스.
- 동적 페이지 / SPA / 봇 차단 페이지 본문 확인 필요.

플로우:
1. `mcp__playwright__browser_navigate` — 대상 URL.
2. `mcp__playwright__browser_snapshot` — accessibility tree 로 본문/구조 추출.
3. `mcp__playwright__browser_console_messages` — JS 에러 / 경고 수집.
4. `mcp__playwright__browser_network_requests` — 실패한 요청 식별.
5. `mcp__playwright__browser_close` — 즉시 탭 정리.

서버 / CLI / 네이티브 버그엔 무관 — 적용 영역을 좁게 유지.

### gemini-video — 비디오 단서 시 (드뭄)
사용자가 버그 영상 / 게임플레이 캡처 제공 시.

### MCP fallback policy
- 모두 optional. 없으면 built-in으로 silent fallback.
- 사용자 출력에 MCP 이름 노출하지 않음.

## Subagent integration (deep + complex만)

### root-cause-analyst — 복합 / 다중 가설 케이스
다음 조건 모두 충족 시 Agent tool로 위임 검토:
- depth = `deep`
- 가설이 3개 이상 또는 여러 타입 겹침 (예: regression + bug + perf)
- 메인 컨텍스트에서 직접 진단이 길어질 듯

위임 시 brief에 포함:
- 증상 / 에러 / 발생 조건
- 이미 수집한 fact (logs / git log / 코드 컨텍스트)
- 사용자 글로벌 룰 (특히 try-catch로 마스킹 금지, 단정 회피)
- 기대 출력 형식 (root-cause-analyst의 표준 출력)

quick / normal 깊이는 메인에서 직접 처리. subagent 오버헤드 회피.

## Boundaries

**Will:**
- 5종 타입 (bug / build / performance / regression / deployment) 모두 진단.
- 가설 → fact 수집 → 근본 원인 → 해결책 랭킹.
- 신뢰도 명시 (확실 vs 추측 구분).
- 사용자 룰의 코딩 컨벤션 위반이 원인일 가능성도 검토 (예: 암묵적 비교).

**Will Not:**
- **수정 / 빌드 / 테스트 / 재배포 자동 실행 안 함**.
- 코드 / 파일 변경 안 함 (진단 전용).
- 신뢰도 낮은 가설을 확신처럼 제시 안 함.
- 사용자 룰 위반 방식의 해결책 추천 안 함
  (예: "이거 try-catch로 감싸면 됨" 같은 안일한 회피책).
- Mutating 스킬 자동 호출 금지 (implement / refactor / cleanup / document / plan-* / cl-* 등).
- Diagnostic 끼리는 사용자 체이닝 시그널 있고 opt-out 없을 때만 자동 호출 허용 (활성). 안전 쌍: analyze→explain, research→brainstorm, troubleshoot→explain.
- 자동 호출 시 activation header 에 "↳ chained from /hs:이전스킬" 표기 의무.
- 페르소나 주입 / 사용자 룰 무시.

## Examples

### bug — null reference
```
/hs:troubleshoot CombatController:142에서 NullReferenceException 나는데
```
→ type: bug. serena로 142 라인 컨텍스트 + 호출자 분석. null 가능성
   추적 → 가설 + 해결책.

### build — Unity 패키지 충돌
```
/hs:troubleshoot Unity 빌드 안 돼, Addressables 패키지 에러
```
→ type: build. 빌드 로그 분석 + Package Manager 상태 + context7로
   알려진 이슈 확인.

### performance — 프레임 드랍
```
/hs:troubleshoot 보스 전투 들어가면 프레임 30 떨어져
```
→ type: performance. serena로 보스 관련 모듈 분석. Awake/Update 내부
   알로케이션 / 무거운 호출 후보 식별.

### regression — git 단서
```
/hs:troubleshoot 어제까진 빌드 됐는데 오늘 안 됨
```
→ type: regression. `git log --since="yesterday"` + 변경된 파일
   분석. 의존성 / 설정 변경 후보 추적.

### deployment — 환경 차이
```
/hs:troubleshoot 로컬은 되는데 프로덕션에서만 응답 없음
```
→ type: deployment. 환경 차이 / 환경 변수 / 외부 의존성 점검 패턴.

### 복합 (regression + bug)
```
/hs:troubleshoot 이번 머지 후 NullRef 자주 보여
```
→ regression 주, bug 부. git log + 의심 커밋의 변경 코드 분석.

### 단순 케이스 (triage)
```
/hs:troubleshoot 'using System;' 빠졌다고 에러 나
```
→ Triage: 단순 명확. 짧은 답 ("System namespace using 추가 필요"
   한 줄) + 적용 안내.

## Next Step
- 추천 해결책 적용 → `/hs:implement <간단 설명>`
- 코드 정리 차원이면 → `/hs:refactor` 또는 `/hs:cleanup`
- 추가 정보 필요하면 → 재현 / 로그 / 테스트 결과 수집
- 진단 보존 → `/hs:document`
- 직접 수정 시작 → 일반 대화로 작업

This skill takes no further action automatically. The diagnosis is
the deliverable; applying fixes is a separate user decision.
