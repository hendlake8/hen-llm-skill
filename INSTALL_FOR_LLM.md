# LLM Install Instructions

> **이 문서는 LLM이 사용자로부터 git URL만 받았을 때 자율 설치 수행을 위한 지침입니다.**
> 사용자(인간)는 [INSTALL.md](INSTALL.md)를 보세요.

## When this applies

User says (대략):
- "{repo-url} 설치해줘"
- "이거 깔아줘 {repo-url}"
- "Install hen-llm-skill from {repo-url}"

## Mandatory pre-checks

### 1. 권한 확인
설치는 다음 디스크 변경을 동반:
- 사용자 홈 디렉토리 아래 파일 생성/수정/삭제 (`~/.claude/`)
- 임의 위치에 git clone
- 환경 변수 영구 설정 (선택)

→ 위 작업 권한이 자동 허용 가능한 환경인지 확인. 아니면 사용자에게 확인 요청.

### 2. 운영체제 확인
```bash
echo $OSTYPE   # Unix: linux-gnu, darwin*
ver            # Windows: Microsoft Windows ...
```
→ Windows: `install.ps1` 사용. Unix/macOS: `install.sh` 사용.

### 3. Python 사전 확인 (필수)
```bash
python --version || python3 --version
```
install 스크립트가 Python 3.7+ 에 의존. 없으면 사용자에게 알리고 정지 (설치 못 함).

### 4. pwsh 사전 확인 (Windows, warn 수준)
```bash
pwsh -v
```
`register_vault.ps1` 호출(Obsidian vault junction 자동 등록)이 PowerShell 7+ (`pwsh`) 에 의존.
미설치여도 설치는 진행하되, 사용자에게 안내: `winget install Microsoft.PowerShell`

## Install procedure (정확히 이 순서)

### Step 1: Clone

기본 권장 위치는 `~/dev/hen-llm-skill` (Claude Code가 자동 인식하는 영역과 분리).
사용자 선호로 변경 가능 — 위치 결정 후 사용자에게 1회 알림.

#### Unix / macOS (bash / zsh)
```bash
TARGET="$HOME/dev/hen-llm-skill"
git clone <repo-url> "$TARGET"
cd "$TARGET"
```

#### Windows (PowerShell)
```powershell
$TARGET = "$env:USERPROFILE\dev\hen-llm-skill"
git clone <repo-url> "$TARGET"
cd "$TARGET"
```

### Step 2: OBSIDIAN_VAULT 입력 받기

Obsidian 사용자면 vault 경로 필요. 미사용자도 placeholder 권장.

다음 중 하나로:
- 사용자에게 1회 질문: "Obsidian vault 경로? (없으면 'D:\\ObsidianPlaceholder' 같은 임의값 OK)"
- 또는 install 스크립트의 `-ObsidianVault` / `--obsidian-vault` 인자로 전달

### Step 3: install 스크립트 실행

#### Windows (PowerShell):
```powershell
cd $TARGET
.\install.ps1 -ObsidianVault "<사용자 입력 경로>"
```

#### Unix:
```bash
cd "$TARGET"
chmod +x install.sh
./install.sh --obsidian-vault "<사용자 입력 경로>"
```

기본 동작 = 기존 ~/.claude/ 파일 충돌 시 자동 .bak 백업 후 덮어쓰기 (안전 default).
rules 는 복사가 아니라 junction(Windows) / symlink(Unix) 연결 — 기존 실폴더는 `rules.bak` 으로 이동 후 연결.
사용자가 백업 없이 강제 덮어쓰기 명시하면 `-Force` / `--force` 추가.

### Step 4: 결과 확인

스크립트 종료 코드가 0이면 성공. 아니면 stdout/stderr 확인 후 사용자에게 보고.

### Step 5: 사용자 안내

설치 성공 시 다음 메시지를 사용자에게 한국어로 그대로 전달.
사용자가 슬래시 명령을 본인의 Claude Code 세션에 직접 입력해야 플러그인이 활성화됨 (LLM은 슬래시 명령 자동 실행 불가):

