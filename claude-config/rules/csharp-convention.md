# C# 코딩 컨벤션

> C# 프로젝트에서만 적용한다.

## XML 문서 주석 (Summary)

모든 클래스, 인터페이스, enum, 메서드(public/private), 프로퍼티에 `<summary>` 주석을 작성한다.
메서드에는 `<param>`, `<returns>` 태그도 포함한다.

```csharp
/// <summary>
/// 플레이어의 이동과 입력을 처리하는 컨트롤러.
/// </summary>
public class PlayerController : MonoBehaviour

/// <summary>
/// 이동 가능한 오브젝트가 구현하는 인터페이스.
/// </summary>
public interface IMovable

/// <summary>
/// 공격 유형.
/// </summary>
public enum AtkType

/// <summary>
/// 현재 체력.
/// </summary>
public int Health { get; private set; }

/// <summary>
/// 대상에게 데미지를 적용한다.
/// </summary>
/// <param name="damage">적용할 데미지 값</param>
/// <param name="target">데미지를 받을 대상</param>
/// <returns>실제 적용된 데미지</returns>
public int ApplyDamage(int damage, GameObject target)

/// <summary>
/// 내부 체력 갱신 처리.
/// </summary>
/// <param name="amount">변경량</param>
private void UpdateHealthInternal(int amount)
```

## #region 사용

관련 메서드를 기능 단위로 `#region`으로 묶어 구조화한다.

```csharp
#region Initialize
public void Initialize() { }
private void SetupComponents() { }
#endregion

#region Combat
public int ApplyDamage(int damage, GameObject target) { }
private void UpdateHealthInternal(int amount) { }
#endregion
```

## 타입 선언

가급적 명시적 타입을 선언한다. `var`는 명시적 타입보다 가독성이나 재사용성에 유리한 경우 사용 가능하다.

```csharp
// ✅ 기본: 명시적 타입 선언
int count = 0;
string playerName = "Hero";
List<int> scores = new List<int>();

// ✅ 허용: 타입이 길거나 우변에서 타입이 명확한 경우
var dict = new Dictionary<string, List<AudioSource>>();
var controller = GetComponent<PlayerController>();
```

## Nullable 표현

가급적 nullable(`?`) 표현을 피한다. 실제로 null이 의미 있는 경우에는 사용 가능하다.

```csharp
// ❌ 불필요한 nullable
int? health = 100;

// ✅ 허용: null이 유효한 의미를 가지는 경우
AudioClip? FindCachedClip(string address)
```
