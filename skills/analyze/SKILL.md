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
- `code` mode — enumerate sources via Glob; group by language/module.
- `data` mode — identify schema, sample rows, value ranges, units.
- `doc` mode — identify sections, intent, audience, structural completeness.

### Step 2 — Scan
Domain-specific by inferred focus:

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

## Boundaries

**Will:**
- Perform multi-target analysis (code / data / docs) across selected domains.
- Produce severity-rated findings with concrete recommendations.
- Auto-detect target type and adapt the flow.

**Will Not:**
- Modify source code, data, or documents.
- Apply fixes, refactors, or cleanups.
- Save, write, or generate report files.
- Run dynamic analysis (compile / execute / profile).
- Inject any persona or override the user's global rules.

## Examples

### Code quality review
```
/hs:analyze src/Combat 코드 품질 깊게 봐줘
```
→ Inferred: code, quality focus, deep. Findings shown inline.

### Security audit
```
/hs:analyze src/Auth 보안 취약점 검사
```
→ Inferred: code, security focus. Severity-rated findings.

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
