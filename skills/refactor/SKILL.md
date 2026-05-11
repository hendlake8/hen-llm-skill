---
name: refactor
description: "코드 리팩토링 (리팩토링, refactor, rename, extract, simplify, 구조 개선) - 행동 보존이 핵심. 명시 호출 전용. 파일 수정은 사용자 승인 후."
version: 0.1.0
---

# /hs:refactor - Code Refactoring (Non-functional Change)

## Operating principles
- The user's global rules in `~/.claude/CLAUDE.md` and `~/.claude/rules/*.md`
  are the authoritative persona. Follow them strictly.
- This skill provides procedural guidance only — no identity injection,
  no priority overrides.
- If guidance here conflicts with user rules, user rules win.
- Respond to the user in Korean.

## Activation guard (explicit-only)
This skill activates ONLY via explicit `/hs:refactor` invocation.
- Auto-trigger: NEVER. Even if the user's prompt mentions "리팩토링",
  "refactor", "정리해줘", "구조 개선" etc., do NOT activate without the
  slash command. Instead, respond as a normal assistant. If appropriate,
  suggest the user invoke `/hs:refactor` explicitly.
- Opt-out keywords still apply as a safety net:
  "스킬 쓰지 말고", "그냥 답해줘", "직접 답변", "스킬 빼고" → SKIP.

## Activation announcement
The FIRST line of every response from this skill MUST be a single-line
header in this exact format:

🔍 [hs:refactor] <short summary of refactor type / target>

Examples:
- 🔍 [hs:refactor] rename: PlayerCtrl → PlayerController (project-wide)
- 🔍 [hs:refactor] extract method: ApplyDamage in CombatController
- 🔍 [hs:refactor] simplify: nested conditionals in TurnManager
- 🔍 [hs:refactor] move: DamageCalculator → 02.Core/CombatSystem, multi-file, subagent

Leave a blank line after the header, then proceed with the skill's
normal output.

## Scope definition

### What this skill does
- **Non-functional change** — improves code quality, structure, or
  internal performance WHILE preserving externally observable behavior.
- Categories:
  - **rename** — symbol renaming (variable, method, class, file).
  - **extract** — extract method, class, variable, interface from
    cohesive code.
  - **inline** — collapse an unnecessary abstraction.
  - **move** — relocate a symbol between files / namespaces / folders.
  - **simplify** — replace complex logic with a clearer equivalent
    (de-nesting, early-return, redundant-condition removal).
  - **replace algorithm / data structure** — different implementation
    with identical external behavior (often perf-driven).
  - **reorganize** — reorder / regroup code without renaming.

### What this skill does NOT do
- Add new behavior, fix bugs, or change observable output → use `/hs:implement`.
- Remove dead code / unused imports / fix formatting → use `/hs:cleanup`.
- Change public API contracts (signatures, return types, exception
  surface) → that is a functional change; use `/hs:implement` and treat
  it explicitly as a breaking change.
- Run tests automatically. The user runs tests when ready.
- Commit to git automatically.

## Behavior-preservation invariant (CRITICAL)
This is the core safety property of every refactor.

- The set of inputs that produced output X must still produce output X.
- The set of side effects must remain identical (file writes, network,
  state mutations, logged messages with semantic meaning).
- Public API (exported / public symbols) must keep the same signature
  unless the user explicitly authorized a signature change.
- Performance characteristics may improve, but must not regress
  meaningfully without explicit user discussion.
- If a refactor cannot preserve behavior (e.g., the user asked for
  something that requires breaking the API), STOP and surface the
  conflict before proceeding.

## Triggers
- Refactoring requests ("리팩토링", "구조 개선", "이름 바꿔줘",
  "이 함수 쪼개줘", "더 깔끔하게").
- Symbol-level rename / move requests.
- Simplification of overly nested or duplicated logic.
- Performance refactors that preserve behavior (algorithm swap,
  data structure swap).
- Followups to `/hs:analyze` findings classified as quality /
  architecture issues.

## Usage
```
/hs:refactor <what to refactor in natural language>
```

