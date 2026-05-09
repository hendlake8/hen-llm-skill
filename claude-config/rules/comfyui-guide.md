# ComfyUI 환경 정보

이미지 생성은 `/gi` Skill 사용을 권장한다.
워크플로우, 파라미터, API 코드는 Skill과 스타일 파일에 포함되어 있다.

## 서버

| 항목 | 값 |
|------|-----|
| 설치 경로 | `D:\ComfyUI_windows_portable` |
| Python | `{ComfyUI경로}/python_embeded/python.exe` |
| API 서버 | `http://127.0.0.1:8188` |
| 출력 디렉토리 | `E:\AIRes\Img` (--output-directory 설정) |
| GPU | NVIDIA RTX 5080 (VRAM 16GB) |

## 설치된 모델

| 종류 | 모델명 | 경로 |
|------|--------|------|
| 체크포인트 | SDXL Base 1.0 | `checkpoints/SDXL/sd_xl_base_1.0.safetensors` |
| 체크포인트 | AnyLoRA BakedVAE FP16 | `checkpoints/anyloraCheckpoint_bakedvaeBlessedFp16.safetensors` |
| ControlNet | OpenPose XL2 | `controlnet/OpenPoseXL2.safetensors` |
| LoRA | Illustrious MIX | `loras/Mutsumi_Inomata_IL_MIX_V01.safetensors` |
| LoRA | 8bitdiffuser (픽셀아트) | `loras/PX64NOCAP_epoch_10.safetensors` |
| 임베딩 | FastNegativeV2 | `embeddings/FastNegativeV2.pt` |

> 모델 목록은 변경될 수 있다. 새 모델 설치 시 이 표를 업데이트할 것.

## 서버 상태 확인

```bash
curl -s http://127.0.0.1:8188/system_stats
```

응답이 없으면 ComfyUI가 실행되지 않은 것이다.

## 제약

- Flux 모델은 상업적 이용 문제로 사용하지 않음
- LoadImage 노드의 image 값은 ComfyUI input 폴더 기준 상대 경로
  - ComfyUI input 폴더: `D:\ComfyUI_windows_portable\ComfyUI\input\`
- 스크립트 실행은 반드시 ComfyUI 내장 Python 사용:
  `"D:/ComfyUI_windows_portable/python_embeded/python.exe" 스크립트.py`
