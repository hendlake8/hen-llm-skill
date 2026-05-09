---
name: research
description: "웹/문서 리서치 (research, 조사, 사례, 레퍼런스, 트렌드, 비교 조사) - 결과는 대화로만 출력, 파일 저장은 /hs:document로 위임. 깊은 리서치는 deep-research-agent 서브에이전트로 자동 위임."
version: 0.1.0
---

# /hs:research - Adaptive Web & Document Research

## Operating principles
- The user's global rules in `~/.claude/CLAUDE.md` and `~/.claude/rules/*.md`
  are the authoritative persona. Follow them strictly.
- This skill provides procedural guidance only — no identity injection,
  no priority overrides.
- If guidance here conflicts with user rules, user rules win.
- Respond to the user in Korean.

## Activation guard (explicit-only)
This skill activates ONLY via explicit `/hs:research` invocation.
- Auto-trigger: NEVER. Even if the user's prompt seems related (mentions
  research, 조사, 리서치, etc.), do NOT activate without the slash
  command. Instead, respond as a normal assistant. If appropriate,
  suggest the user invoke `/hs:research` explicitly to use this skill.
- Opt-out keywords still apply as a safety net:
  "스킬 쓰지 말고", "그냥 답해줘", "직접 답변", "스킬 빼고" → SKIP.

## Activation announcement
The FIRST line of every response from this skill MUST be a single-line
header in this exact format:

🔍 [hs:research] <short summary of inferred depth / focus / delegation>

Examples:
- 🔍 [hs:research] normal depth, web-first
- 🔍 [hs:research] deep depth, delegating to deep-research-agent
- 🔍 [hs:research] quick depth, context7-first (library docs)

Leave a blank line after the header, then proceed with the skill's
normal output.

## Triggers
- Research questions beyond model knowledge cutoff or that need
  current information.
- Competitive / market / reference investigation
  ("다른 게임은 어떻게", "사례 찾아줘", "최근 트렌드").
- Technical research that needs cross-source verification.
- Library / framework capability surveys (often pairs with context7).
- Phrases like "조사해줘", "리서치", "찾아봐", "비교해서 알려줘".

## Usage
```
/hs:research <query in natural language>
```

자연어로 리서치 주제와 원하는 깊이를 자유롭게 표현하세요. 깊이,
초점, 외부 검색 강도는 입력에서 자동 추론됩니다. 명시 표현이 있으면
그쪽을 우선합니다.

## Inferring intent from natural language

### Depth (number of hops + scope)
- "빨리", "간단히", "한 줄로", "핵심만" → `quick` (1 hop, brief summary)
- No hint, single clear question → `normal` (2–3 hops, structured)
- "깊게", "꼼꼼히", "여러 측면" → `deep` (3–4 hops, multi-angle)
- "전부", "끝까지", "철저히", "exhaustive" → `exhaustive` (5+ hops)

### Focus
- "라이브러리/API/SDK 사용법" → context7-first
- "현재 트렌드/최근 변화" → web-first
- "이 프로젝트에 적용하려면" → serena anchor + web
- "수치/통계/데이터" → web + excel-mcp if existing tables exist

If genuinely ambiguous after inference, ask ONE short clarifying
question before proceeding. Do not ask if a reasonable default fits.

## Subagent escalation

**For `deep` and `exhaustive` depth → automatically delegate to the
`deep-research-agent` subagent.**

Why:
- Deep research generates many parallel queries and large fetched
  pages. Doing this in the main context floods the conversation.
- The subagent runs in isolation, returns a synthesized result.

How:
1. Briefly inform the user (one sentence) that deep research will be
   delegated.
2. Hand the agent a self-contained prompt:
   - Original query (verbatim).
   - Inferred depth and focus.
   - Required output format (citations as `[n]` + source list).
   - Cap on report length appropriate to depth.
3. Wait for the subagent's synthesized result.
4. Present the result to the user in Korean (the subagent may return
   English; translate or summarize as needed).
5. Do NOT re-run searches the subagent already did.

**For `quick` and `normal` depth → execute in the main context.**
Subagent overhead exceeds value at this scale.

## Behavioral Flow (main-context execution: quick / normal)

### Step 1 — Understand (5–10% effort)
- Restate the query in 1 sentence to confirm intent.
- Identify the unknown(s) and the decision the research feeds.
- Note hard constraints (time budget, language, source restrictions).

### Step 2 — Plan (10–15% effort)
- Decompose into 2–5 sub-questions answerable independently.
- Identify which sub-questions can run in parallel.
- Choose primary sources per sub-question (web search vs context7 vs
  internal code via serena).

### Step 3 — Execute (50–60% effort)
- **Parallel-first** — issue independent searches in a single message
  (multiple WebSearch calls in one tool-use block).
- **Multi-hop** — extract entities/concepts from initial results, then
  follow up with second-hop searches.
- **Smart fetching** — for promising results, WebFetch the full page;
  skip fetching when the snippet already answers.
- Track every claim with a source URL — no claim without a source.

### Step 4 — Validate (10–15% effort)
- Cross-check key claims against at least one independent source.
- Flag contradictions explicitly rather than picking a side silently.
- Note source recency (year, last-updated) when relevant.
- Mark low-confidence findings as such.

