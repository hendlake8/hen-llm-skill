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

## 수정 범위 자기 검증
- 변경된 모든 라인은 사용자 요청에 직접 추적될 수 있어야 한다
- **내 변경이 만든 orphan(미사용 import/변수/함수)만 정리**. 기존 dead code는 발견해도 *보고만* 하고 삭제 금지
- 사유: 요청 범위 초과 수정은 diff 노이즈 + 회귀 위험 + 리뷰 부담. 기존 dead code 정리는 `/hs:cleanup` 명시 호출 시에만 수행
- 버그 픽스 시 **재현 조건 1줄을 먼저 명시한 뒤** 수정한다 (테스트 코드 작성은 필수 아님)
  - 예: "HP 0 이하에서 죽음 처리 누락 → IsDead 체크 추가" 형태로 *재현 조건 → 수정* 순서로 보고
  - 사유: 재현 조건 없이 수정하면 추정 원인이 진짜 원인인지 검증 불가, 같은 버그 재발 위험
  - 단, `/hs:troubleshoot` 진단 결과를 입력으로 받은 경우 재현 조건은 그 fact 를 재인용하면 충분 (중복 명시 불필요)
