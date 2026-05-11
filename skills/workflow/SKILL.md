---
name: workflow
description: "구현 계획서 작성 (workflow, 작업 순서, Phase 분해, PLAN 작성) - design 결과를 받아 *_PLAN.md 호환 마크다운으로 변환. 명시 호출 전용. 출력 대화 전용, 저장은 /hs:document, 실행 추적은 /hs:plan."
version: 0.1.0
---

# /hs:workflow - Implementation Plan Authoring

## Operating principles
- The user's global rules in `~/.claude/CLAUDE.md` and `~/.claude/rules/*.md`
  are the authoritative persona. Follow them strictly.
- This skill provides procedural guidance only — no identity injection,
  no priority overrides.
- If guidance here conflicts with user rules, user rules win.
- Respond to the user in Korean.

## Activation guard (explicit-only)
This skill activates ONLY via explicit `/hs:workflow` invocation.
- Auto-trigger: NEVER. Even if the user's prompt mentions "워크플로",
  "구현 계획", "Phase 분해" etc., do NOT activate without the slash
  command. Instead, respond as a normal assistant. If appropriate,
  suggest the user invoke `/hs:workflow` explicitly.
- Opt-out keywords still apply as a safety net:
  "스킬 쓰지 말고", "그냥 답해줘", "직접 답변", "스킬 빼고" → SKIP.

## Activation announcement
The FIRST line of every response from this skill MUST be a single-line
header in this exact format:

🔍 [hs:workflow] <short summary of system / scope / depth>

Examples:
- 🔍 [hs:workflow] Combat 시스템 PLAN 작성 (DESIGN 기반)
- 🔍 [hs:workflow] 결제 API PLAN (SPEC만 있음, design 없이 진행)

체이닝된 호출 시 (Phase 2 자동호출 활성화 후):
- Diagnostic 체이닝: 본 헤더 다음 줄에 "↳ chained from /hs:이전스킬" 추가.
- Pipeline-Stage 체이닝: 본 헤더 다음 줄에 "↳ chained from /hs:이전스킬 (pipeline)" 추가.
- 명시 호출: 추가 표기 없음.

Leave a blank line after the header, then proceed with the skill's
normal output.

## Workflow position

This skill is the **third stage** of the user's typical flow, and the
**authoring layer** for implementation plans:

```
brainstorm → design → workflow → /hs:document → /hs:plan → implement
요구사항      구현설계   계획서작성     저장          실행추적     코드 변경
*_SPEC.md    *_DESIGN.md           *_PLAN.md   .hs/progress.yaml
```

- **Inputs**: `*_DESIGN.md`, `*_SPEC.md`, recent `/hs:design` or
  `/hs:brainstorm` context, or freeform user input.
- **Outputs**: PLAN-compatible markdown text (conversation only).
- **Successor**: `/hs:document` to save as `*_PLAN.md`, then `/hs:plan`
  to load and track execution across sessions.
- **Layer separation**: this skill **authors** the plan. It does NOT
  track execution state — that's `/hs:plan`.

## Scope definition