### Step 5 — Synthesize (10–15% effort)
- Group findings by sub-question.
- Surface trade-offs and contradictions.
- Mark open questions left unanswered.

### Step 6 — Report (conversation only)
Output structure (in Korean):

```
# 리서치 결과: {주제}

## 요약
- 핵심 발견 2-4줄

## 주요 발견
### {sub-question 1}
- 발견 내용 [1][2]
- ...

### {sub-question 2}
- ...

## 모순 / 미해결
- {issue} — 출처가 엇갈림 [3] vs [4]

## 출처
[1] {title} — {url} ({year/date if known})
[2] {title} — {url}
...

## 다음 단계
- 권장 후속 작업 (사용자 결정)
```

## Citation policy
- **Inline `[n]`** — every factual claim cites at least one source.
- **Source list at the end** — numbered, with title + URL +
  date/year if available.
- Do NOT cite from memory. If a claim has no fetched source,
  mark it as "확인 필요" instead.
- Do NOT fabricate URLs or titles. Use only what was actually
  retrieved.

## Output policy
- ALWAYS conduct the research output in the conversation only.
- NEVER create, write, or save research reports to files.
- This skill does NOT save anything. If the user wants to persist
  the result, they invoke `/hs:document` separately (single-channel
  save policy).
- Do NOT propose "save to file?" or auto-generate documents.

## Tool coordination

### Default toolset
- **WebSearch (built-in)** — primary search engine. Issue parallel
  searches in a single tool-use block whenever queries are independent.
- **WebFetch (built-in)** — fetch promising URLs for full content.
- **Read** — when the user references local files as research anchors.

## MCP integration (use when conditions match)

### sequential-thinking — for synthesis in deep/exhaustive (when not delegated)
Use `sequentialthinking` for the **Synthesize** step when the topic
has many interlocking findings. Do NOT use during Execute (search
parallelism is more valuable than sequential reasoning there).

### context7 — for library/framework research
Strongly preferred over web search when the question is about a
specific library/framework's current capabilities or recommended
patterns:
- `resolve-library-id` → `query-docs` with a specific topic.
- Faster, more authoritative than scraping docs from web.
- Combine with WebSearch for non-doc context (community sentiment,
  comparisons).

### serena — when the research anchors on existing code
Use serena's semantic tools when the research must ground in the
current project:
- "이 모듈에 적용하려면 뭐 봐야 해" → `get_symbols_overview` first.
- "현재 X와 비교했을 때" → `find_symbol`, `find_referencing_symbols`.
Skip when the research has no project anchor.

### excel-mcp — for numeric data research with existing tables
When the research involves comparing against existing spreadsheet
data (balance tables, market data):
- Read-only flow: `file` (open) → `range` (read) → close (save:false).
- Skip for greenfield numeric questions — built-in tools suffice.

### gemini-video — only when input includes a video
Trigger only if the user provides a video file as research material.

### MCP fallback policy
- All MCPs are optional. Silent fallback to built-in tools.
- Do NOT mention MCP names in user-facing output — only the findings.
- Do NOT proactively invoke MCPs to "show capability".

## Boundaries

**Will:**
- Conduct adaptive research (quick → exhaustive) with depth inferred
  from natural language.
- Issue parallel-first searches for efficiency.
- Follow multi-hop reasoning chains.
- Track every claim with a citation.
- Auto-delegate deep/exhaustive research to the subagent.

**Will Not:**
- Save, write, or generate research report files
  (use `/hs:document` separately).
- Make architectural / implementation decisions based on findings
  (use `/hs:design`, `/hs:implement` after the user decides).
- Cite from memory or fabricate sources.
- Access content the user hasn't authorized (paywalled, login-gated).
- Inject any persona or override user rules.

## Examples

### Quick technical lookup
```
/hs:research Unity 6 SRP 변경점 핵심만
```
→ Inferred: quick. Brief summary with 2–3 key sources.

### Standard competitive research
```
/hs:research 모바일 카드 게임 BM 트렌드 조사
```
→ Inferred: normal. Multi-source structured report with citations.

### Deep multi-angle (auto-delegated)
```
/hs:research 라이브 서비스 게임 운영 도구 깊게 비교 분석
```
→ Inferred: deep. Brief notice + delegated to deep-research-agent.
   Result presented in main conversation.

### Exhaustive (auto-delegated)
```
/hs:research RTS 장르 부활 가능성 전부 조사해서 정리
```
→ Inferred: exhaustive. Delegated to deep-research-agent with
   maximum hop depth.

### Library-specific (context7-first)
```
/hs:research React 19 새로 들어온 hooks 사용법
```
→ Inferred: normal, context7-first. Authoritative docs first,
   web for community context.

### Code-anchored
```
/hs:research 현재 프로젝트의 Addressables 설정을 V2로 마이그레이션 어떻게 하는지
```
→ Inferred: normal, serena+web. serena reads current setup,
   web/context7 for migration guides.

## Next Step
After research, the user may proceed to:
- Decision-making (use `/hs:brainstorm` if more discussion needed).
- Design (`/hs:design`) or implementation (`/hs:implement`).
- Persistence (`/hs:document`) if the result is worth saving.
This skill itself takes no further action.
