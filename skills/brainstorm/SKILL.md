---
name: brainstorm
description: "다용도 브레인스토밍 (브레인스토밍, 아이디어 정리, 요구 탐색, 의사결정, 옵션 비교, requirements discovery, ideation) - 결과는 대화로만 출력, 파일 저장 안 함."
version: 0.1.0
---

# /hs:brainstorm - General-purpose Socratic Brainstorming

## Operating principles
- The user's global rules in `~/.claude/CLAUDE.md` and `~/.claude/rules/*.md`
  are the authoritative persona. Follow them strictly.
- This skill provides procedural guidance only — no identity injection,
  no priority overrides.
- If guidance here conflicts with user rules, user rules win.
- Respond to the user in Korean.

## Activation guard
- Explicit invocation (`/hs:brainstorm`) → always proceed.
- Auto-trigger:
  - Strong match (clear keywords AND clear target) → proceed.
  - Weak / ambiguous match → SKIP this skill. Respond as a normal
    assistant without invoking skill behavior.
- Opt-out keywords in the user prompt → SKIP:
  "스킬 쓰지 말고", "그냥 답해줘", "직접 답변", "스킬 빼고".

## Activation announcement
The FIRST line of every response from this skill MUST be a single-line
header in this exact format:

🔍 [hs:brainstorm] <short summary of inferred topic type / mode / depth>

Example:
- 🔍 [hs:brainstorm] gamedesign topic, socratic mode, normal depth

체이닝된 호출 시 (Phase 2 자동호출 활성화 후):
- Diagnostic 체이닝: 본 헤더 다음 줄에 "↳ chained from /hs:이전스킬" 추가.
- Pipeline-Stage 체이닝: 본 헤더 다음 줄에 "↳ chained from /hs:이전스킬 (pipeline)" 추가.
- 명시 호출: 추가 표기 없음.

Leave a blank line after the header, then proceed with the skill's
normal output.

## Triggers
- Ambiguous topics that need structured exploration.
- Requirements discovery for software, game design, content, or other
  domains.
- Decision support — option exploration, trade-off surfacing.
- General idea generation across any domain.
- Phrases like "brainstorm X", "이거 어떻게 할까", "옵션 펼쳐줘",
  "요구사항 정리해줘", "아이디어 좀", "여러 안 비교".

## Usage
```
/hs:brainstorm <topic in natural language>
```

자연어로 토픽과 원하는 진행 방식을 자유롭게 표현하세요. 토픽 타입,
탐색 깊이, 진행 모드는 입력에서 자동 추론됩니다. 명시 표현이 있으면
그쪽을 우선합니다.

## Inferring intent from natural language

The user expresses intent in prose. Infer these dimensions from the
input rather than requiring flags.

### Topic type
- "코드", "API", "기능", "시스템 구현", "프로그램" → `software`
- "게임", "전투", "스킬", "레벨", "밸런스", "캐릭터", "컨텐츠",
  "퀘스트", "스토리(게임)" → `gamedesign`
- "A vs B", "어느 쪽", "선택", "고민 중", "결정" → `decision`
- "글", "문서", "기획서", "카피", "스토리(글쓰기)" → `content`
- "어디서부터", "조사", "리서치", "어떻게 알아볼까" → `research`
- otherwise → `generic`

### Depth
- "빨리", "간단히", "한 줄로", "요약만", "짧게" → `quick`
- "깊게", "꼼꼼히", "전부", "끝까지" → `deep`
- No hint → `normal`

### Mode
- "질문해가며", "하나씩 짚어줘", "물어봐줘" → `socratic`
- "옵션 다 펼쳐", "선택지", "여러 안", "비교해줘" → `expand`
- No hint → `socratic` (default)

If genuinely ambiguous after inference, ask ONE short clarifying
question before proceeding. Do not ask if a reasonable default fits.

## Behavioral Flow

### Step 0 — Triage
- If the input is a simple question with one natural answer, do NOT
  enter full brainstorm. Give one recommendation with brief reasoning,
  then offer in a single line to expand if the user wants.
- Enter full brainstorm only when:
  - the user explicitly asks for options / comparison / exploration,
  - the topic is genuinely open-ended, OR
  - the user explicitly invoked `/hs:brainstorm` for a non-trivial topic.

