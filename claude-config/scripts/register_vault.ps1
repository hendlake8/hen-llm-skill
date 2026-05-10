<#
.SYNOPSIS
    프로젝트의 특정 폴더(기본 Docs)를 Obsidian 마스터 vault에 junction으로 등록한다.

.PARAMETER VaultPath
    Obsidian 마스터 vault 경로 (예: D:\ObsidianVault).
    생략 시 환경 변수 OBSIDIAN_VAULT 사용.

.PARAMETER ProjectRoot
    프로젝트 루트 경로 (예: D:\ClaudeEtc)

.PARAMETER Name
    vault 내 junction 이름의 베이스 (생략 시 프로젝트 루트 폴더명 사용).
    최종 이름은 Name + NameSuffix.

.PARAMETER Subfolder
    프로젝트 내 노출할 서브폴더 (기본 "Docs").
    예: "cl-reports" → cl-stats 마크다운 리포트 노출

.PARAMETER NameSuffix
    junction 이름에 붙는 접미사 (기본 "").
    예: "-cl" → vault 내 표시 이름이 "{ProjectName}-cl"

.EXAMPLE
    # 기본 (Docs 폴더)
    .\register_vault.ps1 -ProjectRoot "D:\ClaudeEtc"

    # 명시적 vault 경로
    .\register_vault.ps1 -VaultPath "D:\ObsidianVault" -ProjectRoot "D:\ClaudeEtc"

    # cl-reports 폴더 등록 (cm_state.py 가 자동 호출)
    .\register_vault.ps1 -ProjectRoot "D:\GitPrjs\hen-llm-skill" -Subfolder "cl-reports" -NameSuffix "-cl"
#>
param(
    [string]$VaultPath,

    [Parameter(Mandatory = $true)]
    [string]$ProjectRoot,

    [string]$Name,

    [string]$Subfolder = "Docs",

    [string]$NameSuffix = ""
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

$linkName = "$Name$NameSuffix"
$targetPath = Join-Path $ProjectRoot $Subfolder
$junctionPath = Join-Path $VaultPath $linkName

# 검증 1: vault 경로 존재 확인
if (-not (Test-Path $VaultPath)) {
    Write-Host "[ERROR] Vault 경로가 존재하지 않음: $VaultPath" -ForegroundColor Red
    exit 1
}

# 검증 2: 대상 폴더 존재 확인
if (-not (Test-Path $targetPath)) {
    Write-Host "[SKIP]  $linkName - $Subfolder 폴더 없음: $targetPath" -ForegroundColor Yellow
    exit 0
}

# 검증 3: junction 중복 확인
if (Test-Path $junctionPath) {
    Write-Host "[SKIP]  $linkName - junction 이미 존재: $junctionPath" -ForegroundColor Yellow
    exit 0
}

# junction 생성
New-Item -ItemType Junction -Path $junctionPath -Target $targetPath | Out-Null
Write-Host "[OK]    $linkName -> $targetPath" -ForegroundColor Green
