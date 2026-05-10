---
name: cl-stats
description: "CM 누적 사용량 집계 / 마크다운 리포트 (cl-stats, 통계, 사용량, 어디에 토큰 많이 썼지, 리포트). 토픽별/사용자별/전체 합계, Mermaid 그래프 포함."
version: 0.1.0
---

# /hs:cl-stats - CM Usage Statistics & Report

## Operating principles
- The user's global rules in `~/.claude/CLAUDE.md` and `~/.claude/rules/*.md`
  are the authoritative persona. Follow them strictly.
- This skill provides procedural guidance only — no identity injection,
  no priority overrides.
- If guidance here conflicts with user rules, user rules win.
- Respond to the user in Korean.

## Activation guard (explicit-only)
This skill activates ONLY via explicit `/hs:cl-stats` invocation.
- Auto-trigger: NEVER. 자연어로 "사용량 보여줘" 같은 표현이 나와도
  슬래시 명령 없이는 활성화하지 않음.
- Opt-out keywords: "스킬 쓰지 말고", "그냥 답해줘", "직접 답변",
  "스킬 빼고" → SKIP.

## Activation announcement
The FIRST line of every response from this skill MUST be a single-line
header in this exact format:

🔍 [hs:cl-stats] <scope 요약>

Examples:
- 🔍 [hs:cl-stats] 전체 사용자 / 토픽별 / 토큰 정렬
- 🔍 [hs:cl-stats] hendlake / 최근 7일 / 리포트 생성
- 🔍 [hs:cl-stats] 토픽 "API 리팩토링" 단일 / 리포트

Leave a blank line after the header, then proceed with the skill's
normal output.

## Triggers
- "CL 사용량", "통계", "사용량 집계", "어디에 토큰 많이 썼지".
- "리포트", "그래프로 보여줘", "사용량 문서로".
- 명시 `/hs:cl-stats` 호출.

## Usage
```
/hs:cl-stats [자연어 또는 플래그]
```

자연어로 자유롭게 표현하세요. SKILL 이 자연어를 cm_state.py 의 플래그로 변환합니다.

## Inferring intent from natural language

자연어 → 플래그 매핑표:

| 자연어 표현 | 추출 플래그 |
|-------------|-------------|
| "저장", "리포트", "문서로", "남겨", "보고서" | `--report` |
| "그래프", "차트", "시각화" | `--charts all` |
| "그래프 빼고", "표만" | `--charts none` |
| "사용자별", "유저별로" | `--by user` |
| "토픽별", "주제별" | `--by topic` (기본) |
| "사용자 → 토픽", "트리" | `--by user-topic` |
| "지난 한 달", "최근 30일" | `--since` (오늘 - 30일) |
| "지난 일주일", "최근 7일" | `--since` (오늘 - 7일) |
| "오늘", "이번 일자" | `--since` (오늘) |
| "Top 10", "상위 N개" | `--top N` |
| "활성만", "진행 중" | `--active-only` |
| "끝난 것만", "완료된" | `--ended-only` |
| "{이름}만", "내 것만" | `--user <이름>` 또는 detect-user |
| "토큰 많은 순", "비싼 작업" | `--sort tokens` (기본) |
| "오래 걸린 순" | `--sort duration` |
| "phase 많은 순" | `--sort phases` |
| "최근 시작 순" | `--sort started` |
| "토픽 이름 따옴표" | `--topic <패턴>` |

복수 적용 가능. 예: "최근 일주일 사용자별 그래프로 저장" →
`--since {7일전} --by user --charts all --report`

## Behavioral Flow

### Step 1 — Parse natural language → flags
사용자 입력에서 위 매핑표대로 플래그 추출. 모호하면 기본값:
- `--by topic` (기본 그룹)
- `--sort tokens` (기본 정렬)
- 필터 없음 (전체 데이터)
- `--report` 미지정 (대화 출력만)

### Step 2 — Invoke cm_state.py stats

```bash
python {PLUGIN_ROOT}/scripts/cm_state.py stats <flags>
```

`{PLUGIN_ROOT}` 1회 탐색 (다른 hs 스킬과 동일 패턴):
```bash
find ~/.claude/plugins -path "*hs/scripts/cm_state.py" 2>/dev/null | head -1
```

### Step 3 — Parse JSON

응답 키:
- `scope.filters` / `scope.by` / `scope.sort` / `scope.top` — 적용된 옵션
- `topics[]` — 토픽별 (필터/정렬/Top 적용 후)
- `users[]` — 사용자별 합산
- `grand_total` — 전체 합산
- `report` — 리포트 생성 시 `{written, path, size_bytes, charts_included, generated_at}`, 미생성 시 `null`

### Step 4 — Handle empty data

`grand_total.topic_count == 0` 이면:
```
📭 CM 토픽 데이터 없음

먼저 /hs:cl-start "주제" 로 세션을 시작하세요.
```

