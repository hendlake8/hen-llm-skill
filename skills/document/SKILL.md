---
name: document
description: "문서 저장 / 작성 단일 채널 (document, 저장, 문서 작성, 남겨줘). 직전 스킬 결과 저장(Save mode) 또는 신규 문서 작성(Author mode). 사용자 글로벌 룰의 Doc 구조 자동 적용."
version: 0.1.0
---

# /hs:document - Save and Author Documentation

## Operating principles
- The user's global rules in `~/.claude/CLAUDE.md` and `~/.claude/rules/*.md`
  are the authoritative persona. Follow them strictly.
- This skill provides procedural guidance only — no identity injection,
  no priority overrides.
- If guidance here conflicts with user rules, user rules win.
- Respond to the user in Korean.

## Activation guard (explicit-only)
This skill activates ONLY via explicit `/hs:document` invocation.
- Auto-trigger: NEVER. 파일 생성/수정 = 사용자 룰상 명시 호출 필수.
- Opt-out keywords still apply as a safety net:
  "스킬 쓰지 말고", "그냥 답해줘", "직접 답변", "스킬 빼고" → SKIP.

## Activation announcement
The FIRST line of every response from this skill MUST be a single-line
header in this exact format:

🔍 [hs:document] <mode>, <type>, <target file>

Examples:
- 🔍 [hs:document] save, design, COMBAT_DESIGN.md
- 🔍 [hs:document] author, gamedesign, DAMAGE_FORMULA.md
- 🔍 [hs:document] save, plan, COMBAT_PLAN.md

체이닝된 호출 시 (Phase 2 자동호출 활성화 후):
- Diagnostic 체이닝: 본 헤더 다음 줄에 "↳ chained from /hs:이전스킬" 추가.
- Pipeline-Stage 체이닝: 본 헤더 다음 줄에 "↳ chained from /hs:이전스킬 (pipeline)" 추가.
- 명시 호출: 추가 표기 없음.

Leave a blank line after the header, then proceed with the skill's
normal output.

## Workflow position

`/hs:document`는 **모든 hs 스킬의 결과가 영속화되는 단일 채널**.
사용자 룰 "파일 생성/수정/삭제는 명시 요구 후" 정책의 핵심 구현.

```
analyze / brainstorm / design / workflow / research → "저장" → /hs:document
                                                         (Save mode)
임의 주제 신규 작성 요청 → /hs:document
                          (Author mode)
                              ↓
                      자동 타입 판정 + 위치 결정
                              ↓
                      Pre-flight 승인 후 파일 생성
                              ↓
                      Obsidian vault junction 자동 (필요 시)
```

→ 다른 hs 스킬은 **저장 자체를 모름**. 모든 저장은 이 스킬을 거침.

## Scope definition

### What this skill does
- **Save mode**: 직전 대화 출력 (다른 스킬 결과)을 받아서 사용자 Doc
  구조에 맞는 위치에 저장.
- **Author mode**: 사용자 요청에 따라 새 문서를 작성하고 저장.
- 사용자 글로벌 룰의 Doc 구조 / 파일명 컨벤션 / 내부 H1 컨벤션 적용.
- Obsidian vault junction 자동 등록 (`Docs/` 최초 생성 시).

### What this skill does NOT do
- 코드 inline 주석 작성 → `/hs:implement`의 책임.
- 자동 트리거 (사용자 명시 호출 필수).

## Two modes

### Save mode
- 입력: **직전 대화 컨텍스트** (다른 hs 스킬의 출력 등).
- 추가 입력: 사용자가 명시한 텍스트도 가능.
- 작업: 컨텐츠 → 타입 판정 → 위치 결정 → 저장.

### Author mode
- 입력: 사용자 요청 (주제 + 의도).
- Predecessor 자동 탐지: 기존 `Docs/DEVELOPMENT/Dev/{관련 시스템}/` 탐색.
- 작업: 정보 수집 (MCP 활용 가능) → 문서 작성 → 저장.

### Mode 자동 감지

| 입력 패턴 | 모드 |
|---------|------|
| "저장해줘", "남겨줘", "이거 저장" + 직전 대화에 풍부한 컨텐츠 | **Save** |
| "작성해줘", "문서 만들어줘", "{주제} 문서" | **Author** |
| 사용자가 명시: "신규 작성" / "방금 거 저장" | 명시대로 |
| 둘 다 애매 | 사용자에게 1회 확인 |

## Type detection (6종)

저장 위치 / 파일명 결정의 핵심 분류:

