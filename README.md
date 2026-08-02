# hen-llm-skill (hs)

**Claude Code 위에 얹는 워크플로 하네스.** AI 코딩을 즉흥 작업에서 *구조화·추적 가능한 워크플로*로 바꾼다 — 단일 책임 스킬(`/hs:`), 결정적 상태 관리(작업 추적·세션 로깅), 명시적 승인 게이트.

AI 협업이 즉흥적이고 휘발적이라는 문제를 풀기 위해, Claude Code 위에 **워크플로 오케스트레이션 레이어**를 얹는다. 각 작업을 단일 책임 스킬로 분리하고, 작업 진행·세션 기록을 **결정적 Python 상태머신**으로 관리하며, 파일 변경 전 승인 게이트를 둬 AI 개발 과정을 **추적 가능하고 통제 가능하게** 만든다.

## 특징

- **`/hs:` 네임스페이스** — 26개 스킬 (분석 / 기획 / 구현 / 리뷰 / 컨텍스트 관리 등)
- **사용자 룰 정합** — 글로벌 룰(`~/.claude/CLAUDE.md`, `rules/*.md`)을 페르소나로 사용, 무시 안 함
- **단일 책임 원칙** — 각 스킬이 한 가지 일만, 저장은 `/hs:document` 단일 채널
- **결정적 스크립트** — 상태 관리는 Python 스크립트로 처리 (토큰 효율 + 무결성)
- **다중 사용자 격리** — git user.name 자동 추출로 `.hs/{user}/` 격리

## 빠른 시작

### 1. 클론

기본 권장 위치는 `~/dev/hen-llm-skill`. 사용자 선호로 변경 가능.

```bash
# Unix / macOS
git clone <repo-url> ~/dev/hen-llm-skill
cd ~/dev/hen-llm-skill
```

```powershell
# Windows (PowerShell)
git clone <repo-url> "$env:USERPROFILE\dev\hen-llm-skill"
cd "$env:USERPROFILE\dev\hen-llm-skill"
```

### 2. 환경 변수 설정
```cmd
# Windows
setx OBSIDIAN_VAULT "D:\path\to\your\vault"

# Unix (.bashrc 등에 영속화)
export OBSIDIAN_VAULT=/path/to/your/vault
```

### 3. 글로벌 룰 설치
```bash
# 새 PC: 충돌 없이 설치
python scripts/install_claude_config.py

# 기존 룰 있으면 백업 후 설치
python scripts/install_claude_config.py --backup

# 강제 덮어쓰기
python scripts/install_claude_config.py --force
```

### 4. 단일 진입점 설치 스크립트 (권장)

clone 후 한 명령으로 끝:

```powershell
# Windows (기본 = 기존 ~/.claude/ 파일 자동 백업 후 설치)
.\install.ps1

# 백업 없이 강제 덮어쓰기
.\install.ps1 -Force

# OBSIDIAN_VAULT 동시 설정
.\install.ps1 -ObsidianVault "D:\path\to\vault"
```

```bash
# Unix
chmod +x install.sh
./install.sh
./install.sh --force                        # 백업 없이 덮어쓰기
./install.sh --obsidian-vault "/path/to/vault"
```

LLM에게 git URL만 전달하여 자동 설치 — [INSTALL_FOR_LLM.md](INSTALL_FOR_LLM.md) 참고.

### 5. 의존성
- **Python 3.7+** (`pip install pyyaml`)
- **PowerShell 7+ (`pwsh`)** — Windows, `register_vault.ps1` 호출용 (미설치 시 Obsidian vault 자동 등록만 실패)
- **Claude Code** (Opus 4.7 1M 또는 Sonnet 4.6 권장)
- (선택) **Serena MCP** — 코드 분석 / 구현 정확도 ↑
- (선택) **Context7 MCP** — 라이브러리 / 프레임워크 문서

## 스킬 카테고리

### 가벼운 (auto-triggerable, 4개)
| 스킬 | 용도 |
|------|------|
| `/hs:analyze` | 코드 / 데이터 / 문서 분석 |
| `/hs:brainstorm` | 다용도 브레인스토밍 (소크라테스) |
| `/hs:explain` | 코드 / 개념 / 시스템 설명 |
| `/hs:troubleshoot` | 증상 → 원인 → 해결 진단 |

### 무거운 (explicit-only, 9개)
| 스킬 | 용도 |
|------|------|
| `/hs:research` | 웹 / 문서 리서치 (deep 모드 subagent 위임) |
| `/hs:design` | 구현 설계 (아키텍처 / API / 컴포넌트 / DB) |
| `/hs:workflow` | PLAN.md 작성 (사용자 글로벌 룰 형식) |
| `/hs:implement` | 코드 구현 (functional change) |
| `/hs:refactor` | 리팩토링 (행동 보존) |
| `/hs:cleanup` | 데드 코드 / unused import 제거 |
| `/hs:document` | 모든 산출물의 단일 저장 채널 |
| `/hs:review` | subagent 격리 리뷰 (deep 모드 다중 시각) |
| `/hs:context-status` | 컨텍스트 / 토큰 사용량 측정 |

### CM family (3개) — 채팅 기록 세션
| 스킬 | 용도 |
|------|------|
| `/hs:cl-start` | CM 세션 시작 |
| `/hs:cl-save` | 수동 저장 (Phase 자동 증가) |
| `/hs:cl-end` | 세션 종료 |