### Step 5 — Render Korean report

#### `--by topic` (기본)

```
📊 CL 사용량 ({user_count}명 / {topic_count}개 토픽 / {phase_count}개 Phase)

🌐 전체 합계
- 작업 시간: {format(duration_seconds)}
- 청구 토큰: {input+output+cacheCreation:,} (입력 {input:,} / 출력 {output:,} / 캐시 생성 {cacheCreation:,})
- 캐시 읽기: {cacheRead:,}
- 평균 적중률: {계산}%
- 모델: {models join ", "}

🏆 토픽 Top {min(10, len)} (정렬: {sort})
| 토픽 | 사용자 | 상태 | Phase | 시간 | 청구 토큰 | 적중률 |
| ... |

{legacy_phases > 0 이면}
⚠️ Legacy phase {N}개 발견 (토큰 데이터 없음, 0 합산).
{end}

💡 다음 단계
- 리포트 저장 → "저장해줘" 또는 다시 `--report` 옵션과 함께
- 사용자별 보기 → "사용자별로"
- 특정 사용자 → "{이름}만"
```

#### `--by user`

```
📊 CL 사용량 (사용자 {N}명)

| 사용자 | 토픽 | Phase | 시간 | 청구 토큰 | 캐시 읽기 |
| ... |

🌐 전체 합계: {grand_total 한 줄}
```

#### `--by user-topic`

각 사용자 헤더 + 그 사용자의 토픽 목록 + 사용자 소계.

### Step 6 — Surface report path (리포트 생성 시)

```
💾 리포트 저장됨
- 경로: {report.path}
- 크기: {report.size_bytes:,} bytes
- 포함 차트: {charts_included join ", "}
- 생성 시각: {generated_at} UTC
```

### Step 7 — Follow-up natural language

직전 cl-stats 결과 후 사용자가 평문으로:
- "저장해줘", "리포트로", "그래프 저장" → `--report` 모드로 재호출
- "사용자별로", "유저별로" → `--by user` 재호출
- "토픽별로" → `--by topic` 재호출
- "Top 5만" → `--top 5` 추가 후 재호출
- "{사용자}만" → `--user {사용자}` 추가 후 재호출

같은 대화 세션 안에서 자연스럽게 옵션 변경. 매번 슬래시 명령 다시
부를 필요 없음.

## Output policy

- 대화: 필수 (사람이 읽을 수 있게 한국어 표).
- 마크다운 파일: `--report` 옵션 시에만 (스크립트가 직접 저장).
- 다른 스킬 자동 호출 안 함.
- `/hs:document` 우회 — 데이터 export 는 스크립트 책임 (단일 채널 정책의 "분석 결과 저장" 과 다른 영역).

## Tool coordination
- **Bash** — `cm_state.py stats` 호출.
- 다른 도구는 사용 안 함 (pure data aggregation).

## Boundaries

**Will:**
- 누적 CM 데이터를 토픽별 / 사용자별 / 전체 합계로 집계.
- 자연어 → 플래그 변환.
- 마크다운 리포트 생성 (Mermaid 차트 포함).
- 한국어 표 / 카드 형태 결과 렌더링.
- 같은 대화 안에서 follow-up 자연어 옵션 변경 처리.

**Will Not:**
- 어떤 CM 데이터도 변경 (read-only 보장).
- 비용(USD) 추정 (모델 단가표 별도 트랙).
- 인터랙티브 / HTML 리포트 (마크다운만).
- 다른 스킬 자동 호출.

## Examples

### 기본 호출
```
/hs:cl-stats
```
→ 전체 / 토픽별 / 토큰 정렬 / 대화 출력.

### 사용자별 합계
```
/hs:cl-stats 사용자별
```
→ `--by user` 매핑.

### 그래프 리포트 저장
```
/hs:cl-stats 그래프로 저장해줘
```
→ `--charts all --report` 매핑. `.hs/{user}/CM/_reports/CL_USAGE_*.md` 생성.

### 최근 일주일 + Top 5
```
/hs:cl-stats 지난 일주일 Top 5
```
→ `--since {7일전} --top 5` 매핑.

### 특정 사용자 + 리포트
```
/hs:cl-stats hendlake 만 리포트로
```
→ `--user hendlake --report` 매핑.

### Follow-up
```
/hs:cl-stats
... (결과 표시) ...
사용자 > 저장해줘
```
→ 같은 대화 내에서 `--report` 모드로 재호출.

## Next Step
- 다른 view 보기 → 자연어로 "사용자별", "토픽별", "Top 5" 등
- 리포트 저장 → "저장해줘" 또는 직접 `--report`
- 정리 → 사용자가 `.hs/{user}/CM/_reports/` 직접 정리

This skill itself takes no further action automatically.
