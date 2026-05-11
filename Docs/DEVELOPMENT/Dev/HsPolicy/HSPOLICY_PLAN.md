# hs 스킬 정책 완화 + Fact 공유 구현 계획서

## 개요
- 목적: HSPOLICY_DESIGN 의 분류표 / 자동호출 정책 / Output appendix 규약을 모든 hs 스킬 SKILL.md 에 일괄 적용. Pipeline-Stage 예외 명시.
- 참조 설계 문서: `Docs/DEVELOPMENT/Dev/HsPolicy/HSPOLICY_DESIGN.md`
- 참조 명세 문서: 없음 (요구사항은 DESIGN 의 합의 5개로 통합됨)

## 제약 / 가정
- 제약:
  - 글로벌 룰 "파일 생성/수정/삭제는 명시 요구 후" 절대 보전.
  - SKILL.md 만 수정. 코드 / 인프라 신설 X.
  - 모든 mutating 스킬의 Pre-flight approval 동작 보전.
- 가정:
  - 대상 SKILL.md 약 25개 (`~/.claude/plugins/marketplaces/local/plugins/hs/skills/*/SKILL.md`).
  - LLM 이 분류표 보고 분류별 표준 문구 일관 적용 가능.

## 리스크
- **분류 오적용** — 새 스킬 추가 시 분류 누락 가능. 완화: Phase 1-1 의 분류 매핑 표를 DESIGN 에 박아 두고 새 스킬 추가 시 매핑 갱신 의무화.
- **체이닝 시그널 오탐** — 사용자가 의도하지 않은 자동호출 발생 가능. 완화: Phase 2 활성화는 안전 쌍 (analyze → explain, design → implement) 부터. 오탐 발견 시 Phase 4 로 정형화.
- **Output appendix 누락** — 일부 스킬이 appendix 추가 안 함. 완화: Phase 3-2 에서 모든 스킬 일괄 검증.
- **plan-run 충돌** — Pipeline-Stage 예외가 plan-run 의 일괄 승인 흐름과 겹침. 완화: DESIGN 에 별도 예외로 명시. 두 메커니즘은 독립 동작.

## 구현 순서

### Phase 1-1: 분류 매핑 표 작성 (사전 정리)
- hs 스킬 전체 25개 목록 작성 (Glob 으로 SKILL.md 열거)
- 각 스킬에 분류 라벨 부여 (Diagnostic / Pipeline-Stage / Mutating / plan-run 예외)
- 분류 매핑 표를 DESIGN 의 새 섹션 `## 스킬 분류 매핑` 으로 추가 (단일 진실 원천)
- 분류 매핑 표 사용자 검토 + 승인

### Phase 1-2: Diagnostic 스킬 SKILL.md 일괄 수정 (정책 명시 단계)
- analyze / explain / research / brainstorm / troubleshoot / review 의 `## Boundaries > Will Not` 변경
- 표준 문구 1: "Mutating 스킬 자동 호출 금지 ..."
- 표준 문구 2: "Diagnostic 끼리는 사용자 체이닝 시그널 ..."
- 자동 호출 미활성 명시 (정책만 적용, 실 활성화는 Phase 2)
- 6개 파일 변경 후 일관성 검증

### Phase 1-3: Pipeline-Stage 스킬 SKILL.md 수정
- design / workflow 의 `## Boundaries > Will Not` 변경
- Pipeline-Stage 표준 문구 적용 (Mutating 으로도 자동호출 허용 + Pre-flight 보전 명시)
- 2개 파일 변경 후 일관성 검증

### Phase 1-4: Mutating 스킬 SKILL.md 일괄 수정
- implement / refactor / cleanup / document 의 `Will Not` 변경
- plan-* (load / complete / rollback / start / unload / pause / redesign / tasks / list / status / impact) — mutating 분류만 변경
- cl-* (start / save / end / stats) — mutating 분류만 변경
- 표준 문구 "어떤 스킬도 자동으로 호출하지 않음" 적용

### Phase 1-5: review 특별 명시 추가
- review/SKILL.md 에 게이트키퍼 명시 한 줄 추가
- "review 는 Diagnostic 이지만 mutating 자동 호출 명시 차단" 문구 적용
- DESIGN 의 미해결 3번 (확정 사항) 과 일관성 확인

### Phase 1-6: Phase 1 통합 검증
- 모든 SKILL.md 의 분류별 표준 문구 일관성 grep 검증
- 분류 매핑 표 vs 실제 SKILL.md 일치 확인
- DESIGN 의 요구사항 충족 체크박스 1~5 모두 그린 확인

### Phase 2-1: chained 헤더 포맷 도입
- DESIGN 의 `### Activation announcement 변경` 사양 참조
- 모든 스킬의 `## Activation announcement` 섹션에 chained 포맷 예시 추가
- Pipeline-Stage 체이닝 시 `(pipeline)` 태그 명시

