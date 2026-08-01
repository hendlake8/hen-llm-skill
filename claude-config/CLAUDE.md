# Global Rules

## 중요: 언어 설정

**모든 응답은 한국어로 작성해야 합니다.**
- 코드 주석: 한국어
- 설명 및 응답: 한국어
- 에러 메시지 설명: 한국어
- 문서화: 한국어
- 기술 문서는 한글/영어 혼용 가능
- API 문서는 영어 권장
- 변수/함수명: 영어 (국제 표준 준수)

## 중요: 작업 방식
**작업 진행은 대화로 진행 합니다.**
- "할 수 있나?", "가능한가?", "어떨까?" 등 질문형은 실행 요청이 아님

**Bash 명령어 사용 **:
```bash
# ❌ 잘못된 방법 - Git Bash에서 NUL 파일 생성됨
command 2>nul
command 2>NUL
dir 2>nul

# ✅ 올바른 방법 - Unix 스타일 null device 사용
command 2>/dev/null
ls 2>/dev/null
find . -name "*.txt" 2>/dev/null

**중요**: Windows 환경의 Git Bash에서 `2>nul` 또는 `2>NUL`을 사용하면 실제 파일이 생성됩니다. 반드시 `/dev/null`을 사용하세요.

## 중요: 문서화 규칙
분석 작업이나 문제 해결 시 결과를 문서로 남길 때는 다음 규칙을 따릅니다:

### 프로젝트 유형별 적용
- **일반 프로젝트**: 기존 규칙 (Docs/ 아래 주제별 폴더)
- **프로그램 개발 프로젝트**: 아래 GDD/DEV 구조 적용

### 일반 프로젝트 폴더 구조
```
Docs/
├── {주제명}/
│   ├── {분석파일1}.md
│   └── ...
└── ...
```

### 프로그램 개발 프로젝트 폴더 구조
```
Docs/
└── DEVELOPMENT/                      # 개발 문서
    ├── Analyze/                      # 분석, 버그, 에러
    │   └── {시스템명}/
    │       └── {문서}.md
    ├── Dev/                          # 개발 실무 문서
    │   └── {시스템명}/
    │       └── {문서}.md
    └── GameDesign/                   # 기획 문서
        └── {시스템 or 컨텐츠명}/
            └── {문서}.md
```

### 작성 규칙

1. **폴더명**: PascalCase 또는 camelCase 사용
   - 예: `Combat`, `Inventory`, `NetworkSync`

2. **파일명**: 영어 대문자 + 언더스코어 조합
   - 예: `DAMAGE_FORMULA.md`, `HIT_DETECTION_BUG.md`

3. **문서 내부 제목(H1)**: 한국어로 작성
   - 예: 파일명 `DAMAGE_FORMULA.md` → 내부 제목 `# 데미지 공식 설계`

4. **문서 내용**:
   - 문제 상황 및 원인 분석
   - 해결 방안 및 우선순위
   - 실행 계획 (Phase별 체크리스트)
   - 관련 코드 스니펫 및 참고 자료

### 개발 문서 종류 (DEVELOPMENT/Dev)

`Docs/DEVELOPMENT/Dev/{시스템명}/` 하위에 다음 접미사로 문서를 구분한다:

```
Docs/DEVELOPMENT/Dev/{시스템명}/
├── {시스템명}_SPEC.md       ← 요구 명세서 (기능/비기능 요구사항, 결정 사항)
├── {시스템명}_DESIGN.md     ← 구현 설계서 (구조, 흐름, 상세 스펙)
└── {시스템명}_PLAN.md       ← 구현 계획서 (sc:plan 호환, Phase/태스크)
```

| 접미사 | 용도 | 생성 시점 |
|--------|------|-----------|
| `_SPEC` | 요구 명세서 — 무엇을, 왜 만드는지 | 브레인스토밍/요구사항 정리 후 |
| `_DESIGN` | 구현 설계서 — 어떻게 만드는지 | 설계 단계 |
| `_PLAN` | 구현 계획서 — 어떤 순서로 만드는지 | 구현 직전 (sc:plan 호환) |

