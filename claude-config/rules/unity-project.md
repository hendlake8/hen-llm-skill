# Unity 프로젝트 규칙

## Assembly Definition (asmdef) 사용 금지
- 사용자가 명시적으로 요청하지 않는 한 asmdef 파일 생성 금지
- 레이어/모듈 분리는 namespace로 처리
- 사유: 개발 중 순환 참조 빈번 발생, 도메인 리로드 시간 증가
```
// ❌ 금지 (자동 생성하지 말 것)
Assets/Scripts/Core/GoStopDual.Core.asmdef

// ✅ 권장 (namespace로 분리)
namespace GoStopDual.Core { ... }
namespace GoStopDual.Data { ... }
```

## 런타임 리소스 로드 규칙
- `UnityEditor.AssetDatabase`는 에디터 전용 API이므로 **런타임 코드에서 사용 금지**
- `#if UNITY_EDITOR` + `AssetDatabase.LoadAssetAtPath`는 빌드에서 동작하지 않음
- 런타임에서 동적 로드가 필요하면 `Resources.Load` 또는 `Addressables` 사용
- 스프라이트/프리팹을 런타임에 로드해야 하는 경우 `Resources/` 폴더에 배치
```csharp
// ❌ 금지 (빌드에서 동작 안 함)
#if UNITY_EDITOR
Sprite spr = UnityEditor.AssetDatabase.LoadAssetAtPath<Sprite>("Assets/Textures/icon.png");
#endif

// ✅ 권장 (빌드에서도 동작)
Sprite spr = Resources.Load<Sprite>("Sprites/icon");
```