### Phase 2-2: Diagnostic 자동호출 활성화 (안전 쌍부터)
- analyze → explain 자동호출 허용 (가장 자연스러운 쌍)
- research → brainstorm 자동호출 허용
- troubleshoot → explain 자동호출 허용 (에러 원인 설명 흐름)
- 각 SKILL.md 의 자동호출 절에서 "미활성" 표기 제거
- 실제 자연어 입력 1~2 케이스 테스트 (사용자 시그널 → 자동 진입)

### Phase 2-3: Pipeline-Stage 자동호출 활성화
- design → implement 자동호출 허용 (DESIGN 의 케이스 2 흐름)
- workflow → plan-load 자동호출 허용 (DESIGN 의 PLAN 저장 후 추적 흐름)
- design → document 자동호출 허용 (설계 직후 저장)
- mutating 스킬 측의 Pre-flight approval 동작 변동 없음 확인 (회귀 검증)

### Phase 3-1: Output appendix 표준 포맷 정의
- DESIGN 의 `### Fact 공유 — Output appendix 강제 규약` 참조
- 모든 스킬 공통 appendix 템플릿 SKILL.md 의 공유 가능한 위치 결정 (예: 각 스킬에 인라인 vs 공통 참조)
- `Collected Facts` 와 `Next Skill Hints` 두 서브섹션 표준화

### Phase 3-2: 모든 스킬 Report 단계에 appendix 추가
- 각 SKILL.md 의 마지막 Step (보통 Report) 에 appendix 생성 단계 추가
- `Behavioral Flow` 와 `Output policy` 두 곳에 appendix 의무 반영
- 25개 파일 변경 후 일관성 검증

### Phase 3-3: 후속 스킬의 appendix 입력 우선 룰 추가
- 각 SKILL.md 의 `Predecessor artifacts` 또는 `Step 1 Analyze` 에 appendix 우선 사용 명시
- "직전 스킬이 appendix 제공했으면 fact 재수집 회피" 룰 추가
- 메인 스킬군 (analyze / design / workflow / implement) 4개 우선 적용 후 나머지

> **Phase 4 — 잠정 후보**: 1-2주 운영 데이터 누적 후 별도 SPEC 으로
> 확정. DESIGN 의 미해결 1번 (체이닝 시그널 형식화 수준) 과 연동.
> 본 그룹의 task 는 현재 PLAN 시점에서는 명시적 가드 부재. 실제
> 진입 결정은 운영 데이터 기반.

### Phase 4-1: 운영 데이터 수집 (조건부 — Phase 3 안정화 후)
- 실 사용 세션에서 자동호출 발생 케이스 로깅
- 오탐 (의도치 않은 자동호출) / 누탐 (사용자 의도였는데 자동호출 안 됨) 케이스 수집
- 1~2주 운영 후 패턴 분석

### Phase 4-2: 체이닝 시그널 패턴 명시화 (선택)
- 운영 데이터 기반 시그널 키워드 / 패턴 정형화
- 각 SKILL.md 의 자동호출 조건에 명시 패턴 추가
- DESIGN 의 미해결 1번 (체이닝 시그널 형식화) 갱신

### Phase 4-3: 거부 조건 추가 (선택)
- 운영에서 발견된 오탐 케이스를 거부 조건으로 추가
- 각 SKILL.md 의 자동호출 차단 신호 목록 보강
- DESIGN 의 미해결 사항 정리

## 미해결 / 추후 결정 사항
- **Phase 1-1 분류 매핑 위치** — DESIGN 본문에 새 섹션으로 추가할지, 별도 `HSPOLICY_CLASSIFICATION.md` 로 뺄지. 권장: DESIGN 본문에 통합 (단일 진실 원천).
- **Phase 2 자동호출 활성화 범위** — 모든 안전 쌍을 동시 활성화할지, 1개씩 단계 활성화할지. 권장: 안전 쌍 3-4개를 한 번에 활성화 (PLAN 의 Phase 2-2 task 단위로).
- **Phase 3 appendix 가시성** — 사용자에게 보이게 할지 / 시스템 영역으로 숨길지. DESIGN 미해결 2번. 권장: 보이게.
- **Phase 4 진입 기준** — Phase 3 완료 후 얼마나 운영 데이터 쌓이면 Phase 4 진입할지. 권장: 1-2주 + 최소 5건 이상의 자동호출 케이스.

## 다음 단계 (사용자 결정)
- 실행 추적 시작: `/hs:plan-load Docs/DEVELOPMENT/Dev/HsPolicy/HSPOLICY_PLAN.md`
- Phase 1 만 즉시 구현: `/hs:implement` 로 바로 진행 (작은 작업이라 plan-load 없이도 가능)
- PLAN 수정: 본 문서 자체 다듬을 부분 있으면 갱신
