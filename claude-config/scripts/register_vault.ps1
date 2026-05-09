<#
.SYNOPSIS
    프로젝트의 Docs 폴더를 Obsidian 마스터 vault에 junction으로 등록한다.

.PARAMETER VaultPath
    Obsidian 마스터 vault 경로 (예: D:\ObsidianVault).
    생략 시 환경 변수 OBSIDIAN_VAULT 사용.

.PARAMETER ProjectRoot
    프로젝트 루트 경로 (예: D:\ClaudeEtc)

.PARAMETER Name
    vault 내 표시 이름 (생략 시 프로젝트 루트 폴더명 사용)

.EXAMPLE
    # OBSIDIAN_VAULT 환경 변수 사용
    .\register_vault.ps1 -ProjectRoot "D:\ClaudeEtc"

    # 명시적 지정
    .\register_vault.ps1 -VaultPath "D:\ObsidianVault" -ProjectRoot "D:\ClaudeEtc"
    .\register_vault.ps1 -VaultPath "D:\ObsidianVault" -ProjectRoot "D:\GitPrjs\Vams2\Client" -Name "Vams2Client"
#>
param(
    [string]$VaultPath,

    [Parameter(Mandatory = $true)]
    [string]$ProjectRoot,

    [string]$Name
)

# VaultPath 미지정 시 환경 변수 OBSIDIAN_VAULT 사용
if (-not $VaultPath) {
    $VaultPath = $env:OBSIDIAN_VAULT
}

if (-not $VaultPath) {
    Write-Host "[ERROR] VaultPath 미지정 + OBSIDIAN_VAULT 환경 변수도 미설정" -ForegroundColor Red
    Write-Host "        설정 방법:" -ForegroundColor Yellow
    Write-Host "          Windows: setx OBSIDIAN_VAULT `"D:\path\to\vault`"" -ForegroundColor Yellow
    Write-Host "          Unix:    export OBSIDIAN_VAULT=/path/to/vault" -ForegroundColor Yellow
    exit 2
}

# Name 미지정 시 프로젝트 루트 폴더명 사용
if (-not $Name) {
    $Name = Split-Path $ProjectRoot -Leaf
}

$docsPath = Join-Path $ProjectRoot "Docs"
$junctionPath = Join-Path $VaultPath $Name

# 검증 1: vault 경로 존재 확인
if (-not (Test-Path $VaultPath)) {
    Write-Host "[ERROR] Vault 경로가 존재하지 않음: $VaultPath" -ForegroundColor Red
    exit 1
}

# 검증 2: Docs 폴더 존재 확인
if (-not (Test-Path $docsPath)) {
    Write-Host "[SKIP]  $Name - Docs 폴더 없음: $docsPath" -ForegroundColor Yellow
    exit 0
}

# 검증 3: junction 중복 확인
if (Test-Path $junctionPath) {
    Write-Host "[SKIP]  $Name - junction 이미 존재: $junctionPath" -ForegroundColor Yellow
    exit 0
}

# junction 생성
New-Item -ItemType Junction -Path $junctionPath -Target $docsPath | Out-Null
Write-Host "[OK]    $Name -> $docsPath" -ForegroundColor Green