### 구현 계획서 작성 규칙 (sc:plan 호환)

`/sc:plan-load`로 로드 가능한 계획서 작성 시 다음 형식을 따릅니다.

**저장 위치**: `Docs/DEVELOPMENT/Dev/{시스템명}/` 하위에 `{시스템명}_PLAN.md`
- 예: `Docs/DEVELOPMENT/Dev/Character/PLAYER_MOVEMENT_PLAN.md`

**문서 구조**:
```
# 제목 (한국어)

## 개요
- 목적 및 참조 설계 문서 링크

## 구현 순서

### Phase X-Y: 작업명 (환경)
- 태스크 1
- 태스크 2
```

**작성 규칙**:
1. **구현 순서 헤더**: 반드시 `## 구현 순서`로 작성 (파서가 이 헤더를 탐색)
2. **Phase 형식**: `### Phase X-Y: 이름` (X: 그룹, Y: 순서)
   - 같은 X의 Phase는 병렬 가능, Y가 높으면 X 그룹 내 순서
   - 다른 X 그룹은 이전 X 그룹 전체 완료 후 진행
3. **태스크**: `-` 단순 bullet 형식. 진행 상태는 `/hs:plan-status` 로 확인 (PLAN.md = spec, progress.yaml = 상태 — SSOT 분리. PLAN.md 에 진행 마킹 안 함)
4. **설계 문서 연동**: 개요에 관련 설계 문서(`*_DESIGN.md`) 경로 명시

### 주의사항
- 프로젝트 루트에 직접 분석 파일 생성하지 않기
- 임시 파일은 Docs 폴더 내에서만 생성
- 시스템 단위로 문서를 묶어 한 곳에서 확인 가능하도록 구성

### Obsidian Vault 자동 연결

프로젝트의 `Docs/` 폴더에 문서를 최초 생성할 때, Obsidian 마스터 vault에 junction이 없으면 자동 등록한다.

- **마스터 vault 경로**: `OBSIDIAN_VAULT` 환경 변수
  - 미설정 시 설정 방법:
    - Windows: `setx OBSIDIAN_VAULT "D:\path\to\vault"` (cmd) 또는 시스템 환경 변수에서 직접 설정
    - Unix: `export OBSIDIAN_VAULT=/path/to/vault` (`.bashrc` / `.zshrc` 등에 영속화)
- **등록 스크립트**: `~/.claude/register_vault.ps1`
- **자동 등록 대상**:
  - `Docs/` 폴더 — junction 이름: `{프로젝트명}`. **LLM 트리거**: `Docs/` 에 첫 파일 생성 시 LLM 이 직접 호출.
  - `cl-reports/` 폴더 — junction 이름: `{프로젝트명}-cl`. **자동 트리거**: hen-llm-skill 의 `cm_state.py stats --report` 가 첫 리포트 생성 시 자체 호출 (LLM 관여 X).
- **다른 경로**: 자동 등록 대상 아님 (수동 호출 필요).

**LLM 이 호출해야 하는 경우** (Docs/ 트리거):
```bash
# VaultPath 생략 시 OBSIDIAN_VAULT 자동 사용
pwsh -NoProfile -ExecutionPolicy Bypass -File ~/.claude/register_vault.ps1 -ProjectRoot "{프로젝트루트}"
```

다른 폴더를 수동으로 등록하려면 `-Subfolder` / `-NameSuffix` 사용:
```bash
pwsh -NoProfile -ExecutionPolicy Bypass -File ~/.claude/register_vault.ps1 `
  -ProjectRoot "{프로젝트루트}" -Subfolder "cl-reports" -NameSuffix "-cl"
```

- 스크립트가 vault 경로·대상 폴더 존재·junction 중복을 자동 검증
- PC가 바뀌면 `OBSIDIAN_VAULT` 환경 변수만 수정
