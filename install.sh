#!/bin/bash
# hen-llm-skill (hs) 단일 진입점 설치 스크립트 (Unix / macOS / Linux).
#
# Usage:
#   ./install.sh                          # 기본
#   ./install.sh --backup                 # 충돌 시 백업
#   ./install.sh --force                  # 충돌 시 덮어쓰기
#   ./install.sh --obsidian-vault <path>  # OBSIDIAN_VAULT 설정 (~/.bashrc 또는 ~/.zshrc)

set -e

REPO_ROOT="$(cd "$(dirname "$0")" && pwd)"

# 인자 파싱
FORCE=0
BACKUP=0
OBSIDIAN_VAULT_ARG=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --force) FORCE=1; shift ;;
        --backup) BACKUP=1; shift ;;
        --obsidian-vault) OBSIDIAN_VAULT_ARG="$2"; shift 2 ;;
        *) echo "Unknown arg: $1"; exit 2 ;;
    esac
done

echo ""
echo "=== hen-llm-skill (hs) Installer ==="
echo "Repo: $REPO_ROOT"
echo ""

# ============================================================
# Step 1: Python + PyYAML
# ============================================================
echo "[1/5] Python + PyYAML 점검..."

PYTHON_CMD=""
for cmd in python3 python; do
    if command -v "$cmd" >/dev/null 2>&1; then
        PYTHON_CMD="$cmd"
        echo "       Python 발견: $cmd ($("$cmd" --version 2>&1))"
        break
    fi
done

if [ -z "$PYTHON_CMD" ]; then
    echo "[ERROR] Python 미설치. https://python.org 설치 후 재시도." >&2
    exit 1
fi

if "$PYTHON_CMD" -c "import yaml" >/dev/null 2>&1; then
    echo "       PyYAML OK"
else
    echo "       PyYAML 설치 중..."
    "$PYTHON_CMD" -m pip install pyyaml || {
        echo "[ERROR] PyYAML 설치 실패." >&2
        exit 1
    }
fi

# ============================================================
# Step 2: 글로벌 룰 설치
# ============================================================
echo ""
echo "[2/5] 글로벌 룰 설치 (~/.claude/)..."

INSTALL_ARGS=("scripts/install_claude_config.py")
if [ $FORCE -eq 1 ]; then
    INSTALL_ARGS+=("--force")
else
    # 기본: --backup (안전한 default)
    INSTALL_ARGS+=("--backup")
fi

cd "$REPO_ROOT"
OUTPUT=$("$PYTHON_CMD" "${INSTALL_ARGS[@]}" 2>&1) || {
    echo "$OUTPUT"
    echo "[ERROR] 글로벌 룰 설치 실패." >&2
    exit 1
}
echo "$OUTPUT"

# ============================================================
# Step 3: 플러그인 등록 (symlink + marketplace.json)
# ============================================================
echo ""
echo "[3/5] Claude Code 플러그인 등록..."

MP_ROOT="$HOME/.claude/plugins/marketplaces/local"
MP_META="$MP_ROOT/.claude-plugin"
MP_JSON="$MP_META/marketplace.json"
PLUGINS_DIR="$MP_ROOT/plugins"
HS_PLUGIN="$PLUGINS_DIR/hs"

mkdir -p "$MP_META" "$PLUGINS_DIR"

if [ ! -f "$MP_JSON" ]; then
    cat > "$MP_JSON" << EOF
{
  "\$schema": "https://anthropic.com/claude-code/marketplace.schema.json",
  "name": "local",
  "description": "로컬 개인 플러그인 모음",
  "owner": {
    "name": "$USER"
  },
  "plugins": [
    {
      "name": "hs",
      "description": "hendlake personal Claude Code skills",
      "source": "./plugins/hs"
    }
  ]
}
EOF
    echo "       marketplace.json 생성: $MP_JSON"
else
    echo "       marketplace.json 이미 존재 (변경 안 함)"