| Type | 컨텐츠 단서 | 저장 위치 | 파일명 |
|------|----------|---------|------|
| **analysis** | "Critical/High/Medium/Low", 분석 결과, 버그 리포트 | `Docs/DEVELOPMENT/Analyze/{시스템}/` | `{TOPIC}.md` |
| **spec** | 요구 명세, "Functional Requirements", brainstorm 결과 | `Docs/DEVELOPMENT/Dev/{시스템}/` | `{SYSTEM}_SPEC.md` |
| **design** | "## 인터페이스", Mermaid 다이어그램, 구현 설계 | `Docs/DEVELOPMENT/Dev/{시스템}/` | `{SYSTEM}_DESIGN.md` |
| **plan** | "## 구현 순서", "### Phase X-Y" | `Docs/DEVELOPMENT/Dev/{시스템}/` | `{SYSTEM}_PLAN.md` |
| **gamedesign** | 전투/스킬/레벨/밸런스/캐릭터/AI/퀘스트 | `Docs/DEVELOPMENT/GameDesign/{시스템}/` | `{TOPIC}.md` |
| **general** | 그 외 | `Docs/{주제}/` | `{TOPIC}.md` |

**자동 판정 규칙**:
1. 컨텐츠 패턴이 명확하면 그 type
2. 명시적 사용자 override (예: "DESIGN으로 저장", "GameDesign 폴더에") → 강제
3. 모호하면 사용자에게 묻기

**파일명 컨벤션** (사용자 룰):
- 영어 대문자 + `_` (예: `DAMAGE_FORMULA.md`, `COMBAT_SPEC.md`)
- spec/design/plan은 `{SYSTEM}_SPEC.md` 형식 강제

**시스템명 추출**:
- 직전 컨텐츠에서 명시된 시스템 (예: "Combat 시스템 분석" → Combat)
- 사용자가 명시
- 모호하면 사용자에게 묻기

**내부 H1**:
- 한국어 제목 (예: `# 데미지 공식 설계`)
- 파일명은 영어, 내부 제목은 한국어 — 글로벌 룰 그대로

## Triggers
- "저장해줘", "남겨줘", "문서로 정리".
- "{주제} 문서 작성해줘", "{시스템} 문서 만들어줘".
- 명시 `/hs:document` 호출.

## Usage
```
/hs:document [content or topic in natural language]
```

자연어로 의도를 표현하세요. 모드(save/author), 타입(6종), 시스템명,
저장 위치는 입력 + 컨텍스트에서 자동 추론됩니다. 명시 표현이 있으면
그쪽을 우선합니다.

## Predecessor artifacts (Author mode)

문서 작성 전, 관련 기존 문서 자동 탐색:

1. **기존 Doc 폴더 탐색** — `Docs/DEVELOPMENT/Dev/{system}/` 또는
   `Docs/DEVELOPMENT/GameDesign/{system}/` 등 관련 폴더가 있나?
2. **기존 SPEC/DESIGN/PLAN 활용** — 있으면 ground truth로 참조.
3. **관련 코드 anchor** — `이 모듈 문서화` 같은 표현이면 serena로 구조 파악.
4. **외부 라이브러리 의존** — context7 활용 가능 (조건부).

기존 문서가 있는데 같은 이름으로 새로 작성하려 하면 → 사용자 확인:
- "기존 문서 있음. 덮어쓸까요? 아니면 다른 이름?"

## Behavioral Flow

### Step 1 — Detect mode and type
- 모드 자동 판정 (Save / Author / 묻기).
- 타입 자동 판정 (6종 / 묻기).
- 시스템명 추출.
- Author mode이면 predecessor 탐색 (위 섹션).

### Step 2 — Author mode: gather and write (Save mode이면 skip)
정보 수집:
- 기존 Doc 읽기 (Read).
- 관련 코드 분석 (serena, MCP 섹션 참고).
- 라이브러리 정보 (context7, 조건부).
- 데이터 (excel-mcp, 조건부).

문서 작성:
- 사용자 글로벌 룰 따름:
  - 한국어 H1
  - 한국어 본문 (기술 용어는 한글/영어 혼용)
  - 사용자 룰의 Doc 구조 섹션 패턴
- 타입에 맞는 표준 섹션 (spec / design / plan 등):
  - **spec**: 개요 / 기능 요구사항 / 비기능 요구사항 / 결정사항
  - **design**: 개요 / 제약 / 아키텍처 / 인터페이스 / 데이터 모델 / 흐름 / 의존성 / 검증 / 미해결
  - **plan**: 개요 / 제약 / 리스크 / 구현 순서 (Phase X-Y) / 미해결
  - **analysis**: 요약 / 발견 (심각도별) / 권장 / 다음 단계
  - **gamedesign / general**: 자유 형식 (사용자 의도 따름)

### Step 3 — Save mode: extract from prior context (Author mode이면 skip)
- 직전 대화에서 컨텐츠 추출.
- 사용자가 별도 텍스트 제공했으면 그것 우선.

