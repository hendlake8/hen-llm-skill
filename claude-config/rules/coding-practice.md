# 구현 규칙 (모든 언어/엔진 공통)

## 조건문 명시적 비교
- 조건문에서 암묵적 변환 사용 금지
- 함수 반환값을 조건으로 사용할 때도 반드시 비교 대상 명시
- 사유: bool 검사인지, null check인지, 정수형 비교인지, 함수 반환값 검사인지 코드만으로 의도 파악 불가. 디버깅 시 비교 대상이 명확해야 함
- 비교 대상과 연산자를 반드시 명시할 것
```csharp
// ❌ 금지 - 암묵적 변환, 검사 의도 불명확
if (isStop)
if (!isStop)
if (obj)
if (count)
if (string.IsNullOrEmpty(address))
if (!mHandleMap.TryGetValue(key, out var val))

// ✅ 권장 - bool 검사
if (isStop == true)
if (isStop == false)

// ✅ 권장 - null 검사
if (obj == null)
if (obj != null)

// ✅ 권장 - 숫자 검사
if (count == 0)
if (count > 0)
if (count != 0)

// ✅ 권장 - 함수 반환값 검사
if (string.IsNullOrEmpty(address) == true)
if (_handleMap.TryGetValue(key, out var val) == false)
if (Directory.Exists(path) == false)
if (path.Contains("Bundle") == true)
```

## 시그널버스(이벤트 버스) 패턴 사용 규약
- 원칙: 임의 제작한 글로벌 이벤트 브로커(SignalBus/EventBus/MessageBus 등) 사용 금지
- 사유: 디버깅 및 코드 흐름 추적이 어려움
- 예외: 엔진/프레임워크가 기본 제공하거나 프로젝트가 표준으로 채택한 브로커는 사용 가능
- 직접 참조, 인터페이스, 콜백 등 호출 흐름이 명확한 방식을 우선 사용
