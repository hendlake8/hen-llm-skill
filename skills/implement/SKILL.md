---
name: implement
description: "코드 구현 (구현, 추가, implement, build, create) - 새 기능 / 버그 수정 / functional change. 명시 호출 전용. 파일 생성/수정은 사용자 승인 후."
version: 0.1.0
---

# /hs:implement - Code Implementation (Functional Change)

## Operating principles
- The user's global rules in `~/.claude/CLAUDE.md` and `~/.claude/rules/*.md`
  are the authoritative persona. Follow them strictly.
- This skill provides procedural guidance only — no identity injection,
  no priority overrides.
- If guidance here conflicts with user rules, user rules win.
- Respond to the user in Korean.

## Activation guard (explicit-only)
This skill activates ONLY via explicit `/hs:implement` invocation.
- Auto-trigger: NEVER. Even if the user's prompt mentions "구현",
  "implement", "기능 추가", "build" etc., do NOT activate without the
  slash command. Instead, respond as a normal assistant. If appropriate,
  suggest the user invoke `/hs:implement` explicitly.
- Opt-out keywords still apply as a safety net:
  "스킬 쓰지 말고", "그냥 답해줘", "직접 답변", "스킬 빼고" → SKIP.

## Activation announcement
The FIRST line of every response from this skill MUST be a single-line
header in this exact format:

🔍 [hs:implement] <short summary of target / scope>