### Step 4 — Pre-flight approval

**MANDATORY before any file write.**

검사 항목:
1. **Auto-run mode 확인** (다른 hs 스킬과 일관):
   ```bash
   python {PLUGIN_ROOT}/scripts/plan_state.py auto-run-status
   ```
   `active: true && stale: false` → Step 4의 사용자 승인 skip
   (plan-run 일괄 승인된 상태로 간주). 단, 위치/파일명만은 명확히
   보고하고 진행.
   - **다만 document는 plan-run에서 거의 호출되지 않음**
     (plan-run은 코드만 다룸). 안전 가드로만 작동.

2. 정상 흐름 (auto-run 비활성):

```
## 저장 계획
- 모드: {save / author}
- 타입: {analysis / spec / design / plan / gamedesign / general}
- 시스템: {시스템명 or 주제명}
- 저장 경로: {full path}
- 파일명: {filename}
- 신규 폴더 생성: {필요한 경우 어떤 폴더}
- 기존 파일: {existing? overwrite? new name?}
- Obsidian vault junction: {필요한 경우 자동 등록 예정}

진행할까요?
```

WAIT for user approval. 사용자가 위치/이름 변경 요청하면 반영 후 재확인.

### Step 5 — Vault auto-registration (필요 시)

`Docs/` 폴더가 프로젝트에 **최초로 생성되는 경우**, 사용자 글로벌
룰에 따라 Obsidian vault junction 자동 등록:

```bash
powershell -NoProfile -ExecutionPolicy Bypass \
  -File ~/.claude/register_vault.ps1 \
  -VaultPath "D:\ObsidianVault" \
  -ProjectRoot "{프로젝트 루트}"
```

- `Docs/`가 이미 존재하면 → 호출 안 함 (스크립트가 중복 검증함).
- 비-Windows 환경 → 경고 메시지 + skip.
- 실패해도 문서 저장 자체는 진행 (vault 등록은 부가 기능).

### Step 6 — Write file

- 파일 위치 / 이름 확정.
- 신규 폴더는 생성.
- Write 도구로 저장.
- UTF-8 인코딩, 한국어 H1 + 본문 그대로.

### Step 7 — Report

```
✅ 문서 저장 완료

- 경로: {full path}
- 모드: {save / author}
- 타입: {type}
- 크기: {N}줄

{if vault_registered}
📓 Obsidian vault 등록됨: {vault path}
{end}

💡 다음 단계 (사용자 결정):
{type별 적절한 안내}
- spec → "/hs:design 진행 시 이 SPEC 자동 참조됨"
- design → "/hs:workflow 진행 시 이 DESIGN 자동 참조됨"
- plan → "/hs:plan-load {path}로 등록 + 추적 가능"
- analysis → 후속 작업 / 추가 분석
- gamedesign / general → 별도 안내 없음
```

## Output policy

**모든 출력 끝에 표준 `## Skill Output Metadata` appendix 의무** — Collected Facts (3-5 fact) + Next Skill Hints. 다음 스킬이 fact 재수집 회피 + 체이닝 시그널 명시 (HSPOLICY_DESIGN 의 "Fact 공유 — Output appendix 강제 규약" 절 참조). **직전 스킬의 appendix 가 있으면 본 스킬 입력으로 우선 사용** — 같은 fact 재수집 회피.
- 새 파일 생성 / 기존 파일 수정 모두 가능 (스킬의 본질적 책임).
- 단, **Step 4 승인 후에만**.
- 보고서 별도 저장 안 함 (대화 내 요약만).

## Tool coordination

### Default toolset
- **Read** — 기존 문서 / 관련 파일 참조.
- **Glob / Grep** — 기존 Doc 폴더 / 관련 파일 탐색.
- **Write** — 신규 문서 생성.
- **Edit / MultiEdit** — 기존 문서 수정 (드뭄, 보통은 신규 생성).
- **Bash** — vault 등록 스크립트 호출 + auto-run 상태 확인.

## MCP integration (lazy, Author mode 위주)

Save mode는 보통 MCP 안 씀. Author mode에서 컨텐츠 수집 시 활용.

### serena — 코드 문서화 시 strongly preferred
"이 모듈/클래스/시스템 문서화" 류 요청에서:
- `get_symbols_overview` — 모듈 구조 정확 파악.
- `find_symbol` — 특정 심볼 위치/시그니처.
- `find_referencing_symbols` — 사용처 / 호출 관계 (의존성 문서화에
  중요).
- `find_implementations` — 인터페이스 구현체.
→ 메모리 추론 대신 fact 기반 문서. 정확도 압도적으로 높음.

### context7 — 라이브러리 / 프레임워크 의존 시
"Unity 6", "React 19", 특정 라이브러리 가이드 등:
- `resolve-library-id` → `query-docs`.
→ 학습 데이터 stale 회피, 작성 시점 정확도.