자연어로 리팩토링 대상과 의도를 자유롭게 표현하세요. 리팩토링 카테고리,
범위, 깊이는 입력 + 코드 컨텍스트에서 자동 추론됩니다.

## Inferring intent from natural language

### Refactor category
- "이름 바꿔", "rename" → `rename`
- "쪼개", "분리", "extract" → `extract`
- "합쳐", "inline", "굳이 함수로" → `inline`
- "옮겨", "이동", "move" → `move`
- "더 깔끔하게", "단순하게", "simplify", "정리" → `simplify`
- "더 빠르게" + 행동 보존 가능 신호 → `replace algorithm/structure`
- "재정렬", "그룹화", "묶어" → `reorganize`
- 카테고리 불명 → 사용자에게 한 번 묻기

### Scope
- "이 함수만", "이 메서드만", "이 변수만" → narrow, single edit.
- "이 클래스에서", "이 파일에서" → file-level.
- "이 모듈 전반", "프로젝트 전반" → multi-file. Plan first, confirm.

### Risk hint
- Refactor의 자연 위험도 추정:
  - rename / move (project-wide) → high (참조 다수)
  - extract / inline → medium
  - simplify / reorganize → medium
  - 단일 메서드 내부 변경 → low
- High-risk 리팩토링은 Step 3에서 영향 범위를 더 상세히 보여줄 것.

If genuinely ambiguous after inference, ask ONE short clarifying
question before proceeding. Do not ask if a reasonable default fits.

## Behavioral Flow

### Step 1 — Understand
- Restate the refactor intent in 1 line.
- Identify the target symbol(s) / file(s) / region using serena.
- Confirm the public surface that MUST remain unchanged.

### Step 2 — Impact analysis

> Scope = multi-file 또는 project-wide rename / cross-module move
> 이거나 사용자가 "꼼꼼히 / 전수조사 / 안전하게 / 영향 다 봐줘" 표현
> 시 본 단계는 Subagent integration 섹션의 refactoring-expert 위임으로
> 수행. 그 외(narrow / file-level / low-risk)는 아래 절차를 메인에서
> 직접 수행.

- Use `find_referencing_symbols` to enumerate all callers / dependents.
- Note ownership boundaries (is this symbol used outside the project?
  exported as a library? Then signature changes are off-limits unless
  explicitly authorized).
- Identify tests that touch the target (if a tests/ folder exists).
- 위임된 경우: agent의 Findings를 받아 호출자 매핑 / 위험 분류를
  Step 3 plan의 `영향 범위` 와 `행동 보존 검증 계획`에 인용 흡수.

### Step 3 — Pre-flight approval
**MANDATORY before any file write.**

Present a before/after-style plan:

```
## 리팩토링 계획
- 카테고리: {rename / extract / move / simplify / ...}
- 대상: {file_path}:{symbol or line range}
- 의도: {one-line intent}

## 변경 미리보기
Before:
  {short snippet or symbol structure}

After:
  {short snippet or symbol structure}

## 영향 범위
- 호출자 N곳: {brief list}
- 외부 노출: {public/internal — affected? yes/no}
- 테스트: {affected test files, if any}

## 행동 보존 검증 계획
- {how we will confirm behavior is unchanged}
- {예: serena diagnostics 통과, 호출 시그니처 동일, 테스트 변경 없음}

진행할까요?
```

WAIT for user approval before writing.

The slash invocation `/hs:refactor X` is permission to PROPOSE,
not permission to WRITE. Approval at this step is what unlocks
file changes.

### Step 4 — Apply
Apply changes per the approved plan.

- For `rename` → use serena's `rename_symbol` (project-wide consistent).
- For `extract` / `inline` → use serena's `replace_symbol_body` plus
  `insert_before_symbol` / `insert_after_symbol` for the new units.
- For `move` → create destination, then delete source — both via serena
  when possible.
- For `simplify` / `reorganize` → free-form Edit / MultiEdit on the
  specific lines.