Examples:
- 🔍 [hs:implement] new feature: user profile component (Unity, C#)
- 🔍 [hs:implement] bug fix: null check in CombatController

체이닝된 호출 시 (Phase 2 자동호출 활성화 후):
- Diagnostic 체이닝: 본 헤더 다음 줄에 "↳ chained from /hs:이전스킬" 추가.
- Pipeline-Stage 체이닝: 본 헤더 다음 줄에 "↳ chained from /hs:이전스킬 (pipeline)" 추가.
- 명시 호출: 추가 표기 없음.

Leave a blank line after the header, then proceed with the skill's
normal output.

## Scope definition

### What this skill does
- **Functional change** — produces new behavior that did not exist
  before (new feature, bug fix, new code path, behavior modification).
- Includes new files when warranted, but also includes additions /
  modifications to existing files for the new behavior.

### What this skill does NOT do
- Pure code-quality improvements without behavior change → use
  `/hs:refactor` (non-functional change).
- Dead-code / import / formatting cleanup → use `/hs:cleanup`.
- Persistence of analysis or design docs → use `/hs:document`.
- Running tests automatically. The user runs tests when ready.
- Committing to git automatically.

## Triggers
- Feature implementation requests ("X 구현해줘", "Y 기능 추가").
- Bug fix requests ("이 버그 고쳐줘", "이 동작 수정").
- Behavior modification requests ("이 로직을 X로 바꿔줘").
- Implementing what's specified in `_SPEC.md` / `_DESIGN.md` / `_PLAN.md`.

## Usage
```
/hs:implement <what to build/change in natural language>
```

자연어로 무엇을 구현할지 자유롭게 표현하세요. 대상 파일, 언어/엔진,
범위는 입력 + 프로젝트 컨텍스트에서 자동 추론됩니다.

## Inferring intent from natural language

### Target language / framework
- Auto-detected from file extensions, project structure, package files.
- If the user says "C#로", "Unity에서", "Python으로" → that wins.
- If unclear → ask once before generating code.

### Scope
- "이 함수만", "이 메서드만" → narrow scope, single edit.
- "이 모듈에", "이 클래스에" → broader, multi-edit possible.
- "전체 시스템", "프로젝트 전반" → multi-file. Plan first, confirm.

### Spec source
- If the request references `_SPEC.md` / `_DESIGN.md` / `_PLAN.md`
  → those documents are the authoritative source. Read them first.
- If the request is freeform → user input is the spec.

If genuinely ambiguous after inference, ask ONE short clarifying
question before proceeding. Do not ask if a reasonable default fits.

## Behavioral Flow

### Step 1 — Understand
- Read the user's request carefully. Restate the intent in 1 line.
- Check for spec docs:
  - `Docs/DEVELOPMENT/Dev/{system}/*_SPEC.md`
  - `Docs/DEVELOPMENT/Dev/{system}/*_DESIGN.md`
  - `Docs/DEVELOPMENT/Dev/{system}/*_PLAN.md`
  - Read them if present. They are ground truth.
- Identify the relevant code area (use serena for code mode).

### Step 2 — Plan
- Decompose into the minimum set of file changes.
- For each file: classify as `create` / `modify` / `delete`.
- Identify edge cases the user implied but did not state.
- Identify integration points (callers, references) using
  `find_referencing_symbols` if available.

### Step 3 — Pre-flight approval (조건부 게이트)

기본 원칙: `/hs:implement X` slash 호출 자체가 글로벌 룰의 "명시 요구"
를 충족한다. 따라서 명확한 요청은 추가 승인 없이 즉시 진행하고, **요청
이 모호할 때만** 한 번 더 사용자 승인을 받는다.

평가 순서: 3a → 3b → 3c. 어느 단계에서 통과 결정이 나면 즉시 Step 4로
직행.

#### 3a. Check auto-run mode (skip-condition)

If a `/hs:plan-run` orchestration is active, blanket approval was
already obtained upfront and per-Phase approval should be skipped.

Detect this by querying:
```bash
python {PLUGIN_ROOT}/scripts/plan_state.py auto-run-status
```

- Response `active: true && stale: false` → **SKIP 3b/3c**.
  Proceed directly to Step 4. Do NOT show the approval prompt.
- Response `active: true && stale: true` → treat as inactive
  (24h timeout). Proceed with 3b normally.
- Response `active: false` or error (no plan registered) → proceed
  with 3b normally.

Step 5 verification ALWAYS runs regardless of this flag — failure
gates are not bypassed.

#### 3b. Opt-in 우회 키워드 검사

사용자 호출 **끝**에 다음 자연어 키워드 중 하나가 포함되어 있으면 게이트
전체를 스킵하고 Step 4로 직행:

- `바로`
- `진행`

(플래그 형식 — `--go`, `-y` 등 — 은 본 스킬 시스템의 "flags 대신 자연어
추론" 원칙에 따라 사용하지 않는다.)

키워드 위치는 호출 끝으로 제한해 본문에 일반 명사로 등장하는 경우와
구분한다. 예: `/hs:implement X 추가 진행` → 우회 발동.
`/hs:implement 진행 상황 화면 추가` → 우회 발동 아님 (본문 명사).

#### 3c. 모호 판정 (게이트 조건)

다음 5축을 평가:

1. **변경 대상** — 파일/심볼이 사용자 입력 또는 코드 컨텍스트로 식별
   가능한가?
2. **신규 명명** — 새 클래스/함수/필드 이름이 지정되었거나 명백히 도출
   가능한가?
3. **데이터 구조** — 스키마/enum/시그니처가 결정되었는가?
4. **라이브러리/패턴 선택** — 사용할 라이브러리/패턴이 명시 또는 명백히
   추론 가능한가?
5. **통합 지점** — 어디서 호출/배치할지 결정되었는가?

각 축 평가 규칙:
- SPEC/DESIGN/PLAN 문서로 채워진 항목 → 결정된 것으로 간주
- 사용자 호출 + 기존 코드 컨텍스트로 채워진 항목 → 결정된 것으로 간주
- 그 외 → 미결정

**판정**: 미결정 축이 **2개 이상**이면 모호 → 3d (승인 대기) 로 진행.
그렇지 않으면 Step 4로 직행.

명확한 경우 (5축 중 미결정 ≤ 1) 의 흐름:
- 별도 승인 메시지 출력 없음.
- Step 2에서 도출한 변경 계획은 Step 6 보고에 한 줄로 흡수.
- 변경 적용 → 검증 → 보고가 1턴 안에 완결.

#### 3d. 모호한 경우 — 변경 계획 제시 + 승인 대기

3c에서 미결정 축이 2개 이상이면 짧은 계획을 사용자에게 제시:

```
## 변경 계획
- 신규: {file_path} — {purpose}
- 수정: {file_path}:{section} — {change}
- 삭제: {file_path} — {reason}

## 모호 판정
- 미결정 축: {2개 이상의 축 + 각각 무엇이 비어 있는지}

## 영향 범위
- 호출자 N곳 영향: {brief list}

## 추론한 가정
- {assumption that might be wrong}

진행할까요?
```

WAIT for user approval before writing.

The slash invocation `/hs:implement X` is permission to PROPOSE.
명확한 요청에서는 그 자체가 WRITE 권한을 함께 부여하지만, 모호한
요청에서는 본 단계의 추가 승인이 WRITE 권한을 푼다.

### Step 4 — Generate / Modify
Apply changes per the approved plan. Coding conventions, comment
policy, and scope discipline are governed by the user's global rules
(loaded automatically) — defer to them, do not restate.

### Step 5 — Verify (no autonomous tests)
After changes, verify by:
- For C#: confirm syntax / brace matching / using directives.
- For TypeScript / Python / etc.: same syntactic sanity checks.
- Read back modified files mentally to confirm no orphaned references,
  no broken imports, no unfinished edits.
- Do NOT run tests, builds, or `git` commands automatically.
  The user decides when to test/commit.

### Step 6 — Report (conversation only)
Present a concise summary:

```
## 변경 완료
- 신규: {file_path}:{line range} — {purpose}
- 수정: {file_path}:{line range} — {change}

## 추가 확인 필요
- {anything that should be tested manually}
- {assumptions that should be validated}

## 다음 단계 (사용자 결정)
- 빌드/테스트 실행
- 추가 작업이 필요하면 후속 요청
```

Do NOT auto-invoke other skills. Do NOT auto-commit.

## Output policy

**모든 출력 끝에 표준 `## Skill Output Metadata` appendix 의무** — Collected Facts (3-5 fact) + Next Skill Hints. 다음 스킬이 fact 재수집 회피 + 체이닝 시그널 명시 (HSPOLICY_DESIGN 의 "Fact 공유 — Output appendix 강제 규약" 절 참조). **직전 스킬의 appendix 가 있으면 본 스킬 입력으로 우선 사용** — 같은 fact 재수집 회피.
- Code changes: applied via Write / Edit / MultiEdit AFTER pre-flight
  approval (Step 3).
- Reports / summaries: conversation only — no separate report file.
- Persistence (saving the plan, the report, etc.): if the user wants
  to save, they invoke `/hs:document` separately.

## Tool coordination

### Default toolset
- **serena (preferred for code understanding)** — use semantic tools
  before Edit:
  - `get_symbols_overview` — file structure.
  - `find_symbol` — locate target symbol.
  - `find_referencing_symbols` — impact analysis before changes.
  - `replace_symbol_body` / `insert_after_symbol` /
    `insert_before_symbol` — surgical edits.
- **Read** — full file inspection when serena's view is incomplete.
- **Glob / Grep** — discovery, fallback when serena unavailable.
- **Edit / MultiEdit** — modify existing files.
- **Write** — only for new files, only after Step 3 approval.

## MCP integration (use when conditions match)

### serena — strongly preferred for code edits
Already covered in Tool coordination. Use `replace_symbol_body` and
`insert_after_symbol` for symbol-level edits — safer than free-form
Edit when the symbol boundaries are clear.

### context7 — for framework / API specifics
When the implementation requires a specific library/framework's
current API or recommended pattern:
- `resolve-library-id` → `query-docs` with the relevant topic.
- Especially valuable for Unity, React, libraries the user
  references explicitly.

### sequential-thinking — for complex multi-component features
Use `sequentialthinking` when:
- The implementation spans multiple systems with intricate
  dependencies, AND
- A clean decomposition is non-obvious.
Skip for routine single-file changes.

### excel-mcp — only when implementing data table writers
When implementing code that reads/writes existing `.xlsx` data
(game data tables, balance sheets):
- Read-only flow for inspection: `file` open → `range` read → close.
- For schema decisions, read existing structure first.
Do NOT auto-modify Excel files unless the user explicitly authorized.

### MCP fallback policy
- All MCPs are optional. Silent fallback to built-in tools.
- Do NOT mention MCP names in user-facing output.

## Boundaries

**Will:**
- Implement requested features / fixes / behavior changes.
- Read spec docs (`_SPEC.md`, `_DESIGN.md`, `_PLAN.md`) as ground truth.
- Plan changes and obtain user approval before writing files.
- Use serena's symbol-level edits when applicable.
- Report what was changed, in `file_path:line` format.

**Will Not:**
- Write or modify files without Step 3 approval.
- Add features, error handling, or abstractions beyond the request.
- Refactor surrounding code that is not part of the requested change.
- Run tests, builds, or `git` commands autonomously.
- 어떤 스킬도 자동으로 호출하지 않음. 사용자 명시 호출만 진입 가능 (Mutating 스킬 — Pre-flight approval 게이트 필수).
- Save reports to files — that's `/hs:document`'s job.
- Inject any persona or override user rules.

## Examples

### New feature, freeform
```
/hs:implement 플레이어 이동에 대시 능력 추가
```
→ Read current PlayerController. Plan dash field + input handler +
   cooldown. Show plan. Wait for approval. Apply edits.

### From spec doc
```
/hs:implement Combat 시스템 SPEC대로 구현
```
→ Read `Docs/DEVELOPMENT/Dev/Combat/COMBAT_SPEC.md`. Treat it as
   ground truth. Plan from spec. Show plan. Apply.

### Bug fix
```
/hs:implement CombatController에서 null reference 버그 수정
```
→ Locate the bug via serena. Identify minimal fix. Show plan.
   Apply after approval.

### Single-line change (still goes through approval)
```
/hs:implement 이 함수 반환값을 int에서 long으로 바꿔줘
```
→ Even small changes go through Step 3. Show plan + caller impact.
   Apply after approval.

## Next Step
After implementation, the user may proceed to:
- Manual or scripted testing.
- `/hs:refactor` if the new code has improvement opportunities
  (separate concern from getting it working).
- `/hs:document` if the change should be persisted in design docs.
- Commit when satisfied.
This skill takes no further action automatically.
