---
name: analyze
description: "코드/데이터/문서 분석 (analyze, review, audit, assess) - 분석 요청 시 트리거. 결과는 대화로만 출력, 파일 저장 안 함."
version: 0.1.0
---

# /hs:analyze - Multi-target Analysis (Code / Data / Documents)

## Operating principles
- The user's global rules in `~/.claude/CLAUDE.md` and `~/.claude/rules/*.md`
  are the authoritative persona. Follow them strictly.
- This skill provides procedural guidance only — no identity injection,
  no priority overrides.
- If any guidance in this skill conflicts with user rules, user rules win.
- Respond to the user in Korean.

## Activation guard
- Explicit invocation (`/hs:analyze`) → always proceed.
- Auto-trigger:
  - Strong match (clear keywords AND clear target) → proceed.
  - Weak / ambiguous match → SKIP this skill. Respond as a normal
    assistant without invoking skill behavior.
- Opt-out keywords in the user prompt → SKIP:
  "스킬 쓰지 말고", "그냥 답해줘", "직접 답변", "스킬 빼고".

## Activation announcement
The FIRST line of every response from this skill MUST be a single-line
header in this exact format:

🔍 [hs:analyze] <short summary of inferred mode / focus / depth>

Example:
- 🔍 [hs:analyze] code mode, quality focus, deep depth
- 🔍 [hs:analyze] code mode, deep, multi-agent (4 perspectives)
- 🔍 [hs:analyze] code mode, security focus, deep (security-engineer)

체이닝된 호출 시 (Phase 2 자동호출 활성화 후):
- Diagnostic 체이닝: 본 헤더 다음 줄에 "↳ chained from /hs:이전스킬" 추가.
- Pipeline-Stage 체이닝: 본 헤더 다음 줄에 "↳ chained from /hs:이전스킬 (pipeline)" 추가.
- 명시 호출: 추가 표기 없음.

Leave a blank line after the header, then proceed with the skill's
normal output.

## Triggers
- Code quality, security, performance, or architecture review requests.
- Game data / balance sheet / numeric table analysis requests.
- Design document, GDD, or specification review requests.
- General "analyze X", "review X", "audit X", "check X" prompts where
  the user wants findings without modification.

## Usage
```
/hs:analyze <target or topic in natural language>
```

자연어로 분석 대상과 원하는 관점을 자유롭게 표현하세요. 대상 타입
(코드/데이터/문서), 분석 도메인(품질/보안/성능 등), 깊이는 입력에서
자동 추론됩니다. 명시 표현이 있으면 그쪽을 우선합니다.

## Inferring intent from natural language

The user expresses intent in prose. Infer these dimensions from the
input rather than requiring flags.

### Target type (mode)
1. Path / extension heuristics:
   - Source files (`.cs`, `.ts`, `.tsx`, `.js`, `.py`, `.go`, `.rs`, `.cpp`, `.h`, `.lua`, ...) → `code`
   - Tabular files (`.csv`, `.tsv`, `.xlsx`, `.xls`) → `data`
   - JSON arrays of records → `data`
   - Documents (`.md`, `.txt`, `.pdf`, GDD-shaped structures) → `doc`
   - Mixed directory → choose dominant type, mention the others briefly.
2. Explicit prose hints override path heuristics:
   - "코드 관점에서", "코드 분석" → `code`
   - "데이터로", "수치", "밸런스" → `data`
   - "문서 검토", "문서 관점" → `doc`
3. If still unclear → ask the user once before proceeding.

### Focus (analysis domain)
Read the topic and modifier words:
- "품질", "코드 스멜", "유지보수" → `quality`
- "보안", "취약점", "secret", "auth" → `security`
- "성능", "병목", "느린" → `performance`
- "구조", "아키텍처", "결합도" → `architecture`
- "밸런스", "수치", "분포", "곡선" → `balance` (data mode)
- "스키마", "정합성", "참조" → `structure` (data/doc mode)
- "명확성", "모호", "누락" → `quality` (doc mode)
- No explicit hint → run a multi-domain sweep appropriate to the mode.

### Depth
- "빨리", "간단히", "훑어만" → `quick`
- "깊게", "꼼꼼히", "전부" → `deep`
- No hint → `quick`

