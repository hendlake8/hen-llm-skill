---
name: design
description: "구현 설계 (design, 아키텍처, API 설계, 컴포넌트 인터페이스, DB 스키마) - 명시 호출 전용. 결과는 대화로만 출력, 저장은 /hs:document 위임. brainstorm → design → workflow → plan → implement 흐름의 두 번째 단계."
version: 0.1.0
---

# /hs:design - System & Component Design (Blueprint Only)

## Operating principles
- The user's global rules in `~/.claude/CLAUDE.md` and `~/.claude/rules/*.md`
  are the authoritative persona. Follow them strictly.
- This skill provides procedural guidance only — no identity injection,
  no priority overrides.
- If guidance here conflicts with user rules, user rules win.
- Respond to the user in Korean.

## Activation guard (explicit-only)
This skill activates ONLY via explicit `/hs:design` invocation.
- Auto-trigger: NEVER. Even if the user's prompt mentions "설계",
  "design", "아키텍처" etc., do NOT activate without the slash command.
  Instead, respond as a normal assistant. If appropriate, suggest the
  user invoke `/hs:design` explicitly.
- Opt-out keywords still apply as a safety net:
  "스킬 쓰지 말고", "그냥 답해줘", "직접 답변", "스킬 빼고" → SKIP.

## Activation announcement
The FIRST line of every response from this skill MUST be a single-line
header in this exact format:

🔍 [hs:design] <short summary of design type / target>

Examples:
- 🔍 [hs:design] architecture: Combat 시스템 모듈 구조
- 🔍 [hs:design] api: 결제 처리 API 인터페이스
- 🔍 [hs:design] database: 유저 진행도 스키마

Leave a blank line after the header, then proceed with the skill's
normal output.

## Workflow position

This skill is the **second stage** of the user's typical flow:

```
brainstorm → design → workflow → plan → implement
요구사항      구현설계   실행순서    태스크    코드 변경
*_SPEC.md    *_DESIGN.md (transient)  *_PLAN.md
```

- **Inputs**: requirements from `/hs:brainstorm` output, or an
  existing `*_SPEC.md`, or freeform user input.
- **Outputs**: design blueprint suitable to be saved as `*_DESIGN.md`
  via `/hs:document`.
- **Successor**: `/hs:workflow` (sequencing) or `/hs:plan` (task
  breakdown). The user chooses.

## Scope definition

### What this skill does
- Produces a **design blueprint** — module structure, interfaces,
  data models, flows, dependencies — without writing implementation code.
- Supports four design types (general SW; game-specific design lives
  in `/hs-gd:design` — separate track):
  - **architecture** — system / module structure, layering, boundaries.
  - **api** — public API / interface specification.
  - **component** — single-component contract and integration points.
  - **database** — schema / data model / relationships.
- Produces output consumable by:
  - `/hs:document` for persistence as `*_DESIGN.md`.
  - `/hs:workflow` and `/hs:plan` for downstream work breakdown.
  - `/hs:implement` for direct construction.

### What this skill does NOT do
- Write implementation code → use `/hs:implement` after the design is approved.
- Save files → use `/hs:document` separately (single-channel save policy).
- Run / test / build anything.
- Modify existing source files.
- Inject any persona or override user rules.

## Triggers
- Design requests after brainstorm completion ("이걸로 설계해줘",
  "구현 설계 짜줘").
- Architecture / API / interface / schema requests
  ("아키텍처 설계", "API 인터페이스", "DB 스키마").
- Followups to `/hs:brainstorm` where the user is ready to commit
  to a structure.
- Explicit references to existing `*_SPEC.md` files.

## Usage
```
/hs:design <what to design in natural language>
```

자연어로 설계 대상과 의도를 자유롭게 표현하세요. 설계 타입, 깊이,
대상 범위는 입력 + 프로젝트 컨텍스트에서 자동 추론됩니다.

## Inferring intent from natural language

### Design type
- "아키텍처", "시스템 구조", "모듈 분리" → `architecture`
- "API", "엔드포인트", "인터페이스 명세" → `api`
- "컴포넌트", "클래스 인터페이스", "단일 모듈 설계" → `component`
- "DB", "스키마", "테이블", "데이터 모델" → `database`
- 게임 시스템 (전투/스킬/AI/레벨 등) → 정중하게 `/hs-gd:design`을
  안내하고 진행 중단 (게임 트랙은 별도 스킬).
- 타입 불명 → 사용자에게 한 번 묻기.