### Step 1 — Explore (Socratic)
Surface hidden assumptions and constraints through questions tailored
to the inferred topic type. Ask **2–4 high-leverage questions per round**
and wait for user answers before proceeding. Do not assume.

Question themes by topic type:

- **software** — target users, scale, must-have vs nice-to-have,
  integration constraints, success criteria, deployment context.
- **gamedesign** — genre, target player, core fun loop, progression,
  failure / retry states, comparable references, platform.
- **decision** — decision criteria, weights, deadline, reversibility,
  what's been ruled out and why.
- **content** — audience, tone, length, key message, format, references.
- **research** — known unknowns, available sources, time budget,
  decision the research is feeding into.
- **generic** — goal, constraints, success criteria, what's been tried.

In `expand` mode, skip questioning and present a structured option
landscape immediately, then invite refinement.

### Step 2 — Synthesize
Once enough information is gathered:
- Group findings under topic-appropriate headings.
- Highlight trade-offs the user implied but did not state.
- Mark open questions explicitly so they are not lost.
- For `decision` type, lay out a comparison matrix against the
  user's stated criteria.

### Step 3 — Handoff
Conclude with:
- A short summary of where things stand.
- 2–3 suggested next actions (e.g., write a SPEC, prototype, decide,
  research X further).
- The user chooses what comes next. Do NOT auto-trigger other skills.

## Output policy

**모든 출력 끝에 표준 `## Skill Output Metadata` appendix 의무** — Collected Facts (3-5 fact) + Next Skill Hints. 다음 스킬이 fact 재수집 회피 + 체이닝 시그널 명시 (HSPOLICY_DESIGN 의 "Fact 공유 — Output appendix 강제 규약" 절 참조). **직전 스킬의 appendix 가 있으면 본 스킬 입력으로 우선 사용** — 같은 fact 재수집 회피.
- ALWAYS conduct the brainstorm in the conversation only.
- NEVER create, write, or save documents — even if the result resembles
  a requirements doc, GDD, or design brief.
- Do NOT propose "save to file?" or auto-generate documents.
- If the user explicitly asks to save afterwards, treat it as a
  separate request and follow the user's global file-creation rules.

## Tool coordination
- **Read** — only when the user references a specific file/doc that
  needs reading to anchor the brainstorm.
- **Glob / Grep** — only when the user asks to brainstorm against
  existing code/docs (and serena is unavailable).
- **WebSearch / WebFetch** — only when the user explicitly invites
  external research, OR when topic type is `research`.
- Avoid eager tool use. Ask first when in doubt.

## MCP integration (lazy, not eager)

Brainstorming is conversational by nature. MCPs are activated only when
the topic clearly anchors on real artifacts (code, data, libraries,
external sources). Default is no MCP usage — just dialogue.

### sequential-thinking — for deep + complex topics
Use `sequentialthinking` when:
- depth is `deep` AND the topic has multiple interlocking concerns
  (multi-system feature design, complex trade-off decisions).
Skip for normal/quick depth — overhead exceeds value.

### serena — when the topic references existing code
Use serena's semantic tools to ground the brainstorm in current reality:
- The user references a specific module / class / system in the project.
- Phrases like "이 모듈에 추가", "현재 구조 위에서", "기존 X와 어떻게".
- Preferred entry points:
  - `get_symbols_overview` — quick structure of a file/module.
  - `find_symbol` — locate an existing definition by name.
  - `find_referencing_symbols` — impact map for "이걸 바꾸면 뭐가 영향?".
Do NOT use serena for greenfield ideation with no code anchor.

### context7 — for library/framework-specific decisions
Trigger when the brainstorm hinges on a specific library or framework's
current capabilities or recommended patterns.
- `resolve-library-id` → `query-docs` with a specific topic.
- Use sparingly. Most brainstorms don't need framework docs.

### excel-mcp — for numeric design with existing tables
For `gamedesign` or `decision` topics that reference existing
spreadsheet data (balance tables, economy models, comparison sheets).
- Read-only flow: `file` (open) → `range` (read) → `file` (close, save:false).
- Skip for greenfield numeric brainstorm — Read alone is enough.
- Per the user's excel-mcp note: target file must be CLOSED in Excel
  desktop. If COM open fails, surface and stop.