- Coding conventions, comment policy, scope discipline are governed by
  the user's global rules (loaded automatically) — defer to them.
- Do NOT add features. Do NOT fix unrelated bugs. Do NOT clean up dead
  code (that's `/hs:cleanup`).

### Step 5 — Verify behavior preservation
After changes:
- Run `get_diagnostics_for_file` (serena) on every modified file.
  Zero new errors / warnings is the bar.
- Re-read modified files and confirm:
  - Public symbols have the same signatures.
  - No removed code paths that callers depend on.
  - No accidentally introduced behavior change.
- For `rename`, confirm no occurrences of the old name remain (unless
  intentional, e.g., comments / strings).
- Do NOT run tests, builds, or `git` commands automatically — but
  recommend the user do so before committing.

### Step 6 — Report (conversation only)
Present a concise summary:

```
## 리팩토링 완료
- 카테고리: {category}
- 변경: {file_path}:{line range} — {what changed}
- 영향: 호출자 N곳 자동 갱신 / 수동 확인 M건

## 행동 보존 확인
- {how preservation was verified}
- {any residual concerns}

## 다음 단계 (사용자 결정)
- 테스트 실행 권장
- 추가 리팩토링이 필요하면 후속 요청
```

Do NOT auto-invoke other skills. Do NOT auto-commit.

## Output policy
- Code changes: applied via Write / Edit / MultiEdit / serena AFTER
  pre-flight approval (Step 3).
- Reports / summaries: conversation only — no separate report file.
- Persistence: if the user wants to save the plan or summary, they
  invoke `/hs:document` separately.

## Tool coordination

### Default toolset
- **serena (strongly preferred)** — refactoring is serena's strongest
  domain. Use:
  - `get_symbols_overview` — file structure.
  - `find_symbol` — locate target.
  - `find_referencing_symbols` — full call graph for impact.
  - `rename_symbol` — safe project-wide rename.
  - `replace_symbol_body` — body-only edit, signature preserved.
  - `insert_after_symbol` / `insert_before_symbol` — surgical insertion.
  - `safe_delete_symbol` — when extract/inline removes the original.
  - `get_diagnostics_for_file` — post-change verification.
- **Read** — full file inspection when serena's view is incomplete.
- **Glob / Grep** — discovery, fallback when serena unavailable.
- **Edit / MultiEdit** — for non-symbol-level edits (formatting,
  whitespace, in-method logic).
- **Agent** — high-risk impact 분석 분기에서 refactoring-expert 위임
  (Subagent integration 참조). 위임은 Step 2 한정.

## MCP integration (use when conditions match)

### serena — required-grade for refactor
Already covered above. For project-wide rename / move, serena's
`rename_symbol` is far safer than Grep+Edit. Use it.

### sequential-thinking — for complex multi-step refactors
Use `sequentialthinking` when:
- The refactor spans multiple modules with intricate dependencies, AND
- Decomposing the refactor into safe sub-steps is non-obvious.
Skip for routine single-file refactors.

### context7 — rarely useful here
Refactor is mostly internal. context7 helps only when the refactor
involves swapping a library API call for an updated equivalent
(e.g., deprecated → current). In that case, behavior must still
be confirmed identical.

### MCP fallback policy
- All MCPs are optional. Silent fallback to built-in tools.
- Do NOT mention MCP names in user-facing output.
- For `rename` without serena: be very cautious. Grep-based rename
  has high false-positive risk. Prefer to surface the limitation to
  the user and ask for explicit confirmation per file.

## Subagent integration (high-risk impact 위임)

### 활성화 조건 (OR — 하나만 충족해도 진입)
- **Scope**: scope = multi-file 또는 project-wide.
- **Category 위험도**: rename (project-wide) 또는 move (cross-module).
- **사용자 명시 표현**: "꼼꼼히", "전수조사", "깊게", "안전하게",
  "영향 다 봐줘", "위험 검토".

위 조건이 모두 미충족이면 메인에서 직접 Step 2 수행 (회귀 없음).
narrow scope · low risk 리팩토링은 위임 오버헤드가 가치보다 큼.

### 위임 범위 — Step 2 (Impact analysis) 한정
- agent는 **read-only 진단만** 담당:
  - 호출자 / 의존성 매핑
  - 리팩토링 카테고리 적합성 검증
  - Behavior preservation 리스크 분류 (S / M / L)
  - 추측성 추상화 제안 차단 (사용자 룰 인용)
- 다음은 메인에서 직접 수행 (위임 금지):
  - Step 3 (Plan 본문 작성 / 사용자 승인)
  - Step 4 (Apply — 코드 수정)
  - Step 5 (Verify — serena diagnostics)
  - Step 6 (Report)

agent 결과는 Step 3 plan의 `## 영향 범위` 와 `## 행동 보존 검증 계획`
섹션에 인용 형태로 흡수.

### Agent 선택
- 기본: `refactoring-expert` 단독.
- 다중 시각 호출 안 함 (refactor는 단일 도메인 — analyze와 다른 점).
- 사용자가 후속으로 "구조 영향까지 봐달라" 명시하면 `system-architect`
  추가 호출은 별도 turn에서 처리 (자동 다중 분기 안 함).

### Brief 템플릿 (자기충족적)

```
[배경]
사용자 리팩토링 요청 — Impact analysis 단계 격리 위임.
/hs:refactor (category={category}, scope={scope}, risk={risk}).
read-only 진단 — 코드 수정 금지 (수정은 메인 담당).

[리팩토링 의도]
- 카테고리: {rename / extract / inline / move / simplify / reorganize / replace}
- 대상: {file_path}:{symbol or line range}
- 의도: {one-line — 사용자 표현 그대로}
- Public surface 보존 요구: {yes/no — 변경 가능 범위}

[현재 코드 (메인 사전조사)]
- 구조 개요: {serena get_symbols_overview 결과}
- 호출자 후보: {find_referencing_symbols 결과 — file:line 목록}
- 영향 받을 모듈: {namespace / 폴더 목록}
- 관련 테스트 파일: {있으면}

[주의: 사용자 글로벌 룰 — 위반 권장 차단]
- "Three similar lines is better than a premature abstraction"
- YAGNI — 추측성 추상화 / 패턴 적용 권장 금지
- SOLID 강제 금지 (사용자가 명시 요구하지 않은 추상화는 권장 X)
- Behavior preservation 절대 — 외부 동작 변경 제안 차단
- Unity: asmdef 자동 생성 금지, AssetDatabase 런타임 사용 금지
- 사용자 룰 파일 경로: ~/.claude/rules/*.md

[요청 분석]
1. 호출자 / 의존성 완전성 — 메인 사전조사 결과의 누락 후보 식별.
2. Behavior preservation 리스크 — 카테고리별 위험 지점.
   - rename: 문자열 참조 / 리플렉션 / 외부 직렬화 키 사용 여부
   - extract: 캡처 변수 / private 상태 의존
   - move: 네임스페이스 변경 / using 갱신 누락 / 외부 import
   - simplify: 부작용 순서 / 단축평가 의미 / 예외 경로
   - replace 알고리즘: 반복 순서 / 중복 처리 / 안정성
3. 리팩토링 카테고리 적합성 — 사용자가 제안한 카테고리가 의도에 맞는지.
4. 추측성 권장 차단 — 본 의도 외 "겸사겸사" 권장 금지.

[기대 출력 — 한국어, refactoring-expert 표준 포맷]
## Refactoring Findings

### Real Issues (concrete complexity / duplication)
- {file_path}:{line range} — {issue}
  Category: {category}
  Suggestion: {specific action — 이번 리팩토링 의도 범위 내}
  Risk: {S / M / L + behavior preservation concerns}
  Effort: {S / M / L}

### 영향 범위 매핑
- 호출자: {file_path}:{line} — {호출 방식}
- 누락 가능성: {메인이 못 잡은 후보 — 리플렉션 / 문자열 / 직렬화 키}

### Behavior Preservation 검증 계획
- {확인 방법 1}
- {확인 방법 2}

### Out of Scope (의도 외 권장 금지)
- {요청에 없는 개선 후보는 여기에만 적되, 권장 톤 사용 금지}
```

### Fallback policy
- Agent 호출 실패 silent fallback → 메인에서 직접 Step 2 수행.
- 사용자 보고 텍스트에 agent 사용 사실 언급 안 함.
- 활성 조건 충족 시 activation 헤더에 `subagent` 태그로 가시성 확보
  (예: "move: DamageCalculator → 02.Core/CombatSystem, multi-file, subagent").

## Boundaries

**Will:**
- Refactor code while preserving externally observable behavior.
- Use serena's symbol-level operations as the default.
- Plan changes and obtain user approval (Step 3) before writing.
- Verify behavior preservation via diagnostics and signature checks.
- Report what changed and what to verify manually.
- 위험 큰 리팩토링(multi-file / project-wide rename / cross-module move)
  은 Step 2 영향 분석을 refactoring-expert에 격리 위임 후 합성.

**Will Not:**
- Change public API signatures unless the user explicitly authorized
  it (and even then, treat it as a breaking change, not a refactor).
- Add new features, fix unrelated bugs, or modify behavior.
- Remove dead code, unused imports, or fix formatting (use `/hs:cleanup`).
- Run tests, builds, or `git` commands autonomously.
- Refactor surrounding code that was not part of the request
  ("scope creep").
- Auto-invoke other skills (`/hs:test`, `/hs:document`, etc.).
- Save reports to files — that's `/hs:document`'s job.
- Inject any persona or override user rules.
- Subagent에 코드 수정 권한 위임 (Step 4 Apply는 메인 전용).

## Examples

### Project-wide rename
```
/hs:refactor PlayerCtrl을 PlayerController로 전부 이름 바꿔줘
```
→ scope=project-wide → Step 2 refactoring-expert 위임 (호출자 / 문자열
   참조 / 리플렉션 후보 누락 검토). 메인이 plan 작성 → 승인 → serena
   `rename_symbol`로 적용 → diagnostics 검증.

### Cross-module move (subagent 위임)
```
/hs:refactor DamageCalculator를 다른 어셈블리로 옮기는데 안전하게 꼼꼼히
```
→ scope=multi-file + 사용자 명시 표현 → refactoring-expert 위임으로
   네임스페이스 변경 / using 갱신 / 외부 import 영향 매핑. 메인이
   Step 3 plan에 흡수 → 사용자 승인 → serena 이동 + 참조 갱신 → 검증.

### Extract method
```
/hs:refactor ApplyDamage 함수가 너무 길어서 데미지 계산 부분만 분리
```
→ Identify cohesive block. Extract as named method on the same class.
   Update internal call. Public API unchanged.

### Simplify nested logic
```
/hs:refactor TurnManager의 if 중첩이 너무 깊은데 정리해줘
```
→ Apply guard clauses / early returns / boolean simplification.
   Behavior identical. Cyclomatic complexity drops.

### Move to better location
```
/hs:refactor DamageCalculator 클래스 02.Core/CombatSystem 폴더로 옮겨줘
```
→ serena move. Update namespace. Update references. Verify.

### Replace data structure (perf)
```
/hs:refactor _enemyList를 List에서 Dictionary로 바꿔서 ID 조회 빠르게
```
→ Confirm behavior-preserving (iteration order matters? duplicates?).
   If safe, swap and adjust call sites. If iteration order leaks
   externally, surface the conflict and stop.

### Single-line simplify
```
/hs:refactor 이 삼항연산자 너무 복잡해서 if/else로 풀어줘
```
→ Even tiny refactors go through Step 3 (briefly).

## Next Step
After refactoring, the user may proceed to:
- Run tests / build to confirm no regressions.
- `/hs:cleanup` if there is dead code / unused imports left over.
- `/hs:implement` if a follow-up functional change is needed.
- `/hs:document` if the structural change should be reflected in design docs.
- Commit when satisfied.
This skill takes no further action automatically.
