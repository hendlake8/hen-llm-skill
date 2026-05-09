# Unity 프로젝트 폴더 구조

> Unity 프로젝트에서만 적용. Assets 폴더가 존재하는 프로젝트에 해당.

## 최상위 폴더 구성

```
Assets/
├── 00.BuildScenes/          # 런타임 씬 파일만 배치 (빌드 대상)
├── 01.Contents/             # 게임 컨텐츠 (빌드 대상)
├── 02.Core/                 # 코어 시스템/프레임워크 코드
├── 03.Process/              # 프로세스/라이프사이클 시스템
├── 04.Data/                 # 데이터 테이블 (빌드 대상)
├── 05.WorkScenes/           # 테스트/작업용 씬 (빌드 대상 아님)
└── 99.ResetByRelease/       # 릴리즈 시 초기화 대상
```

## 00.BuildScenes

- 씬 파일(.unity)만 배치
- 씬을 구성하는 리소스/스크립트는 01.Contents의 해당 컨텐츠 폴더에 위치
- 씬 번호로 순서 관리 (0.Boot, 1.Clear, 2.Title, 3.Game)

## 01.Contents (컨텐츠별 구성)

컨텐츠 단위로 Scripts, RES 등 모든 구성품을 한 곳에 모아서 관리한다.
타입별(scripts/, images/) 분리가 아닌 **컨텐츠별 분리** 원칙.

```
01.Contents/
├── {Category}/                  # 카테고리 (선택적)
│   └── {ContentName}/           # 컨텐츠 단위
│       ├── Scripts/
│       └── RES/
│           ├── Bundle/          # Addressable 에셋번들 대상
│           │   ├── Animations/
│           │   ├── Atlas/
│           │   └── Prefabs/
│           ├── Origin/          # 원본 리소스 (빌드 비포함, 참조 금지)
│           │   └── Images/
│           └── Resources/       # Resources.Load 대상 (내장 리소스)
│               ├── Animations/
│               ├── Atlas/
│               └── Prefabs/
│
├── Global/                      # 전역 공유 리소스 (폰트 등)
│   └── Font/
│       ├── FontSource/
│       └── RES/Builtin/
│
└── {ContentName}/               # 카테고리 없이 바로 배치도 가능
    ├── Scripts/
    └── RES/
        └── ...
```

### Bundle/ 번들 단위 규칙
- Bundle/ 하위에 폴더가 있으면 → 각 폴더가 하나의 에셋번들
- Bundle/ 바로 아래에 파일이 있으면 → Bundle/ 자체가 하나의 에셋번들
- Bundle/ 안의 에셋이 참조하는 리소스도 Bundle/ 안에 배치 (중복 방지)

### Origin/ 아틀라스용 개별 이미지
- SpriteAtlas에 등록할 개별 스프라이트 이미지를 모아두는 폴더
- 프리팹/씬에서 해당 스프라이트를 Inspector로 직접 참조 가능
- 빌드 시 아틀라스에 포함된 스프라이트는 원본 텍스처가 strip되고 아틀라스 텍스처만 포함됨
- PSD 등 작업 소스 파일을 넣는 곳이 아님

### Resources/ 내장 리소스
- Addressables 초기화 전에 필요한 에셋 (로딩 UI, 기본 폰트 등)
- `ResourceManager.Instance.Load<T>(path, true)`로 로드

## 02.Core

코어 시스템/프레임워크 코드. 모듈 단위로 구성.

```
02.Core/
├── AssetManagementSystem/       # 리소스 운영 시스템 (Addressables 래핑)
│   ├── Runtime/
│   │   ├── ResourceManager.cs
│   │   ├── AssetTracker.cs
│   │   └── PatchHandler.cs
│   └── Editor/
│       ├── AddressableRegistrar.cs
│       ├── AddressableAutoRegistrar.cs
│       └── AddressablePathCopier.cs
│
├── SceneController/             # 씬 로드 관리 시스템
│   ├── Runtime/
│   │   ├── SceneData.cs
│   │   ├── SceneController.cs
│   │   └── SceneNames.cs        # 자동 생성
│   └── Editor/
│       ├── SceneDataAutoCreator.cs
│       └── SceneNamesGenerator.cs
│
├── DefineSymbolManager/         # 전처리 심볼 관리 도구
│   └── Editor/
│       ├── DefineSymbolData.cs
│       └── DefineSymbolManagerWindow.cs
│
├── EditorDefine/                # 에디터 전용 상수 정의
│   └── Editor/
│       └── EditorDefine.cs
│
├── Utilities/                   # 공용 유틸리티
│   ├── ArrayBuffer/
│   ├── MonoSingleton/
│   └── Logger/
│
└── {ModuleName}/                # 추가 모듈 (필요 시)
    ├── Runtime/                 # 런타임 코드 (있는 경우만)
    └── Editor/                  # 에디터 전용 코드 (있는 경우만)
```

## 03.Process

프로세스/라이프사이클 시스템.

```
03.Process/
├── Bootstrap.cs                 # 앱 진입점 (RuntimeInitializeOnLoadMethod)
└── Lifecycle/                   # 라이프사이클 이벤트 시스템
    ├── SystemReceiver.cs        # Unity 라이프사이클 → 디스패처 중계
    ├── IProcessLife.cs          # 마커 인터페이스
    ├── Lifes/                   # 개별 라이프사이클 인터페이스
    │   ├── IBoot.cs
    │   ├── IStart.cs
    │   ├── IUpdate.cs
    │   └── ...
    └── Editor/
        └── Generator/           # 디스패처 Source Generator
```

## 04.Data

데이터 테이블.

```
04.Data/
├── Scripts/                     # 데이터 관련 코드
└── RES/
    ├── Bundle/                  # 에셋번들 대상 데이터
    ├── Origin/                  # 원본 데이터
    └── Resources/               # 내장 데이터
```

## 05.WorkScenes

- 테스트/작업용 씬 (빌드 대상 아님)
- 기능 테스트, 프로토타이핑 등에 사용

## 99.ResetByRelease

- 릴리즈 시 초기화/정리 대상
- 개발 중에만 사용하는 임시 리소스