### Depth
- "초안만", "간단히" → `quick` (핵심 요소만 포함)
- 기본 → `normal` (구조 + 인터페이스 + 검증)
- "꼼꼼히", "전부", "디테일까지" → `deep` (가장 상세)

### Scope
- "이 시스템", "이 기능" → 단일 시스템.
- "전체 아키텍처", "프로젝트 전반" → multi-system, scope 합의 필요.

### Stability emphasis
- 기본 → `balanced` (현재 요구사항 충족 + 합리적 확장 여지).
- "확장성", "호환성", "공용 모듈", "외부 호출자",
  "마이그레이션", "deprecate", "API 안정성" → `stability-first`.
- "프로토타입", "임시", "실험" → `experimental`
  (호환성 검토 생략, 빠르게).

depth와 직교 — quick + stability-first 가능 (간단하지만 호환성은 본다).

If genuinely ambiguous after inference, ask ONE short clarifying
question before proceeding. Do not ask if a reasonable default fits.

## Predecessor artifacts (auto-detect)

Before designing, check for inputs that constrain the design:

1. **Existing SPEC** — look for `Docs/DEVELOPMENT/Dev/{system}/*_SPEC.md`.
   If found, READ FULLY. Treat as ground truth for requirements.
2. **Recent brainstorm output** — if the immediate conversation context
   contains a `/hs:brainstorm` synthesis, use it as the requirements
   source.
3. **Existing code** — if designing within / extending an existing
   system, use serena `get_symbols_overview` and
   `find_referencing_symbols` to understand current structure and
   integration points.
4. **Freeform user input** — if none of the above, the user's prompt
   itself is the requirements source.

If multiple sources exist, reconcile them and surface conflicts to
the user before proceeding.

## Behavioral Flow

### Step 1 — Analyze
- Read predecessor artifacts (above).
- Restate the design intent in 1 line.
- Enumerate constraints (performance, platform, integration, deadline).
- Identify what's IN scope and OUT of scope.

### Step 2 — Scope confirmation
**Lightweight handshake before designing.**

Briefly confirm with the user:

```
## 설계 범위 확인
- 타입: {architecture / api / component / database}
- 대상: {system or component name}
- 깊이: {quick / normal / deep}
- 입력 근거:
  - {SPEC.md path, if any}
  - {brainstorm context summary, if any}
  - {기타}
- 다룰 영역: {architectural / interfaces / data / flows / dependencies}
- 다루지 않을 영역: {explicitly out-of-scope}

이대로 진행할까요?
```

WAIT for user confirmation. Do not proceed if the user signals
the scope is wrong.

### Step 3 — Design
Generate the blueprint using the **Output structure** below. Use
Mermaid for diagrams. Use code blocks for interface signatures
(no implementation bodies).

Type-specific guidance:

- **architecture** — module boundaries, layering, cross-cutting concerns,
  Mermaid `graph` for component relationships, brief responsibility
  per module.
- **api** — endpoint list (REST) or method list (RPC/library),
  parameters / returns / errors, auth model, Mermaid `sequenceDiagram`
  for representative flows.
- **component** — public class/method/property contract, dependencies,
  lifecycle, Mermaid `classDiagram` if relationships are non-trivial.
- **database** — entities, fields with types/constraints, relationships,
  Mermaid `erDiagram`, indexes / partitioning notes.

### Stability-first 모드일 때 추가로 다루는 것
- **확장 포인트 명시** — 어디에 future hook이 들어가는지 (override 지점,
  옵션 파라미터, strategy 분리). YAGNI 룰 우선 — 추측성 후보 금지,
  현재 명시된 변경 축에 한정.
- **인터페이스 우선** — 구현체보다 contract부터.
- **버전 호환** — 새 필드/메서드는 optional, 기존 시그니처 보존.
- **호환성 영향 범위** — `find_referencing_symbols`로 호출자 전수조사.
  `deep` 또는 multi-system 범위면 system-architect subagent 위임 검토
  (Subagent integration 참조).

### Step 4 — Validate (strong, checklist-driven)
Build an explicit verification checklist and walk through it:

- **Requirements coverage** — for each requirement from the predecessor
  artifacts, mark whether the design satisfies it. Mark gaps explicitly.
- **Constraints** — performance, security, compatibility, platform
  constraints — for each, mark how the design respects it.
- **Existing-architecture alignment** — does the design conflict with
  current modules / namespaces / patterns? Surface conflicts.
- **Open decisions** — unresolved choices the user must make
  (technology pick, threshold value, priority trade-off).