### What this skill does
- Decompose a system / feature into **Phases** with explicit `X-Y` IDs
  (matching the user's documented PLAN.md grammar).
- Decompose each Phase into actionable **tasks** as `-` bullets (SSOT — 진행 상태는 progress.yaml 이 단독 관리, PLAN.md 에 체크박스 X).
- Produce a complete `*_PLAN.md`-shaped markdown text in the conversation,
  ready to be saved by `/hs:document` and loaded by `/hs:plan`.
- Auto-detect predecessor artifacts (DESIGN / SPEC / recent skill context).

### What this skill does NOT do
- Save / write the PLAN file → use `/hs:document` (single-channel save).
- Track execution / Phase status → use `/hs:plan`.
- Write implementation code → use `/hs:implement`.
- Modify any source file.
- Run / test / build anything.
- Inject any persona or override user rules.

## Triggers
- Plan-authoring requests after design completes
  ("이걸로 PLAN 짜줘", "구현 계획 짜자", "Phase로 분해").
- Direct invocation when only a SPEC exists (design 생략 가능).
- Freeform invocation for small features with neither SPEC nor DESIGN.
- Explicit references to existing `*_DESIGN.md` or `*_SPEC.md`.

## Usage
```
/hs:workflow <what to plan in natural language>
```

자연어로 무엇을 계획할지 자유롭게 표현하세요. 시스템 이름, 깊이,
Phase 입도는 입력 + 컨텍스트에서 자동 추론됩니다.

## Inferring intent from natural language

### Granularity (Phase 입도)
- "큰 흐름만", "대략" → coarse (Phase 3–5개, Phase당 태스크 3–5개)
- 기본 → normal (Phase 5–10개, Phase당 태스크 4–8개)
- "꼼꼼히", "자세히", "전부" → fine (Phase 10+개, Phase당 태스크 더 많이)

### Source priority
- 사용자가 SPEC/DESIGN 파일을 명시 → 그것 우선.
- 직전 `/hs:design` 대화 컨텍스트가 있으면 → 그것 우선.
- 둘 다 없고 freeform → user input이 입력.

### Scope
- "이 시스템", "이 기능" → 단일 시스템.
- "프로젝트 전반" → multi-system, scope 합의 필요.

If genuinely ambiguous after inference, ask ONE short clarifying
question before proceeding. Do not ask if a reasonable default fits.

## Predecessor artifacts (auto-detect)

Before authoring, check for inputs in this priority order:

1. **Existing DESIGN** — `Docs/DEVELOPMENT/Dev/{system}/*_DESIGN.md`.
   If found, READ FULLY.
2. **Existing SPEC** — `Docs/DEVELOPMENT/Dev/{system}/*_SPEC.md`.
   If found alongside DESIGN, both inform the plan; if only SPEC,
   work from SPEC alone (design step skipped is OK for small features).
3. **Recent skill context** — `/hs:design` or `/hs:brainstorm` synthesis
   in the immediate conversation.
4. **Existing code** — if planning extensions to existing modules,
   use serena `get_symbols_overview` and `find_referencing_symbols`
   to scope realistic Phases.
5. **Freeform user input** — if none of the above, the user's prompt
   itself is the source.

If multiple sources exist, reconcile and surface conflicts to the
user before authoring.

## Behavioral Flow

### Step 1 — Analyze
- Read predecessor artifacts (above).
- Restate the planning intent in 1 line.
- Identify the system name (will be used in title and Doc path).
- Note constraints (deadline, environment splits, deployment stages).

### Step 2 — Scope confirmation
**Lightweight handshake before authoring.**

```
## PLAN 작성 범위
- 시스템: {system name}
- 입력 근거:
  - {DESIGN.md path, if any}
  - {SPEC.md path, if any}
  - {recent skill context, if any}
  - {freeform input}
- 입도: {coarse / normal / fine}
- 다룰 영역: {what's included}
- 다루지 않을 영역: {explicitly out-of-scope}

이대로 진행할까요?
```

WAIT for user confirmation if scope is ambiguous; otherwise proceed.

### Step 3 — Decompose into Phases
- Group work by **logical concerns** (data model, core logic, integration,
  UI, polish, etc.) — NOT by file count.
- Assign Phase IDs as `X-Y`:
  - **X** = group identifier. Phases in the same X group can run in
    parallel.
  - **Y** = order within the group. Higher Y depends on lower Y.
  - Different X groups run sequentially: X=2 starts only after all
    X=1 Phases complete.
- This grammar is mandated by the user's `/hs:plan` parser
  (auto-dependency: `Phase X-Y` depends on `Phase X-(Y-1)`).
- Aim for Phases that map to clear, demoable milestones.

### Step 4 — Decompose into tasks
For each Phase, enumerate concrete actionable tasks as `-` bullet items.

- Each task is small enough to be done in one focused session
  (rough heuristic: a task is one to a few file edits, or one well-defined
  research / verification action).
- Tasks within a Phase are listed in execution order.
- Use Korean task descriptions (per global rule).
- Avoid vague tasks like "최적화 작업" — split into specific actions.

### Step 5 — Validate
Walk an explicit checklist:

- **Requirement coverage** — every requirement from SPEC/DESIGN appears
  in at least one task. Mark gaps explicitly.
- **Dependency sanity** — no cycles. Sequential X-groups are correct.
  Same-group Phases are genuinely independent.
- **Phase balance** — no Phase is dramatically larger than others.
  If one Phase has 20 tasks and others have 3, split it.
- **Granularity check** — no task is too large to fit in one focused
  session; no task is too trivial to merit a checkbox.
- **Out-of-scope leaks** — confirm nothing crept in beyond the agreed
  scope.
- Surface issues; do not paper over them.

### Step 6 — Report (conversation only)
Present the full PLAN markdown using the structure below. The output
should be ready to save as `*_PLAN.md` via `/hs:document` without
restructuring.

## Output structure

```
# {시스템명} 구현 계획서

## 개요
- 목적: {one-line purpose}
- 참조 설계 문서: {DESIGN.md path or "없음 (SPEC 기반)" or "freeform"}
- 참조 명세 문서: {SPEC.md path, if any}

## 제약 / 가정
- 제약: {hard constraints — deadline, platform, deps}
- 가정: {assumptions the plan depends on}

## 리스크
- {risk} — 완화: {mitigation}

## 구현 순서

### Phase 1-1: 작업명 (환경)
- 태스크 1
- 태스크 2
- 태스크 3

### Phase 1-2: 다음 작업명 (환경)
- 태스크 1
- 태스크 2

### Phase 2-1: 다른 그룹 작업 (환경)
- 태스크 1

### Phase 2-2: 후속 작업 (환경)
- 태스크 1

## 미해결 / 추후 결정 사항
- {open decision} — {options + recommendation if any}

## 다음 단계 (사용자 결정)
- 저장: `/hs:document`로 `*_PLAN.md` 저장
- 실행 추적 시작: 저장 후 `/hs:plan-load <path>`
- 작은 작업은 바로 `/hs:implement` 진행도 가능
```

Notes on the structure:
- The `## 구현 순서` header is REQUIRED verbatim — it is the parser
  anchor that `/hs:plan-load` looks for (per the user's global rule).
- Phase headers must be `### Phase X-Y: 이름` exactly. The "(환경)"
  parenthetical is optional but supports the user's documented format.
- Task lines must use `-` simple bullet — `/hs:plan-load` 가 task entry 로
  인식. 체크박스 형식 (`- [ ]` / `- [x]`) 은 backward compat 으로 여전히
  인식되지만 신규 PLAN.md 는 단순 bullet 만 사용. PLAN.md 에 진행 마킹
  안 함 (SSOT: progress.yaml 단독).
- Omit `## 제약 / 가정`, `## 리스크`, `## 미해결` sections if they
  would be empty — they are optional per the user's PLAN.md format.

## Output policy

**모든 출력 끝에 표준 `## Skill Output Metadata` appendix 의무** — Collected Facts (3-5 fact) + Next Skill Hints. 다음 스킬이 fact 재수집 회피 + 체이닝 시그널 명시 (HSPOLICY_DESIGN 의 "Fact 공유 — Output appendix 강제 규약" 절 참조). **직전 스킬의 appendix 가 있으면 본 스킬 입력으로 우선 사용** — 같은 fact 재수집 회피.
- ALWAYS present the PLAN markdown in the conversation only.
- NEVER create, write, or save PLAN files — even if the result is long.
- Do NOT propose "save to file?" or auto-generate `*_PLAN.md`.
- If the user wants to persist, they invoke `/hs:document` separately.

## Tool coordination

### Default toolset
- **Read** — predecessor SPEC/DESIGN docs.
- **serena** — for understanding existing code that the plan must
  integrate with:
  - `get_symbols_overview` — identify modules to extend.
  - `find_referencing_symbols` — gauge integration impact for sizing.
- **Glob / Grep** — discovery, fallback when serena unavailable.
- **No write tools** — workflow produces conversation output only.

## MCP integration (use when conditions match)

### serena — when planning within an existing project
Already covered in Tool coordination. Strongly preferred when the
plan extends or modifies existing modules — informs realistic Phase
decomposition.

### sequential-thinking — for complex multi-system plans
Use `sequentialthinking` when:
- The plan spans multiple subsystems with intricate dependencies, AND
- A clean Phase decomposition is non-obvious.
Skip for routine feature plans.

### context7 — sparingly
Use only when the plan hinges on a specific library/framework's
upgrade/migration steps that need authoritative ordering.

### MCP fallback policy
- All MCPs are optional. Silent fallback to built-in tools.
- Do NOT mention MCP names in user-facing output.

## Boundaries

**Will:**
- Author PLAN-compatible markdown strictly following the user's
  documented PLAN.md grammar (`## 구현 순서`, `### Phase X-Y: 이름`,
  `-` bullet tasks).
- Auto-detect DESIGN / SPEC / recent skill context as inputs.
- Decompose work into balanced Phases with sane dependency structure.
- Validate the plan against requirements, dependency cycles, and
  Phase balance.
- Hand off cleanly to `/hs:document` for persistence and `/hs:plan`
  for execution tracking.

**Will Not:**
- Save, write, or generate the PLAN file (use `/hs:document`).
- Track execution state, Phase status, or `.hs/progress.yaml`
  (that is `/hs:plan`'s job).
- Write implementation code (use `/hs:implement`).
- Modify existing source files.
- Run / test / build anything.
- Inject any persona or override user rules.
- Pipeline-Stage 스킬 — 산출물이 다음 단계 입력 사양인 본 스킬은 후속이 mutating 이어도 사용자 체이닝 시그널 시 자동 호출 허용 (활성). 활성 체이닝: workflow → plan-load, workflow → document. 단 호출 직전에 mutating 스킬의 자체 Pre-flight approval (Step 3) 은 그대로 수행 — 자동 호출이 변경 승인을 건너뛰는 것은 아님.
- 자동 호출 시 activation header 에 "↳ chained from /hs:이전스킬 (pipeline)" 표기 의무.

## Examples

### From DESIGN doc
```
/hs:workflow Combat 시스템 PLAN 짜줘
```
→ Reads `Docs/DEVELOPMENT/Dev/Combat/COMBAT_DESIGN.md` (and SPEC
   if present). Confirms scope. Authors PLAN markdown. Validates
   coverage. Reports.

### From recent design conversation
```
/hs:design 결제 시스템 아키텍처
... (design 진행) ...
/hs:workflow 방금 설계로 PLAN 짜자
```
→ Uses recent `/hs:design` context as the source. Authors PLAN.

### SPEC only (design 생략)
```
/hs:workflow Inventory_SPEC.md대로 작은 기능이라 design 건너뛰고 PLAN
```
→ Reads SPEC. Confirms design-skipped intent. Authors lightweight
   PLAN appropriate to the small scope.

### Freeform (no SPEC, no DESIGN)
```
/hs:workflow 로그인 화면 새로 만드는데 큰 흐름만 짜줘
```
→ No predecessor docs. coarse granularity inferred. Authors a brief
   PLAN from the user's prompt alone.

### Multi-Phase decomposition
```
/hs:workflow 라이브 서비스 운영 도구 PLAN 꼼꼼히 짜줘
```
→ fine granularity. Multiple X groups (data model / core / UI / ops),
   each with several Phases.

## Next Step
After the PLAN is presented, the user typically proceeds:

1. **Save** — `/hs:document`로 `*_PLAN.md`로 저장
   (위치: `Docs/DEVELOPMENT/Dev/{system}/{SYSTEM}_PLAN.md`).
2. **Load for tracking** — `/hs:plan-load <path>`로 등록 후
   `/hs:plan-start Phase 1-1`로 실행 추적 개시.
3. **Skip-ahead** — 작은 작업이면 저장/추적 없이 바로 `/hs:implement` 가능.

This skill itself takes no further action automatically.