fi

if [ -L "$HS_PLUGIN" ]; then
    echo "       hs 심볼릭 링크 이미 존재: $HS_PLUGIN"
elif [ -e "$HS_PLUGIN" ]; then
    echo "[ERROR] $HS_PLUGIN 이 심볼릭 링크가 아닌 일반 파일/폴더. 수동 정리 필요." >&2
    exit 1
else
    ln -s "$REPO_ROOT" "$HS_PLUGIN"
    echo "       hs 심볼릭 링크 생성: $HS_PLUGIN -> $REPO_ROOT"
fi

# ============================================================
# Step 4: OBSIDIAN_VAULT 점검
# ============================================================
echo ""
echo "[4/5] OBSIDIAN_VAULT 환경 변수 점검..."

# Shell 설정 파일 결정
SHELL_RC=""
if [ -n "$ZSH_VERSION" ] || [ -f "$HOME/.zshrc" ]; then
    SHELL_RC="$HOME/.zshrc"
elif [ -n "$BASH_VERSION" ] || [ -f "$HOME/.bashrc" ]; then
    SHELL_RC="$HOME/.bashrc"
else
    SHELL_RC="$HOME/.profile"
fi

if [ -n "$OBSIDIAN_VAULT_ARG" ]; then
    # rc 파일에서 기존 OBSIDIAN_VAULT 라인 제거
    if [ -f "$SHELL_RC" ]; then
        grep -v 'export OBSIDIAN_VAULT=' "$SHELL_RC" > "$SHELL_RC.tmp" && mv "$SHELL_RC.tmp" "$SHELL_RC"
    fi
    echo "export OBSIDIAN_VAULT=\"$OBSIDIAN_VAULT_ARG\"" >> "$SHELL_RC"
    echo "       설정 완료 (영구): OBSIDIAN_VAULT = $OBSIDIAN_VAULT_ARG"
    echo "       파일: $SHELL_RC"
    echo "       (새 터미널 또는 'source $SHELL_RC' 후 적용)"
elif [ -n "$OBSIDIAN_VAULT" ]; then
    echo "       현재 세션에 설정됨: $OBSIDIAN_VAULT"
    if ! grep -q "OBSIDIAN_VAULT" "$SHELL_RC" 2>/dev/null; then
        echo "[WARN] 영구 설정 권장: $SHELL_RC 에 export OBSIDIAN_VAULT=... 추가" >&2
    fi
else
    echo "[WARN] OBSIDIAN_VAULT 미설정." >&2
    echo "       Obsidian vault 경로를 영구 설정하세요:" >&2
    echo "         echo 'export OBSIDIAN_VAULT=\"/path/to/vault\"' >> $SHELL_RC" >&2
    echo "       또는 ./install.sh --obsidian-vault \"<path>\" 로 재실행" >&2
fi

# ============================================================
# Step 5: 다음 단계 안내
# ============================================================
echo ""
echo "[5/5] 설치 완료."
echo ""
echo "================================================================="
echo "Claude Code 세션에서 아래를 차례로 복붙하세요."
echo ""
echo "(1) 처음 설치하는 PC:"
echo "    /plugin marketplace add $MP_ROOT"
echo "    /plugin install hs@local"
echo "    /reload-plugins"
echo "    /hs:context-status"
echo ""
echo "(2) 이미 설치된 PC 업데이트:"
echo "    /plugin marketplace update local"
echo "    /reload-plugins"
echo "    /hs:context-status"
echo ""
echo "마지막 명령에서 '[hs:context-status]' 헤더가 나오면 정상."
echo "================================================================="
echo ""
echo "위치 정보:"
echo "  - 플러그인: $HS_PLUGIN"
echo "  - 글로벌 룰: ~/.claude/CLAUDE.md, ~/.claude/rules/ (symlink -> $REPO_ROOT/claude-config/rules)"
echo ""