If genuinely ambiguous after inference, ask ONE short clarifying
question before proceeding. Do not ask if a reasonable default fits.

## Behavioral Flow

### Step 1 — Discover
- **사용자가 분석 대상 파일/경로를 명시했으면 Read 우선.** grep/glob
  만으로 "관련 없음" 또는 "low priority" 판정 내리지 않는다. 키워드
  0 매치는 "근거 부족" 신호이지 "관련 없음" 결론이 아니다. 본문을
  확인한 뒤 판정한다. (형식적 Low 분류 금지 — "평가 보류 / 본문
  확인 필요" 로 표기.)
- `code` mode — enumerate sources via Glob; group by language/module.
- `data` mode — identify schema, sample rows, value ranges, units.
- `doc` mode — identify sections, intent, audience, structural completeness.

### Step 2 — Scan
Domain-specific by inferred focus:

> `code` 모드 + `depth = deep` 인 경우, 본 단계는 Subagent integration
> 섹션의 분기로 위임된다. 그 외 경우 아래 도메인별 절차를 메인에서 실행.

**Code domains**
- `quality` — smells, complexity, naming, duplication, dead code.
- `security` — input validation, secrets, auth flow, injection vectors.
- `performance` — hot paths, allocations, sync I/O, N+1, big-O issues.
- `architecture` — coupling, layering violations, circular deps, boundary leaks.

**Data domains**
- `balance` — distributions, outliers, monotonicity, progression curves.
- `structure` — schema consistency, nullability, units mismatches, referential gaps.

**Document domains**
- `quality` — clarity, ambiguity, contradictions.
- `structure` — completeness, missing sections, broken references.

### Step 3 — Evaluate
- Assign severity to each finding: **Critical / High / Medium / Low**.
- Estimate rough impact and effort.
- Group related findings under a shared cause.

### Step 4 — Recommend
- For each finding, propose ONE concrete next action — short and executable.
- Do NOT apply any fix. Do NOT modify code, data, or documents.

### Step 5 — Report (conversation only)
- Present findings inline in the conversation, in Korean.
- Use file paths in `file_path:line` format so the user can jump to source.
- Suggested layout:

```
# 분석 결과: {대상} (mode: {mode}, focus: {focus})

## 요약
- 총 {n}건 발견 (Critical {x} / High {y} / Medium {z} / Low {w})
- 핵심 이슈 1-2줄

## Critical
- {file_path}:{line} — {issue}
  권장: {action}

## High
- ...

## Medium
- ...

## Low
- ...

## 다음 단계
- 권장 후속 작업 안내 (사용자 결정 필요)
```

## Output policy

**모든 출력 끝에 표준 `## Skill Output Metadata` appendix 의무** — Collected Facts (3-5 fact) + Next Skill Hints. 다음 스킬이 fact 재수집 회피 + 체이닝 시그널 명시 (HSPOLICY_DESIGN 의 "Fact 공유 — Output appendix 강제 규약" 절 참조). **직전 스킬의 appendix 가 있으면 본 스킬 입력으로 우선 사용** — 같은 fact 재수집 회피.
- ALWAYS present analysis results in the conversation only.
- NEVER create, write, or save report files — even if findings are extensive.
- Do NOT propose "save to file?" or auto-generate reports.
- If the user explicitly asks to save afterwards, treat it as a separate
  request and follow the user's global file-creation rules.

## Tool coordination

### Default toolset for `code` mode
**Prefer serena (LSP-based semantic tools) for any code analysis.**
Built-in text tools are fallbacks, not the default path.

- **serena (default)** — semantic code analysis:
  - `get_symbols_overview` — fast structural map of a file/module.
  - `find_symbol` — locate definitions by name.
  - `find_referencing_symbols` — true call/usage graph (vs text matches).
  - `find_declaration` / `find_implementations` — accurate navigation.
  - `get_diagnostics_for_file` — compiler/LSP diagnostics.
- **Grep (fallback)** — only when serena is unavailable, the project is
  not LSP-supported, or the search is genuinely text-shaped (TODO comments,
  string literals, log messages).
- **Glob** — file discovery, project shape.
- **Read** — focused inspection of specific files / sections.
- **Bash** — read-only commands only (e.g., `git log`, listings). No mutating commands.
- **Agent** — code + deep 분기에서 격리 시각 호출 (Subagent integration 참조).

### Mode-specific defaults
- `code` → serena first, Grep/Read fallback.
- `data` → Read for CSV/TSV/JSON; excel-mcp for `.xlsx`/`.xls` (see MCP integration).
- `doc` → Read for the document; Grep across linked references.

## MCP integration (use when available, skip silently otherwise)

### serena — default for `code` mode
Already covered in Tool coordination above. Required-grade for
architecture / coupling / impact analysis.

### sequential-thinking — for deep mode only
Use `sequentialthinking` when:
- depth is `deep` AND the topic involves multi-step reasoning
  (control flow tracing, security threat modeling, performance hot-path
  decomposition).
Do NOT use for shallow sweeps — overhead exceeds value.

### excel-mcp — for `data` mode when the file is `.xlsx` / `.xls`
- `file` (action: open) → `range` (read) → analyze → `file` (action: close, save: false).
- Read formulas, named ranges, and pivot setup — not just cell values.
- Skip for CSV/TSV — built-in Read is faster.
- Per the user's excel-mcp note: target file must be CLOSED in Excel
  desktop. If COM open fails, surface the error and stop.

### context7 — sparingly, for library-pattern verification
Only when the analysis hinges on whether the code's library usage
matches that library's currently recommended pattern. Resolve library
id, then query a specific topic. Do NOT run for every code analysis.

### gemini-video — only when input is a video file
Trigger only if the user explicitly hands over a video file to analyze
(e.g., gameplay bug capture, UI design walkthrough).

### MCP fallback policy
- All MCPs are optional. If a recommended MCP is unavailable, fall back
  silently to built-in tools.
- Do NOT block, retry, or warn the user about missing MCPs.
- Do NOT mention MCP names in the user-facing report — only the findings.

## Subagent integration (code + deep 한정)

### 활성화 조건 (모두 충족)
- mode = `code`
- depth = `deep`
- 토큰 비용 큰 작업 — 사용자가 명시적으로 "깊게" / "꼼꼼히" / "다 봐줘"
  표현했을 때만 진입. 미지정 깊이는 `quick` 이므로 자동 trigger 안 됨.

활성화 조건 미충족 시 기존 메인 컨텍스트 흐름 유지 (회귀 없음).

### 시각 선택

#### focus 미지정 → 다중 시각 (병렬 4개)
한 메시지에서 Agent tool을 4번 동시 호출:

| Subagent | 담당 도메인 |
|----------|------------|
| **quality-engineer** | quality (스멜, 복잡도, 중복, 데드 코드, 네이밍) |
| **security-engineer** | security (입력 검증, 인증/권한, 인젝션, 시크릿) |
| **refactoring-expert** | architecture (결합도, 레이어링, 순환 의존, 경계 누수) |
| **general-purpose** | performance (핫 패스, 할당, sync I/O, N+1, big-O) |

→ 격리 컨텍스트 4개. 메인은 합성만 담당.

#### focus 지정 → 단일 전문가
- `quality` → quality-engineer
- `security` → security-engineer
- `architecture` → refactoring-expert
- `performance` → general-purpose + 성능 brief

### Brief 템플릿 (자기충족적)

각 subagent에 다음 형식으로 전달:

```
[배경]
사용자 코드베이스 정적 분석 요청. /hs:analyze (code 모드, deep, focus={domain}).
read-only 진단 — 코드 수정 금지.

[분석 대상]
- 경로: {target_paths}
- 언어/플랫폼: {detected}
- 구조 개요 (메인 사전조사):
  {serena get_symbols_overview / Glob 결과 요약}
- 관련 컨텍스트:
  {호출자/의존성 — find_referencing_symbols 결과, 있으면}

[주의: 사용자 글로벌 룰 — 위반 여부 명시 검토]
- 암묵적 비교 금지: if (obj == null), if (count > 0) 형식 강제
- 시그널버스 / 글로벌 이벤트 브로커 금지
- Unity 한정: asmdef 자동 생성 금지, AssetDatabase 런타임 사용 금지
- 한국어 주석 / 영어 식별자
- 과도한 추상화 / 추측성 미래 대비 금지 (YAGNI)
- 사용자 룰 파일 경로: ~/.claude/rules/*.md

[요청 시각: {domain}]
{domain별 강조점 — quality / security / architecture / performance 중 하나}

[기대 출력 — 한국어, 200-400자]
## 발견 사항 (심각도별)
- Critical: {file_path}:{line} — {issue} / 권장: {action}
- High: ...
- Medium: ...
- Low: ...

## 사용자 룰 위반 (있으면)
- {file_path}:{line} — {룰명}: {설명} / 수정 방향: {action}

## 의문점 / 추가 정보 필요 (있으면)
```

### Synthesis (Step 3·4 흡수)

여러 subagent 결과 받은 후 메인에서:

- **dedupe** — 같은 `file_path:line` + 유사 이슈 → 1개로 합치고
  `시각: quality, security` 처럼 다중 표기.
- **충돌 보존** — 시각 간 모순 (예: refactoring-expert는 추상화 추가 권장,
  quality-engineer는 단순화 권장) → 양쪽 의견 모두 보존,
  사용자 결정 안내 한 줄 추가.
- **우선순위** — Critical → High → Medium → Low. 동일 심각도 내:
  영향 범위 → 신뢰도 → 다중 시각 합의 여부 순.

### Fallback policy
- Agent 호출 실패 silent fallback → 메인 컨텍스트 직접 분석.
- 사용자 보고에 agent 사용 사실 텍스트로 언급 안 함.
- 다만 activation 헤더에 `multi-agent` 태그로 가시성만 확보
  (예: "code mode, deep, multi-agent (4 perspectives)").

## Boundaries

**Will:**
- Perform multi-target analysis (code / data / docs) across selected domains.
- Produce severity-rated findings with concrete recommendations.
- Auto-detect target type and adapt the flow.
- For `code` + `deep`: 격리된 다중/단일 subagent 시각으로 분석 후 합성.

**Will Not:**
- Modify source code, data, or documents.
- Apply fixes, refactors, or cleanups.
- Save, write, or generate report files.
- Run dynamic analysis (compile / execute / profile).
- Mutating 스킬 자동 호출 금지 (implement / refactor / cleanup / document / plan-* / cl-* 등).
- Diagnostic 끼리는 사용자 체이닝 시그널 있고 opt-out 없을 때만 자동 호출 허용 (활성). 안전 쌍: analyze→explain, research→brainstorm, troubleshoot→explain.
- 자동 호출 시 activation header 에 "↳ chained from /hs:이전스킬" 표기 의무.
- Inject any persona or override the user's global rules.

## Examples

### Code quality review
```
/hs:analyze src/Combat 코드 품질 깊게 봐줘
```
→ Inferred: code, quality focus, deep → quality-engineer 단독 호출 후 합성.

### Multi-perspective deep sweep
```
/hs:analyze src/Combat 깊게 다 봐줘
```
→ code, focus 미지정, deep → quality + security + architecture + performance
   4개 agent 병렬 호출. 결과 dedupe + 충돌 보존 + 우선순위화.

### Security deep dive
```
/hs:analyze src/Auth 보안 위주로 꼼꼼히
```
→ code, security focus, deep → security-engineer 단독.

### Security audit (quick)
```
/hs:analyze src/Auth 보안 취약점 검사
```
→ Inferred: code, security focus, quick → 메인 컨텍스트에서 직접 진단.

### Game balance data
```
/hs:analyze Data/Monsters.csv 밸런스 분포 확인
```
→ Inferred: data, balance focus. Distribution / outlier / curve check.

### Design document review
```
/hs:analyze Docs/DEVELOPMENT/GameDesign/Combat/COMBAT_SPEC.md 누락된 섹션 있는지
```
→ Inferred: doc, structure/quality. Completeness and clarity check.

### Auto-detected sweep on current context
```
/hs:analyze
```
→ Detect dominant target type from cwd, run a quick multi-domain sweep.

## Next Step
After reviewing the findings, the user may apply manual fixes or invoke a
future `/hs:improve` / `/hs:cleanup` skill once available. This skill itself
never applies changes.