### plan family (12개) — 작업 진행 추적
```
plan-load / plan-list / plan-unload          # 라이프사이클
plan-start / plan-pause / plan-complete /
plan-rollback                                # Phase 실행
plan-run                                     # 자동 전체 실행 (★)
plan-tasks                                   # 태스크 단위
plan-status                                  # 진행 현황
plan-redesign / plan-impact                  # 변경 관리
```

## 디렉토리 구조

```
hen-llm-skill/
├── .claude-plugin/plugin.json    # 플러그인 manifest (name: "hs")
├── claude-config/                # 사용자 글로벌 설정 원본 (SSOT)
│   ├── CLAUDE.md
│   ├── rules/                    # 룰 파일 (~/.claude/rules 가 이 폴더로의 junction)
│   └── scripts/register_vault.ps1
├── scripts/
│   ├── _user.py                  # 공통 user detection
│   ├── plan_state.py             # plan 상태 + JSONL 파싱
│   ├── cm_state.py               # CM 상태 + JSONL → CHAT_LOG
│   ├── context_usage.py          # 컨텍스트 / 토큰 측정
│   └── install_claude_config.py  # claude-config/ → ~/.claude/ (파일 복사, rules 는 junction)
└── skills/                       # 26개 SKILL.md
    ├── analyze/SKILL.md
    ├── brainstorm/SKILL.md
    └── ...
```

## 런타임 상태

각 프로젝트에서 hs 사용 시 자동 생성. `{user}` 는 git user.name → OS 사용자 자동 추출 (다중 개발자 격리).

### 로컬 전용 (`.hs/` — gitignore 대상)

채팅 본문, 진행 상태 등 사적 데이터. **절대 공유 금지**.

```
<project>/.hs/{user}/
├── PlanTask/
│   ├── state.yaml                # current_plan
│   └── {plan}/progress.yaml      # plan별 진행 상태
└── CM/
    └── {topic}/
        ├── CM_STATE.json         # 토픽 메타 + 토큰/시간 누적
        └── Phase_NN/CHAT_LOG.md  # 풀 채팅 로그 (도구 호출 결과 포함)
```

### 공유 가능 (`cl-reports/` — git tracked)

cl-stats 가 생성하는 사람용 마크다운 리포트. 채팅 본문 없이 집계 메트릭 + Mermaid 그래프만 포함.

```
<project>/cl-reports/{user}/
└── CL_USAGE_{YYYY-MM-DD_HHMMSS}.md  # 토픽별/사용자별/전체 통계
```

> 📌 토픽명에 민감한 식별자가 들어갈 수 있으니 public repo 에 push 전 검토 권장.

> 🔗 `OBSIDIAN_VAULT` 환경변수가 설정된 Windows 환경이면, `cl-stats --report` 첫 실행 시 vault 에 `{프로젝트명}-cl` junction 이 자동 등록됨 (Obsidian 에서 즉시 열람 가능).

## 글로벌 설정 유지보수

저장소(`claude-config/`)가 진실의 원천(SSOT)이다. `~/.claude/rules` 는 이 저장소로의
junction 이라 rules 수정은 즉시 라이브에 반영된다.

### 룰 변경 시 (개발 PC)
```bash
# claude-config/rules/*.md 수정 (junction 이라 별도 배포 불필요)
git add claude-config/
git commit -m "rules: ..."
git push
```

CLAUDE.md / register_vault.ps1 은 단일 파일이라 복사 배포 대상:
```bash
# claude-config/ 쪽 수정 후
python scripts/install_claude_config.py --backup
```

### 스킬 수정 시
`skills/*/SKILL.md` 는 플러그인 junction 이라 저장소 수정이 곧 라이브 반영 —
새 세션 또는 `/reload-plugins` 부터 적용된다. 커밋/푸시는 rules 와 동일.

### 다른 PC에서 가져오기
```bash
git pull
python scripts/install_claude_config.py --backup  # 파일 갱신 + rules junction 생성
```

## 핵심 워크플로 예시

### 새 기능 구현
```
/hs:brainstorm "X 기능 요구사항"
   ↓ (요구사항 정리됨)
/hs:document → *_SPEC.md 저장
/hs:design "X 시스템 설계"
   ↓
/hs:document → *_DESIGN.md 저장
/hs:workflow "X 구현 PLAN"
   ↓
/hs:document → *_PLAN.md 저장
/hs:plan-load Docs/.../X_PLAN.md
/hs:plan-run                       # 자동 실행 (선택)
또는 /hs:plan-start Phase 1-1     # 수동
```

### 컨텍스트 관리
```
/hs:cl-start "주제명"
... 작업 ...
/hs:context-status                 # 사용량 확인
/hs:cl-save                        # 임계 도달 시 저장
/compact                           # 사용자 직접 입력
... 다음 Phase 작업 ...
/hs:cl-end                         # 종료
```

## 룰 / 정책

본 프로젝트의 스킬 설계 정책:

- **페르소나 주입 없음** — 사용자 글로벌 룰이 페르소나
- **플래그 없음** — 자연어로 의도 추론
- **explicit-only 우선** — 헤비 작업은 사용자 명시 호출 시만
- **MCP는 lazy** — 명확한 조건 충족 시만 발동, fallback 가능
- **저장은 `/hs:document` 단일 채널** — 다른 스킬은 결과 출력만
- **사용자 룰 위반 회피** — 안일한 try-catch / asmdef 자동 생성 등 거부

## 라이선스

개인 사용 / 학습 목적.