### sequential-thinking — 복잡 다층 문서 작성 시
긴 기획서 / 다층 아키텍처 문서 / 복잡 가이드 — 섹션 구조가
비명확할 때만. 짧은 문서엔 오버헤드.

### excel-mcp — 데이터 기반 문서 시
기존 `.xlsx` 밸런스 시트 / 수치 테이블 인용 시:
- 읽기 전용 흐름: file open → range read → close (save:false).

### gemini-video — 비디오 자료 입력 시
드뭄. 사용자가 비디오 명시 제공할 때만.

### MCP fallback policy
- 모두 optional. 없으면 built-in으로 silent fallback.
- 사용자 출력에 MCP 이름 노출하지 않음.

## Boundaries

**Will:**
- 직전 대화 출력 (Save mode) 또는 신규 작성 (Author mode) 모두 처리.
- 사용자 글로벌 룰의 Doc 구조 / 파일명 컨벤션 / 내부 H1 룰 준수.
- 6종 type 자동 판정 + 명시 override.
- Step 4 사전 승인 + 사용자 결정 반영.
- Obsidian vault junction 자동 등록 (글로벌 룰 따름).

**Will Not:**
- Step 4 승인 없이 파일 생성하지 않음 (auto-run 모드 예외 단,
  document는 plan-run에서 거의 안 불림).
- 코드 파일에 inline 주석 작성 안 함 (그건 implement의 책임).
- 기존 파일 silent overwrite 안 함 (덮어쓸 때 사용자 확인).
- 어떤 스킬도 자동으로 호출하지 않음. 사용자 명시 호출만 진입 가능 (Mutating 스킬 — Step 4 Pre-flight approval 게이트 필수). plan-load 등 후속은 안내만.
- 사용자 룰의 Doc 구조 외 임의 위치에 저장 안 함
  (사용자가 명시 path 지정 시 그것 우선).

## Examples

### Save mode — 분석 결과
```
/hs:analyze src/Combat 코드 품질
... (분석 결과 출력) ...
/hs:document 이거 저장해줘
```
→ 모드: save, 타입: analysis (자동 판정).
→ 위치: `Docs/DEVELOPMENT/Analyze/Combat/{TOPIC}.md`.
→ Pre-flight → 저장.

### Save mode — design 결과
```
/hs:design 결제 시스템 아키텍처
... (DESIGN 출력) ...
/hs:document 저장
```
→ 모드: save, 타입: design.
→ 위치: `Docs/DEVELOPMENT/Dev/Payment/PAYMENT_DESIGN.md`.

### Save mode — workflow 결과 (PLAN.md)
```
/hs:workflow Combat PLAN
... (PLAN markdown) ...
/hs:document 이걸로 PLAN 저장
```
→ 모드: save, 타입: plan.
→ 위치: `Docs/DEVELOPMENT/Dev/Combat/COMBAT_PLAN.md`.
→ "다음: /hs:plan-load {path}" 안내.

### Author mode — 신규 분석 문서
```
/hs:document 데미지 공식 설계 문서 작성해줘
```
→ 모드: author, 타입: gamedesign (전투 특성).
→ 위치: `Docs/DEVELOPMENT/GameDesign/Combat/DAMAGE_FORMULA.md`.
→ 기존 `Docs/DEVELOPMENT/GameDesign/Combat/` 탐색 → 보완 또는 신규.

### Author mode — 코드 모듈 문서 (serena 활용)
```
/hs:document CombatController 클래스 API 문서 작성
```
→ 모드: author, 타입: gamedesign 또는 general.
→ serena로 클래스 구조 / 메서드 / 사용처 fact 수집.
→ 기반으로 정확한 API 문서 작성.

### Author mode — 라이브러리 가이드 (context7 활용)
```
/hs:document Unity 6 Addressables V2 마이그레이션 가이드
```
→ 모드: author, 타입: general.
→ context7로 Unity 6 공식 정보 수집.
→ 위치: `Docs/Migration/UNITY6_ADDRESSABLES_V2.md`.

### 모호한 경우
```
/hs:document Combat 관련 정리해줘
```
→ "save (직전 출력)인지 author (신규)인지 묻기" → 사용자 결정.

## Next Step
저장 후 사용자 결정. 보통:
- spec 저장 → `/hs:design`으로 진행 (자동 참조됨)
- design 저장 → `/hs:workflow`로 PLAN 작성
- plan 저장 → `/hs:plan-load <path>`로 등록 + 추적
- analysis 저장 → 후속 작업 / 정리
- gamedesign / general → 별도 작업 없음 (필요 시 사용자 결정)

This skill takes no further action automatically.