### WebSearch / WebFetch — for research or competitive grounding
Activate when:
- topic type is `research`, OR
- the user explicitly invites external lookup ("사례 찾아",
  "다른 게임은 어떻게", "최근 트렌드", "레퍼런스").
Do NOT search proactively for software/gamedesign brainstorms unless
the user signals interest in external grounding.

### gemini-video — only when user provides a video
Trigger only if input includes a video file (gameplay reference,
UI walkthrough, bug capture).

### MCP fallback policy
- All MCPs are optional. If a recommended MCP is unavailable, proceed
  with dialogue and built-in tools.
- Silent fallback — do NOT mention missing MCPs to the user.
- Do NOT proactively invoke MCPs to "show capability". Activate only
  when the conditions above are met.
- Do NOT mention MCP names in user-facing output — only the synthesis.

## Subagent integration (software type, deep depth)

### requirements-analyst — software 타입 + deep + PRD 수준 필요 시
조건 모두 충족 시 Agent tool로 위임 검토:
- topic type = `software`
- depth = `deep`
- 사용자가 명시적으로 PRD / 명세서 수준 결과물 요청

위임 시 brief에 포함:
- 사용자 원래 입력 (verbatim)
- 이미 모은 컨텍스트 (앞 라운드 답변)
- 사용자 글로벌 룰 (특히 "comprehensive PRD" push 회피)
- 기대 출력 형식 (requirements-analyst 표준 출력)

quick/normal은 메인에서 Socratic 직접. subagent 오버헤드 회피.

## Boundaries

**Will:**
- Ask Socratic questions to surface hidden assumptions and constraints.
- Adapt question style to the inferred topic type.
- Synthesize findings into a clear, structured summary.
- Triage simple questions away from full brainstorm flow.

**Will Not:**
- Generate code, designs, schemas, or implementation plans
  (those belong to other skills like `/hs:implement`, `/hs:design`).
- Save, write, or generate document files.
- Inject any persona or override user rules.
- Force multi-domain exploration on simple, single-answer questions.
- Mutating 스킬 자동 호출 금지 (implement / refactor / cleanup / document / plan-* / cl-* 등).
- Diagnostic 끼리는 사용자 체이닝 시그널 있고 opt-out 없을 때만 자동 호출 허용 (활성). 안전 쌍: analyze→explain, research→brainstorm, troubleshoot→explain.
- 자동 호출 시 activation header 에 "↳ chained from /hs:이전스킬" 표기 의무.
- Continue questioning past the point where the user has clearly
  signaled they want synthesis.

## Examples

### Software requirements discovery
```
/hs:brainstorm 주식 분석 프로그램을 구현하기 위한 요구 명세
```
→ Inferred: software, normal depth, socratic. Asks about target users,
data sources, analysis dimensions, performance constraints.

### Game design exploration
```
/hs:brainstorm 전투 시스템 기획 깊게 파보자
```
→ Inferred: gamedesign, deep, socratic. Asks about genre, target
player, fun loop, progression, references.

### Decision support
```
/hs:brainstorm Unity vs Godot 어떤 엔진 쓸까
```
→ Inferred: decision. Surfaces criteria, weights, constraints, then
lays out trade-offs in a comparison matrix.

### Quick option spread
```
/hs:brainstorm 캐릭터 이름 후보 옵션 다 펼쳐
```
→ Inferred: content, expand mode. Skips questioning, presents a
structured option landscape immediately.

### Single-answer triage
```
/hs:brainstorm DB 테이블에 인덱스 하나 추가하면 되는 거 아냐?
```
→ Triage: this is a single-answer question. Skip full brainstorm.
Give one direct recommendation + offer to expand if the user wants.

### Research direction
```
/hs:brainstorm 게임 라이브 서비스 운영 도구 어디서부터 조사할까
```
→ Inferred: research. Asks about decision being fed, time budget,
known sources, then suggests a search plan.

## Next Step
After brainstorming, the user may proceed to spec writing, design,
prototyping, decision execution, or further research. This skill
provides synthesis only; the user chooses what comes next.
