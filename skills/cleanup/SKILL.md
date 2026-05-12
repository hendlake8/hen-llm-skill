---
name: cleanup
description: "코드 정리 (cleanup, 데드 코드 제거, unused import 정리, 주석 처리 코드 제거) - 명시 호출 전용. 행동 보존 + 미사용 검증 후 사용자 승인 시에만 삭제."
version: 0.1.0
---

# /hs:cleanup - Code Cleanup (Remove the Unneeded)

## Operating principles
- The user's global rules in `~/.claude/CLAUDE.md` and `~/.claude/rules/*.md`
  are the authoritative persona. Follow them strictly.
- This skill provides procedural guidance only — no identity injection,
  no priority overrides.
- If guidance here conflicts with user rules, user rules win.
- Respond to the user in Korean.

## Activation guard (explicit-only)
This skill activates ONLY via explicit `/hs:cleanup` invocation.
- Auto-trigger: NEVER. Even if the user's prompt mentions "정리",
  "cleanup", "데드 코드" etc., do NOT activate without the slash command.
  Instead, respond as a normal assistant. If appropriate, suggest the
  user invoke `/hs:cleanup` explicitly.
- Opt-out keywords still apply as a safety net:
  "스킬 쓰지 말고", "그냥 답해줘", "직접 답변", "스킬 빼고" → SKIP.

## Activation announcement
The FIRST line of every response from this skill MUST be a single-line
header in this exact format:

🔍 [hs:cleanup] <short summary of cleanup target / scope>

Examples:
- 🔍 [hs:cleanup] dead code + unused imports in src/Combat
- 🔍 [hs:cleanup] commented-out code blocks across project
- 🔍 [hs:cleanup] unused locals in CombatController

체이닝된 호출 시 (Phase 2 자동호출 활성화 후):
- Diagnostic 체이닝: 본 헤더 다음 줄에 "↳ chained from /hs:이전스킬" 추가.
- Pipeline-Stage 체이닝: 본 헤더 다음 줄에 "↳ chained from /hs:이전스킬 (pipeline)" 추가.
- 명시 호출: 추가 표기 없음.

Leave a blank line after the header, then proceed with the skill's
normal output.

## Scope definition

### What this skill does
- **Mechanical removal of the unneeded.** Behavior is preserved by
  definition because the removed code was not in use.
- Categories:
  - **Dead code** — unreferenced functions, classes, methods.
  - **Unused imports** — `using` / `import` / `require` statements
    not actually used in the file.
  - **Unused locals** — local variables / parameters never read.
  - **Commented-out code** — old code preserved as comments
    (distinct from intentional explanatory comments).
  - **Empty constructs** — empty try-catch, empty methods that are
    not abstract / interface implementations.
  - **Trailing whitespace / final-newline normalization** (low priority,
    only if user explicitly requests).

### What this skill does NOT do
- Restructure code (rename, extract, simplify) → use `/hs:refactor`.
- Add new behavior or fix bugs → use `/hs:implement`.
- Reformat code style (indent, brace style) — that's a formatter's job.
- Remove anything based on "looks unused" — must be VERIFIED unused.
- Remove items in the public API of a library / plugin / shared module
  unless the user explicitly authorizes treating them as removable.
- Run tests, builds, or `git` commands automatically.
- Commit automatically.

## Behavior-preservation invariant (CRITICAL)
Cleanup is safe ONLY when the removed code is genuinely unreferenced.
False positives cause silent breakage. Defaults bias toward
**conservative — when in doubt, do not delete**.

- A symbol is "unused" only if all of the following hold:
  - serena `find_referencing_symbols` returns no callers.
  - No reflection / dynamic-dispatch indicators (attributes,
    framework markers, runtime-resolved strings).
  - Not part of an exported public API surface.
  - Not invoked by tests or configuration.
- Framework markers that mean "used by the framework" — DO NOT delete:
  - Unity: `[SerializeField]`, `[MenuItem]`, `[InitializeOnLoad]`,
    lifecycle methods (`Awake`, `Start`, `Update`, `OnEnable`,
    `OnDisable`, `OnDestroy`, `FixedUpdate`, `LateUpdate`,
    `OnTriggerEnter`, `OnCollisionEnter`, etc.), Editor callbacks.
  - DI / IoC: `[Inject]`, `[Provides]`, `[Service]` etc.
  - Serialization: `[Serializable]`, `[JsonProperty]`, etc.
  - Reflection-driven: anything referenced by string in config files,
    addressable keys, or asset references.