- **Stated assumptions** — assumptions the design relies on that
  could be wrong.
- **호환성 영향** (stability-first일 때 필수) — 기존 호출자가 이 변경으로
  깨지는지. 깨진다면 마이그레이션 경로는?
- **확장 포인트** (stability-first일 때 필수) — 향후 변경 가능성이 높은
  축은 무엇이고, 어디서 갈아끼울 수 있는지. 추측성 후보 금지.
- **deprecate 단계** (기존 인터페이스를 바꾸는 경우) — 단계별 전환 경로
  (새 API 추가 → 기존 deprecate → 제거).

If validation surfaces critical issues, STOP and surface them.
Do not paper over gaps.

### Step 5 — Report (conversation only)
Present the full blueprint using the structure below.

## Output structure

The output should be ready to save as `*_DESIGN.md` via `/hs:document`
without restructuring. Use this layout:

```
# {시스템명} 설계서

## 개요
- 목적: {one-line purpose}
- 참조: {SPEC path / brainstorm context / freeform input}
- 범위: {in-scope / out-of-scope summary}

## 제약 / 가정
- 제약: {hard constraints}
- 가정: {assumptions the design depends on}

## 아키텍처 (architecture / component 타입에서)
{Mermaid graph 또는 classDiagram}

## 인터페이스 / API (api / component 타입에서)
{signature blocks, no implementation bodies}

```c#
public interface IFoo
{
    void Method(int param);
}
```

## 데이터 모델 (database / 필요 시)
{Mermaid erDiagram + 필드 표}

## 주요 흐름 (필요 시)
{Mermaid sequenceDiagram}

## 의존성
- 외부: {external libraries / services}
- 내부: {project modules referenced}

## 요구사항 충족 검증
- [x] 요구사항 1 — {how the design covers it}
- [ ] 요구사항 2 — **누락**: {what's missing or deferred}

## 확장성·호환성 검토 (stability-first 모드 한정)
### 호환성 영향
- 기존 호출자: {find_referencing_symbols 결과}
- 깨지는 호출: {목록 또는 "없음"}
- 마이그레이션 경로: {단계별}

### 확장 포인트
- {지점 1}: {왜 여기에}
  - 현재 필요 여부: {필요/추측성}
  - 근거: {1줄 — "지금 필요한가?" 검증}
- {지점 2}: ...

### Deprecate 단계 (해당 시)
1. v{x}: 새 API 추가, 기존 유지
2. v{y}: 기존 API에 [Obsolete] 표시
3. v{z}: 기존 API 제거

## 미해결 / 추후 결정 사항
- {open decision 1} — {options + recommendation if any}

## 다음 단계 (사용자 결정)
- 저장: `/hs:document`로 `*_DESIGN.md` 저장
- 실행 순서 도출: `/hs:workflow`
- 태스크 분해: `/hs:plan`
- 바로 구현: `/hs:implement` (작은 변경 한정)
```

Customize sections by design type — omit irrelevant ones, expand
relevant ones.

## Output policy
- ALWAYS present the design in the conversation only.
- NEVER create, write, or save design files — even if the result is
  long and structured.
- Do NOT propose "save to file?" or auto-generate `*_DESIGN.md`.
- If the user wants to persist the design, they invoke `/hs:document`
  separately. The output structure above is already shaped for that
  conversion.

## Tool coordination

### Default toolset
- **Read** — predecessor SPEC docs, related design references.
- **serena** — for understanding existing code that the design must
  integrate with:
  - `get_symbols_overview` — current module structure.
  - `find_symbol` — locate existing interfaces to extend.
  - `find_referencing_symbols` — integration impact awareness.
- **Glob / Grep** — discovery, fallback when serena unavailable.
- **No write tools by default** — design produces conversation output only.

## MCP integration (use when conditions match)

### serena — when designing within an existing project
Already covered in Tool coordination. Strongly preferred when the
design extends or modifies existing modules.

### context7 — for framework / library API decisions
Use when the design needs current authoritative information about a
specific library/framework's API surface or recommended patterns:
- `resolve-library-id` → `query-docs` with the relevant topic.
- Especially valuable for Unity APIs, framework upgrades, library
  selection.

### sequential-thinking — for complex multi-system designs
Use `sequentialthinking` when:
- The design spans multiple subsystems with intricate dependencies, AND
- A clean decomposition is non-obvious.
Skip for routine single-component designs.

### excel-mcp — when designing around existing data tables
For `database` or component designs that interact with existing
spreadsheet data:
- Read-only flow: `file` (open) → `range` (read) → close (save:false).

