# 설치 가이드

## 사전 요구사항

| 항목 | 버전 / 비고 |
|------|----------|
| Python | 3.7+ (3.8+ 권장) |
| PyYAML | `pip install pyyaml` |
| Claude Code | 최신 안정 버전 |
| git | 사용자 식별 (`git config user.name`)에 사용 |
| PowerShell 7+ (`pwsh`) | Windows — `register_vault.ps1` 호출용. 미설치 시 vault 자동 등록 실패. `winget install Microsoft.PowerShell` |

선택 사항:
- **Serena MCP** — 코드 분석 정확도 향상
- **Context7 MCP** — 라이브러리 / 프레임워크 문서

## 설치 단계

### 1. 저장소 클론

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

설치 위치는 자유. Claude Code가 플러그인으로 인식할 수 있는 경로면 됨.

### 2. Python 의존성

```bash
pip install pyyaml
```

또는 가상환경:
```bash
python -m venv .venv
source .venv/bin/activate    # Unix
.venv\Scripts\activate       # Windows
pip install pyyaml
```

### 3. 환경 변수 — `OBSIDIAN_VAULT`

`/hs:document` 스킬이 Obsidian vault junction 자동 등록 시 사용. Obsidian 미사용 시에도 설정 권장 (placeholder 경로라도 OK).

#### Windows
```cmd
setx OBSIDIAN_VAULT "D:\path\to\your\ObsidianVault"
```
(새 터미널부터 적용)

확인:
```cmd
echo %OBSIDIAN_VAULT%
```

#### Unix (macOS / Linux)

`~/.bashrc` / `~/.zshrc` / `~/.profile` 등에 추가:
```bash
export OBSIDIAN_VAULT="/path/to/ObsidianVault"
```

적용:
```bash
source ~/.bashrc    # 또는 해당 파일
echo $OBSIDIAN_VAULT
```

### 4. 글로벌 룰 설치

#### 권장: 단일 진입점 사용

`install.ps1` / `install.sh`가 글로벌 룰 + 플러그인 등록 + 환경 변수 점검을 모두 처리. **이 단계 따로 실행 불필요** — Step 5 참고.

#### 직접 실행 (수동 / 디버그용)

rules 는 복사가 아니라 저장소 `claude-config/rules` 로의 junction(Windows) / symlink(Unix) 연결이다.

```bash
# 기본: 충돌 시 .bak 백업 후 덮어쓰기 (안전)
python scripts/install_claude_config.py --backup

# 강제 덮어쓰기 (백업 없음)
python scripts/install_claude_config.py --force

# 미리보기
python scripts/install_claude_config.py --dry-run
```

`install.ps1` / `install.sh`는 내부적으로 위 명령을 `--backup` default로 호출.

### 5. Claude Code 플러그인 등록

방법은 Claude Code 환경에 따라 다름. 일반적 옵션:

#### A. 마켓플레이스 형식 (권장 — 정식 플러그인 등록)
Claude Code의 marketplace에 추가하는 방식. 자세한 절차는 Claude Code 문서 참조.

#### B. 직접 심볼릭 링크 (개발 중 권장)
플러그인 폴더로 직접 link:
```cmd
:: Windows (관리자 cmd)
mklink /D "%USERPROFILE%\.claude\plugins\hs" "%USERPROFILE%\dev\hen-llm-skill"
```
```bash
# Unix
ln -s ~/dev/hen-llm-skill ~/.claude/plugins/hs
```

(정확한 위치는 Claude Code 버전에 따라 다를 수 있음. `claude --help` 또는 설정 확인.)

### 6. 검증

Claude Code 새 세션 시작 후:

```bash
# 사용자 식별 확인
python scripts/cm_state.py detect-user

# 컨텍스트 측정 확인
python scripts/context_usage.py

# 빈 plan 목록 확인 (정상)
python scripts/plan_state.py list
```

스킬 호출 확인:
```
/hs:context-status
```

`🔍 [hs:context-status]` 헤더로 시작하는 응답이 나오면 정상.

## 업데이트

### 본인이 룰 수정 시

`~/.claude/rules` 는 `claude-config/rules` 로의 junction — 저장소 쪽을 수정하면 즉시 반영된다.

```bash
# claude-config/rules/*.md 수정 후 (배포 단계 없음)
cd ~/dev/hen-llm-skill
git add claude-config/
git commit -m "rules: <changes>"
git push
```

CLAUDE.md / register_vault.ps1 은 복사 배포 대상 — `claude-config/` 쪽 수정 후:
```bash
python scripts/install_claude_config.py --backup
```

### 다른 PC에서 최신 받기

```bash
cd ~/dev/hen-llm-skill
git pull
python scripts/install_claude_config.py --backup
```

### hs 스킬 업데이트만

```bash
git pull
# Claude Code 재시작 — 플러그인 자동 재로드
```

## 다중 사용자 환경

같은 git repo를 여러 명이 사용 시:
- `git config user.name`이 각자 다르면 `.hs/{user}/` 경로가 자동 격리
- 서로의 plan / CM 데이터 안 보임
- `claude-config/`는 공유 (전체 룰 통일)

`OBSIDIAN_VAULT` 환경 변수는 각자 본인 PC에서 따로 설정.

## 트러블슈팅

### `python scripts/...` 호출 시 `ModuleNotFoundError: yaml`
```bash
pip install pyyaml
```

### `OBSIDIAN_VAULT` 환경 변수 미설정 에러
INSTALL.md Step 3 참고.

### `~/.claude/CLAUDE.md` 변경 안 적용됨
- Claude Code 새 세션으로 재시작 필요
- 또는 `/clear` 후 재로드

### 스킬 호출 시 `[hs:foo]` 헤더 안 나옴
- 플러그인 등록 확인 (Step 5)
- `~/.claude/plugins/` 또는 marketplace 설정 확인
- Claude Code 재시작

### 플러그인 등록 후에도 스킬 인식 안 됨
- `.claude-plugin/plugin.json`의 `"name": "hs"` 확인
- 플러그인 경로 정확한지 확인
- 권한 문제 (Windows 심볼릭 링크는 관리자 권한 필요)

### git user.name 미설정
```bash
git config --global user.name "Your Name"
```

## 제거 (uninstall)

```bash
# 1. 플러그인 등록 해제 (Claude Code 설정에서 제거 또는 심볼릭 링크 제거)

# 2. 글로벌 룰 정리 (선택, 백업 권장)
mv ~/.claude/CLAUDE.md ~/.claude/CLAUDE.md.removed
cmd //c rmdir "%USERPROFILE%\.claude\rules"   # junction 링크 제거 (저장소 원본은 유지)
mv ~/.claude/register_vault.ps1 ~/.claude/register_vault.ps1.removed

# 3. 프로젝트별 .hs/ 데이터 삭제 (각 프로젝트에서)
rm -rf .hs/

# 4. 클론 폴더 제거
rm -rf ~/dev/hen-llm-skill
```

## 추가 자료

- [README.md](README.md) — 전체 개요 / 스킬 카테고리
- 스킬 본문 — `skills/<name>/SKILL.md` 각 파일에 사용법 / 예시