- If a symbol could be referenced via reflection / runtime config that
  this skill cannot statically verify, mark it as **uncertain** and
  require explicit user confirmation before removal.

## Triggers
- Cleanup requests ("정리해줘", "데드 코드 제거", "안 쓰는 거 빼줘",
  "import 정리").
- Followups to `/hs:analyze` findings classified as dead code / unused.
- After `/hs:refactor` (extract/inline) leaves stranded helpers.
- After `/hs:implement` if the user asks to clean up scaffolding.

## Usage
```
/hs:cleanup <what to clean in natural language>
```

자연어로 정리 대상과 범위를 자유롭게 표현하세요. 정리 카테고리,
범위, 보수성 수준은 입력 + 코드 컨텍스트에서 자동 추론됩니다.

## Inferring intent from natural language

### Cleanup category
- "데드 코드", "안 쓰는 함수", "unused method" → `dead code`
- "import 정리", "using 정리", "unused import" → `unused imports`
- "안 쓰는 변수", "unused local" → `unused locals`
- "주석 처리된 코드", "commented out" → `commented-out code`
- "빈 함수", "empty method" → `empty constructs`
- 카테고리 미언급 → 사용자에게 어떤 카테고리를 다룰지 묻거나, 안전한
  것부터 (`unused imports` → `unused locals` → 그 외) 순으로 진행.

### Scope
- "이 파일", "이 클래스" → file-level.
- "이 모듈", "이 폴더" → directory-level.
- "프로젝트 전반" → multi-file. Plan first, confirm.

### Risk-aware default
- Unity / framework / DI 프로젝트가 감지되면 **boost conservatism**:
  - `[SerializeField]` 등 마커 자동 보호.
  - public 심볼은 기본 보호 (사용자가 "public도 포함" 명시 시만).
- 비프레임워크 단순 프로젝트는 표준 모드.

If genuinely ambiguous after inference, ask ONE short clarifying
question before proceeding. Do not ask if a reasonable default fits.

## Behavioral Flow

### Step 1 — Discover candidates
- For `dead code` / `unused locals`:
  - Use serena `get_symbols_overview` to enumerate symbols in scope.
  - Use `find_referencing_symbols` for each candidate.
  - Use `get_diagnostics_for_file` — many compilers / LSPs report
    unused symbols natively.
- For `unused imports`:
  - Read file. Identify imports. Verify each name appears in the
    file body (excluding the import line itself).
- For `commented-out code`:
  - Read file. Find comment blocks containing code-shaped content
    (matching language syntax, not natural-language comments).

### Step 2 — Filter for safety
For every candidate, run safety checks:

- Apply framework-marker filter (Unity attributes, DI markers, etc.).
- Confirm not part of public API surface.
- Search for string-based references (config files, asset refs):
  - For Unity: search YAML scenes / prefabs for the symbol name.
  - For general: Grep across non-source files for the literal symbol name.
- Classify each candidate by confidence:
  - **High** — references = 0, no markers, not public, no string refs.
  - **Medium** — references = 0 but has markers OR is public OR has
    string-shaped occurrences.
  - **Low / uncertain** — anything more ambiguous.

### Step 3 — Pre-flight approval (조건부 게이트)

기본 원칙: `/hs:cleanup X` slash 호출 자체가 글로벌 룰의 "명시 요구"
를 충족한다. 요청이 명확하면 추가 승인 없이 진행하지만, **cleanup
의 본질적 안전 원칙상 Medium / Low confidence 항목은 게이트 우회와
무관하게 항상 사용자 확인을 거친다** (False positive 시 silent 손
실 방지).

평가 순서: 3a → 3b → 3c. 통과 결정 시 Step 4 로 직행.

#### 3a. Check auto-run mode (skip-condition)

`/hs:plan-run` 활성 시 일괄 승인된 것으로 간주:

```bash
python {PLUGIN_ROOT}/scripts/plan_state.py auto-run-status
```

- `active: true && stale: false` → **SKIP 3b/3c**. Step 4 로 직행하되
  **High confidence 항목만** 제거. Medium/Low 는 보고에 명시만 하고
  보류.
- 그 외 → 3b 로 진행.

Step 5 (행동 보존 검증) 는 항상 실행.