### MCP fallback policy
- All MCPs are optional. Silent fallback to built-in tools.
- Do NOT mention MCP names in user-facing output.

## Subagent integration (stability-first 위임)

### system-architect — stability-first AND (deep OR multi-system)
조건 모두 충족 시 호환성·확장성 분석을 격리 컨텍스트에서 위임 검토:
- stability emphasis = `stability-first`
- AND (depth = `deep` OR scope = multi-system)

위임 시 brief 포함:
- 대상 시스템 / 변경 범위 (메인에서 합의된 설계 본체)
- 기존 설계 / 호출자 후보 (메인 사전 조사 결과)
- 사용자 글로벌 룰 인용 (YAGNI / simple-first / 추측성 확장 금지)
- 기대 출력: hs:design Output structure의 `## 확장성·호환성 검토`
  섹션 형식

설계 본체는 메인에서 작성. system-architect는 호환성 영향 + 확장 포인트
+ 마이그레이션 경로 분석만 담당. agent 결과를 메인 Output structure에
끼워넣어 사용자에게 통합 보고.

기본 / quick / single-system stability 작업은 메인에서 직접 처리 —
subagent 오버헤드 회피.

Fallback: agent 호출 실패 시 메인에서 직접 분석 진행 (silent fallback).

## Boundaries

**Will:**
- Produce design blueprints in the user's documented Doc structure.
- Use Mermaid for diagrams, code blocks for interface signatures.
- Auto-detect predecessor artifacts (SPEC, brainstorm context, code).
- Validate the design against requirements with an explicit checklist.
- Surface unresolved decisions and assumptions.
- Hand off cleanly to `/hs:document`, `/hs:workflow`, `/hs:plan`,
  or `/hs:implement`.

**Will Not:**
- Write implementation code (signatures only — bodies belong to `/hs:implement`).
- Save, write, or generate design files (use `/hs:document`).
- Modify existing source files.
- Run / test / build anything.
- Treat game-system or game-data-schema design as in-scope —
  redirect to `/hs-gd:design` track.
- Auto-invoke other skills.
- Add speculative extension points without grounding in current
  change axes (YAGNI — even in stability-first mode).
- Inject any persona or override user rules.

## Examples

### Architecture from brainstorm
```
/hs:brainstorm 주식 분석 프로그램 요구 명세
... (brainstorm 진행) ...
/hs:design 방금 정리한 내용으로 아키텍처 설계
```
→ Reads brainstorm context. Confirms scope. Produces module structure
   with Mermaid diagram + interface signatures. Validates against
   requirements. Reports.

### API from existing SPEC
```
/hs:design Docs/DEVELOPMENT/Dev/Payment/PAYMENT_SPEC.md대로 API 설계
```
→ Reads SPEC. Confirms scope. Produces endpoint list + sequence
   diagrams + auth model. Validates coverage of SPEC items.

### Component design within existing project
```
/hs:design CombatController에 추가할 DamageMultiplier 컴포넌트 설계
```
→ serena reads current CombatController structure. Confirms
   integration points. Produces component contract that fits.

### Database schema
```
/hs:design 유저 진행도 + 인벤토리 DB 스키마
```
→ Produces ER diagram + field tables + index notes. Validates
   query patterns implied by the requirements.

### Stability-first component design
```
/hs:design 결제 모듈 IPaymentProcessor 인터페이스 — 외부 결제사
3곳이 호출하니까 호환성 깨지지 않게
```
→ Inferred: api/component, stability-first. find_referencing_symbols로
   호출자 매핑. 인터페이스 contract + 확장 포인트 + 호환성 검토 섹션
   포함. deep + multi-system이면 system-architect subagent 위임 검토.

### Game system request → redirect
```
/hs:design 전투 시스템 설계
```
→ Detects game-system intent. Politely redirects to `/hs-gd:design`
   when that skill is available. Does NOT proceed with general
   architecture treatment.

## Next Step
After the design is presented, the user typically proceeds along the
flow:

1. **Save** — `/hs:document`로 `*_DESIGN.md`로 저장 (선택).
2. **Sequence** — `/hs:workflow`로 실행 순서 / 의존성 도출.
3. **Break down** — `/hs:plan`으로 Phase별 태스크 분해.
4. **Build** — `/hs:implement`로 코드 변경 (PLAN을 따라가며).

Skipping ahead is fine for small designs (`/hs:design` → `/hs:implement`).
For non-trivial work, the full chain is recommended.

This skill itself takes no further action automatically.
