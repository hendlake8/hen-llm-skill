<#
.SYNOPSIS
    hen-llm-skill (hs) 단일 진입점 설치 스크립트 (Windows / PowerShell).

.DESCRIPTION
    수행 단계:
    1. Python + PyYAML 점검
    2. 글로벌 룰 설치 (claude-config → ~/.claude/)
    3. Claude Code 플러그인으로 hs 등록 (junction + marketplace.json)
    4. OBSIDIAN_VAULT 환경 변수 점검
    5. 다음 단계 안내

.PARAMETER Force
    글로벌 룰 충돌 시 강제 덮어쓰기 (백업 없음).

.PARAMETER Backup
    글로벌 룰 충돌 시 .bak 백업 후 덮어쓰기 (default 동작이라 명시 불필요).

.PARAMETER ObsidianVault
    OBSIDIAN_VAULT 환경 변수 값 (지정 시 setx로 영구 설정).

.EXAMPLE
    .\install.ps1
    .\install.ps1 -Backup
    .\install.ps1 -Force -ObsidianVault "D:\ObsidianVault"
#>
param(
    [switch]$Force,
    [switch]$Backup,
    [string]$ObsidianVault
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$repoRoot = $PSScriptRoot

Write-Host ""
Write-Host "=== hen-llm-skill (hs) Installer ===" -ForegroundColor Cyan
Write-Host "Repo: $repoRoot"
Write-Host ""

# ============================================================
# Step 1: Python + PyYAML
# ============================================================
Write-Host "[1/5] Python + PyYAML 점검..." -ForegroundColor Yellow

$pythonCmd = $null
foreach ($cmd in @("python", "python3", "py")) {
    try {
        $version = & $cmd --version 2>&1
        if ($LASTEXITCODE -eq 0) {
            $pythonCmd = $cmd
            Write-Host "       Python 발견: $cmd ($version)"
            break
        }
    } catch { continue }
}

if (-not $pythonCmd) {
    Write-Host "[ERROR] Python 미설치. https://python.org 설치 후 재시도." -ForegroundColor Red
    exit 1
}

try {
    & $pythonCmd -c "import yaml" 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "import failed" }
    Write-Host "       PyYAML OK"
} catch {
    Write-Host "       PyYAML 설치 중..."
    & $pythonCmd -m pip install pyyaml
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ERROR] PyYAML 설치 실패." -ForegroundColor Red
        exit 1
    }
}

# ============================================================
# Step 2: 글로벌 룰 설치
# ============================================================
Write-Host ""
Write-Host "[2/5] 글로벌 룰 설치 (~/.claude/)..." -ForegroundColor Yellow

$installArgs = @("scripts/install_claude_config.py")
if ($Force) {
    $installArgs += "--force"
} else {
    # 기본: --backup (안전한 default)
    $installArgs += "--backup"
}

Push-Location $repoRoot
try {
    $output = & $pythonCmd $installArgs 2>&1 | Out-String
    Write-Host $output

    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ERROR] 글로벌 룰 설치 실패." -ForegroundColor Red
        exit 1
    }
} finally {
    Pop-Location
}

# ============================================================
# Step 3: 플러그인 등록 (junction + marketplace.json)
# ============================================================
Write-Host ""
Write-Host "[3/5] Claude Code 플러그인 등록..." -ForegroundColor Yellow

$marketplaceRoot = Join-Path $env:USERPROFILE ".claude\plugins\marketplaces\local"
$marketplaceMeta = Join-Path $marketplaceRoot ".claude-plugin"
$marketplaceJson = Join-Path $marketplaceMeta "marketplace.json"
$pluginsDir = Join-Path $marketplaceRoot "plugins"
$hsPluginPath = Join-Path $pluginsDir "hs"

# Marketplace 디렉토리 / metadata 생성
New-Item -ItemType Directory -Path $marketplaceMeta -Force | Out-Null
New-Item -ItemType Directory -Path $pluginsDir -Force | Out-Null