#### 3b. Opt-in 우회 키워드 검사

사용자 호출 **끝**에 다음 자연어 키워드 중 하나가 포함되어 있으면
**High confidence 항목만 자동 제거 모드** 로 게이트 스킵:

- `바로`
- `진행`

Medium / Low confidence 항목은 본 우회와 무관하게 항상 보고에 명시
하되 제거하지 않음. 플래그 형식은 사용하지 않는다.

#### 3c. 모호 판정 (게이트 조건)

다음 5축을 평가:

1. **카테고리** — dead code / unused imports / unused locals /
   commented-out / empty constructs 중 어느 것인가?
2. **범위** — file / directory / project-wide 중 어디인가?
3. **보존 정책** — public 심볼 포함 여부 / 프레임워크 마커 처리 방침
   이 명시되었는가?
4. **Confidence 임계** — High-only / High+Medium 중 어디까지 자동
   제거할지 결정되었는가?
5. **결과 처리 방식** — 일괄 제거 / 카테고리별 / 항목별 선택 중
   결정되었는가?

평가 규칙: 사용자 호출 + 코드 컨텍스트 + 본 SKILL.md 의 Risk-aware
default 로 채워진 항목 → 결정. 그 외 → 미결정.

**판정**: 미결정 ≥ 2 → 3d 로 진행. 그렇지 않으면 Step 4 로 직행하며
디폴트는 **High-only 자동 제거**.

#### 3d. 모호한 경우 — 후보 분류 제시 + 사용자 결정 대기

3c 에서 미결정 축이 2개 이상이면 후보를 confidence 별로 묶어 옵션
제시:

```
## 정리 후보

### High confidence (안전하게 제거 가능)
- {file_path}:{line} — {symbol/import/block} ({reason: 0 callers, no markers})
- ...

### Medium confidence (확인 필요)
- {file_path}:{line} — {symbol} ({reason: public, but no internal callers})
- ...

### Low confidence (보존 권장)
- {file_path}:{line} — {symbol} ({reason: matches reflection pattern})
- ...

## 영향 추정
- 총 {N}건 식별, 제거 후 라인 수 약 {n}줄 감소

## 모호 판정
- 미결정 축: {2개 이상의 축}

## 어떻게 진행할까요?
1. High만 제거
2. High + Medium 제거 (Medium은 항목별 재확인)
3. 카테고리별 (dead code만 / imports만 등)
4. 항목별 선택
5. 취소
```

WAIT for user decision. Default if user says "go" without specifying:
**High confidence only**.

The slash invocation `/hs:cleanup X` is permission to PROPOSE.
명확한 요청에서는 그 자체가 High-only 제거 권한을 함께 부여하지만,
모호한 요청에서는 본 단계의 추가 결정이 어떤 confidence 까지 제거할
지를 푼다.

### Step 4 — Apply
Apply approved deletions only.

- Prefer serena `safe_delete_symbol` for symbol-level removal.
- For unused imports: Edit the import lines.
- For commented-out code blocks: Edit the comment lines.
- Do NOT touch anything not in the approved list.
- Do NOT "while I'm here" cleanup adjacent issues — that violates
  scope discipline. Surface them in the report instead.

### Step 5 — Verify behavior preservation
After deletions:
- Run `get_diagnostics_for_file` on every modified file. Zero new
  errors / warnings is the bar.
- For symbol deletions, confirm no remaining references appeared
  (e.g., a string reference we missed).
- If diagnostics show new errors, immediately revert that specific
  deletion and surface to the user.

### Step 6 — Report (conversation only)
Present a concise summary:

```
## 정리 완료
- High confidence: N건 제거 ({lines saved})
- Medium confidence: M건 처리 (제거 / 보류)
- 보류된 Low confidence: K건 ({file_path}:{line} — {reason})

## 진단 결과
- 컴파일러/LSP 진단 신규 에러: 없음 (또는 발견 시 상세)

## 추가 발견 (정리 대상 아님)
- {anything noticed during scan that the user might want to follow up}

## 다음 단계 (사용자 결정)
- 빌드/테스트 실행 권장
- 추가 정리가 필요하면 후속 요청
```

Do NOT auto-invoke other skills. Do NOT auto-commit.

## Output policy