```
✅ hen-llm-skill 설치 완료.

Claude Code 세션에서 아래를 차례로 복붙하세요.

(1) 처음 설치하는 PC:
    /plugin marketplace add <MARKETPLACE_ROOT>
    /plugin install hs@local
    /reload-plugins
    /hs:context-status

(2) 이미 설치된 PC 업데이트:
    /plugin marketplace update local
    /reload-plugins
    /hs:context-status

마지막 명령에서 '[hs:context-status]' 헤더가 나오면 정상.

설치 위치:
- 플러그인: ~/.claude/plugins/marketplaces/local/plugins/hs (junction → {TARGET})
- 글로벌 룰: ~/.claude/CLAUDE.md, ~/.claude/rules/ (junction → {TARGET}/claude-config/rules)

문제 발생 시:
- {TARGET}/INSTALL.md 트러블슈팅 섹션 참고
```

`<MARKETPLACE_ROOT>` 는 OS별로 다음 절대경로로 치환:
- Windows: `%USERPROFILE%\.claude\plugins\marketplaces\local` (실제 expand된 절대경로)
- Unix:    `$HOME/.claude/plugins/marketplaces/local` (실제 expand된 절대경로)

install 스크립트가 종료 시 위 블록을 실제 절대경로로 채워서 그대로 출력하므로,
LLM은 스크립트 stdout을 그대로 사용자에게 전달하면 됨.

## Common failure modes

### A. Conflict (해당 없음 — 기본 동작에서 자동 처리)
- 기본이 백업 후 덮어쓰기라 충돌 자체가 발생 안 함
- 사용자가 `-Force` / `--force` 명시 시만 백업 없이 덮어쓰기

### B. Python 미설치
- Python 3.7+ 설치 안내, 진행 정지

### C. PyYAML 설치 실패
- `pip` 권한 / 네트워크 문제
- 해결: `python -m pip install --user pyyaml`

### D. Junction 생성 실패 (Windows)
- 일반적으로 Windows에서 junction은 관리자 권한 불필요
- 그래도 실패 시 수동 안내:
  ```cmd
  mklink /J "%USERPROFILE%\.claude\plugins\marketplaces\local\plugins\hs" "{TARGET}"
  mklink /J "%USERPROFILE%\.claude\rules" "{TARGET}\claude-config\rules"
  ```
  (rules 쪽은 기존 실폴더가 있으면 먼저 백업/제거 필요)

### E. OBSIDIAN_VAULT 미설정 (warn)
- 설치는 성공하지만 경고
- 사용자에게 전달:
  ```
  setx OBSIDIAN_VAULT "<your vault path>"
  ```

### F. 플러그인 미인식 (Claude Code 재시작 후에도 /hs:* 호출 안 됨)
- Claude Code의 marketplace 등록이 마켓플레이스.json 자동 인식 안 할 수 있음
- 1차 시도: Claude Code 새 세션에서 `/plugin` 명령으로 marketplace 'local' 활성화 안내
- 2차 시도: 사용자에게 직접 marketplace 등록 명령 실행 요청
- INSTALL.md 트러블슈팅 참고

### G. pwsh 미설치 (Windows)
- 증상: `pwsh` 명령 인식 안 됨 → `register_vault.ps1` 호출 실패 (vault junction 자동 등록 불가)
- 스킬 본체 동작에는 영향 없음 — warn 후 진행
- 해결: `winget install Microsoft.PowerShell` 안내

## Do NOT do

- ❌ 사용자 의도 없이 ~/.claude/ 의 다른 파일 변경
- ❌ ~/.claude/settings.json 직접 편집 (인증 정보 위험)
- ❌ Claude Code 강제 종료 / 재시작 (사용자가 직접)
- ❌ 다른 LLM 도구 (sc, cm, gd 등) 임의 제거
- ❌ git history 변경 (clone만)

## Verification commands (실행 후)

```bash
# 사용자 식별
python "$TARGET/scripts/cm_state.py" detect-user

# 컨텍스트 측정 (새 세션 후)
python "$TARGET/scripts/context_usage.py"

# 글로벌 설정 확인
ls ~/.claude/CLAUDE.md ~/.claude/rules/ ~/.claude/register_vault.ps1
```

## Update procedure

이미 설치된 hen-llm-skill 업데이트 요청 시:

```bash
cd "$TARGET"
git pull
./install.sh --backup    # 또는 install.ps1 -Backup
```

rules 는 junction 이라 `git pull` 만으로 즉시 반영된다.
install 재실행은 복사 배포 파일(CLAUDE.md, register_vault.ps1) 갱신용 (멱등 — rules 는 "이미 연결됨"으로 skip).