if (-not (Test-Path $marketplaceJson)) {
    $manifest = @{
        '$schema' = "https://anthropic.com/claude-code/marketplace.schema.json"
        name = "local"
        description = "로컬 개인 플러그인 모음"
        owner = @{ name = $env:USERNAME }
        plugins = @(
            @{
                name = "hs"
                description = "hendlake personal Claude Code skills"
                source = "./plugins/hs"
            }
        )
    }
    $json = $manifest | ConvertTo-Json -Depth 10
    [System.IO.File]::WriteAllText($marketplaceJson, $json, [System.Text.UTF8Encoding]::new($false))
    Write-Host "       marketplace.json 생성: $marketplaceJson"
} else {
    Write-Host "       marketplace.json 이미 존재 (변경 안 함)"
}

# hs junction 생성 (이미 있으면 재사용)
if (Test-Path $hsPluginPath) {
    $item = Get-Item $hsPluginPath -Force
    if ($item.Attributes -band [System.IO.FileAttributes]::ReparsePoint) {
        Write-Host "       hs junction 이미 존재: $hsPluginPath"
    } else {
        Write-Host "[ERROR] $hsPluginPath 이 junction이 아닌 일반 폴더입니다. 수동 정리 필요." -ForegroundColor Red
        exit 1
    }
} else {
    New-Item -ItemType Junction -Path $hsPluginPath -Target $repoRoot | Out-Null
    Write-Host "       hs junction 생성: $hsPluginPath -> $repoRoot"
}

# ============================================================
# Step 4: OBSIDIAN_VAULT 점검
# ============================================================
Write-Host ""
Write-Host "[4/5] OBSIDIAN_VAULT 환경 변수 점검..." -ForegroundColor Yellow

$currentVault = $env:OBSIDIAN_VAULT
$persistedVault = [System.Environment]::GetEnvironmentVariable("OBSIDIAN_VAULT", "User")

if ($ObsidianVault) {
    [System.Environment]::SetEnvironmentVariable("OBSIDIAN_VAULT", $ObsidianVault, "User")
    Write-Host "       설정 완료 (영구): OBSIDIAN_VAULT = $ObsidianVault"
    Write-Host "       (새 터미널부터 적용)"
} elseif ($persistedVault) {
    Write-Host "       이미 설정됨 (영구): $persistedVault"
} elseif ($currentVault) {
    Write-Host "       현재 세션에 설정됨: $currentVault"
    Write-Host "[WARN] 영구 설정 권장: setx OBSIDIAN_VAULT `"<path>`"" -ForegroundColor Yellow
} else {
    Write-Host "[WARN] OBSIDIAN_VAULT 미설정." -ForegroundColor Yellow
    Write-Host "       Obsidian vault 경로를 영구 설정하세요:" -ForegroundColor Yellow
    Write-Host "         setx OBSIDIAN_VAULT `"D:\path\to\vault`"" -ForegroundColor Yellow
    Write-Host "       또는 install.ps1 -ObsidianVault `"<path>`" 로 재실행" -ForegroundColor Yellow
}

# ============================================================
# Step 5: 다음 단계 안내
# ============================================================
Write-Host ""
Write-Host "[5/5] 설치 완료." -ForegroundColor Green
Write-Host ""
Write-Host "================================================================="
Write-Host "Claude Code 세션에서 아래를 차례로 복붙하세요." -ForegroundColor Cyan
Write-Host ""
Write-Host "(1) 처음 설치하는 PC:"
Write-Host "    /plugin marketplace add $marketplaceRoot" -ForegroundColor White
Write-Host "    /plugin install hs@local" -ForegroundColor White
Write-Host "    /reload-plugins" -ForegroundColor White
Write-Host "    /hs:context-status" -ForegroundColor White
Write-Host ""
Write-Host "(2) 이미 설치된 PC 업데이트:"
Write-Host "    /plugin marketplace update local" -ForegroundColor White
Write-Host "    /reload-plugins" -ForegroundColor White
Write-Host "    /hs:context-status" -ForegroundColor White
Write-Host ""
Write-Host "마지막 명령에서 '[hs:context-status]' 헤더가 나오면 정상." -ForegroundColor Gray
Write-Host "================================================================="
Write-Host ""
Write-Host "위치 정보:" -ForegroundColor Gray
Write-Host "  - 플러그인: $hsPluginPath"
Write-Host "  - 글로벌 룰: ~/.claude/CLAUDE.md, ~/.claude/rules/ (junction -> $repoRoot\claude-config\rules)"
Write-Host ""