**모든 출력 끝에 표준 `## Skill Output Metadata` appendix 의무** — Collected Facts (3-5 fact) + Next Skill Hints. 다음 스킬이 fact 재수집 회피 + 체이닝 시그널 명시 (HSPOLICY_DESIGN 의 "Fact 공유 — Output appendix 강제 규약" 절 참조). **직전 스킬의 appendix 가 있으면 본 스킬 입력으로 우선 사용** — 같은 fact 재수집 회피.
- Code changes: applied via Edit / MultiEdit / serena AFTER pre-flight
  approval (Step 3).
- Reports / summaries: conversation only — no separate report file.
- Persistence: if the user wants to save the cleanup summary, they
  invoke `/hs:document` separately.

## Tool coordination

### Default toolset
- **serena (strongly preferred)** — cleanup's safety depends on
  semantic reference data. Use:
  - `get_symbols_overview` — enumerate candidates.
  - `find_referencing_symbols` — confirm zero references.
  - `get_diagnostics_for_file` — compiler-detected unused warnings.
  - `safe_delete_symbol` — remove symbol cleanly.
- **Read** — full file inspection, especially for import / comment
  detection.
- **Grep** — string-based reference search across the project,
  including non-source files (configs, scenes, prefabs).
- **Glob** — file discovery.
- **Edit / MultiEdit** — non-symbol-level deletions (imports,
  comment blocks).

## MCP integration (use when conditions match)

### serena — required-grade for cleanup
Cleanup without semantic reference data is unsafe. If serena is
unavailable, escalate the bar:
- Skip `dead code` cleanup entirely (Grep is too unreliable for
  reference detection).
- Limit scope to `unused imports` + `commented-out code` + `unused
  locals` (which compilers/LSPs often flag without serena).
- Surface the limitation to the user.

### sequential-thinking — rarely needed
Cleanup is mechanical. Skip unless the user requests a complex
multi-pass cleanup with interlocking removals.

### context7 — not used
Cleanup is internal-only.

### MCP fallback policy
- All MCPs are optional. If serena is unavailable, see the elevated
  bar above.
- Silent fallback otherwise.
- Do NOT mention MCP names in user-facing output.

## Boundaries

**Will:**
- Identify and remove dead code, unused imports, unused locals,
  commented-out code, and empty constructs.
- Apply framework-marker / public-API safety filters by default.
- Classify candidates by confidence and require user approval.
- Verify post-deletion via compiler/LSP diagnostics.
- Default to **High confidence only** if the user says "go" without
  specifying.

**Will Not:**
- Delete anything without Step 3 approval.
- Delete framework-marked symbols (Unity attributes, DI markers, etc.).
- Delete public API symbols based purely on internal "unused" status.
- Delete reflection-/string-referenced code without explicit user
  confirmation.
- Refactor, reformat, or restructure code (use `/hs:refactor`).
- Add features or fix bugs (use `/hs:implement`).
- Run tests, builds, or `git` commands autonomously.
- 어떤 스킬도 자동으로 호출하지 않음. 사용자 명시 호출만 진입 가능 (Mutating 스킬 — Pre-flight approval 게이트 필수).
- Save reports to files — that's `/hs:document`'s job.
- Inject any persona or override user rules.

## Examples

### Dead code in a module
```
/hs:cleanup src/Combat 데드 코드 정리
```
→ serena enumerates symbols, finds zero-reference candidates.
   Filters out lifecycle methods and `[SerializeField]`. Shows plan.
   Removes after approval.

### Unused imports project-wide
```
/hs:cleanup 프로젝트 전체 unused using 정리
```
→ Per-file import scan. High-confidence removals batched. Approve
   per file or all at once.

### Commented-out code
```
/hs:cleanup 주석 처리된 코드 블록 다 제거
```
→ Detect code-shaped comment blocks. Show per-file list. Apply.

### Post-refactor stranded helper
```
/hs:cleanup 방금 inline 한 후에 안 쓰는 헬퍼 메서드 정리
```
→ Targeted scan after a refactor. Verify zero references via serena.
   Remove safely.

### After analyze
```
/hs:cleanup 방금 analyze에서 나온 dead code 항목들 정리
```
→ Use the analyze findings as the candidate list. Re-verify with
   serena before deletion (analyze findings can be stale).

## Next Step
After cleanup, the user may proceed to:
- Run tests / build to confirm no regressions.
- `/hs:refactor` if the now-cleaner code reveals restructuring opportunities.
- Commit when satisfied.
This skill takes no further action automatically.
