# PowerShell 스크립트 인코딩

## 원칙

한글 등 비-ASCII 문자가 포함된 `.ps1` 파일은 **UTF-8 with BOM** 으로 저장한다.

## Why

Windows PowerShell 5.1 (Win10/11 기본 셸) 은 BOM 없는 파일을 시스템 코드페이지(cp949) 로 해석. 한글이 박힌 BOM-less PS1 은 파서가 문자열 종결자를 못 찾고 깨짐.

에러 메시지 함정: 실제 원인은 인코딩인데 PowerShell 은 *"문자열에 \" 종결자가 없습니다"* 라고 표시 → 따옴표 빠진 줄을 찾느라 시간 낭비하기 쉬움.

PowerShell 7+ (`pwsh`) 는 기본 UTF-8 이라 BOM 없어도 OK. 하지만 사용자 PC 가 5.1 이면 깨짐.

## How to apply

### 신규/수정 시
Claude Code 의 Write/Edit 도구는 PS1 에 BOM 을 자동 부착하지 않는다. **수동 보정 필요**:

```bash
python -c "
import io
p = 'path/to/script.ps1'
with io.open(p, 'r', encoding='utf-8') as f: c = f.read()
with io.open(p, 'w', encoding='utf-8-sig', newline='') as f: f.write(c)
"
```

또는 PowerShell 에서:
```powershell
$p = 'path\to\script.ps1'
$c = Get-Content -Raw -Encoding UTF8 $p
[System.IO.File]::WriteAllText($p, $c, (New-Object System.Text.UTF8Encoding $true))
```

### 검증
```bash
head -1 file.ps1 | od -c | head -1
# 첫 3바이트가 357 273 277 (EF BB BF) 면 BOM 정상
```

### 예외
- ASCII-only PS1 → BOM 불필요
- 사용자가 pwsh 7+ 전용 환경 명시 → BOM 불필요

## 트리거 케이스

다음 패턴이 보이면 BOM 점검:
- `.ps1` 파일에 한국어 주석 / 문자열 작성
- 기존 `.ps1` 수정 (Edit 도구 사용 후 원본 BOM 유지 여부 보장 안 됨)
- PowerShell 실행 시 *"문자열 종결자 없음"* 또는 *"닫는 '}' 부족"* 류 파싱 에러
