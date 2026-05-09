# 코딩 컨벤션 (모든 언어 공통)

## 클래스
- 대문자로 시작 (PascalCase)
- 예: `class PlayerController`, `class DamageCalculator`

## 인터페이스
- `I` 접두어 + PascalCase
- 예: `interface IMovable`, `interface IDamageable`

## 멤버 변수
- **public 필드**: PascalCase (접두어 없음)
- 예: `public int Health`, `public string PlayerName`
- **private 필드**: `_` 접두어 + camelCase
- 예: `private int _health`, `private string _playerName`
- **public 프로퍼티**: PascalCase (접두어 없음)
- 예: `public int Health { get; set; }`

## 로컬 변수
- 소문자 시작 (camelCase)
- 예: `int count = 0`, `string playerName`

## 함수 파라미터
- 소문자 시작 (camelCase)
- 예: `void SetName(string name)`, `void TakeDamage(int damage)`

## 함수
- 대문자로 시작 (PascalCase)
- static 함수 포함
- 예: `void Initialize()`, `static void CreateInstance()`

## static 변수 / const
- 전부 대문자 + 단어 사이 `_` 연결 (UPPER_SNAKE_CASE)
- 예: `static int MAX_HEALTH`, `const string DEFAULT_NAME`

## enum
- enum 이름: 대문자 시작 (PascalCase)
- enum 값: 대문자 시작 (PascalCase)
- 시작값은 0, 마지막 값은 `Max` (유효성 검사 및 갯수 확인용)
- 특별 지정이 필요한 경우만 시작값 변경
```csharp
enum AtkType
{
    Melee = 0,
    Range,
    Max
}
```
