# MCP 서버 설치 규칙

> 이 규칙은 MCP 서버 설치/등록 작업 시에만 참고합니다.

## 핵심 원칙

Claude Code는 `~/.claude.json` 파일에서 MCP 서버를 관리합니다.
`~/.claude/settings.json`에 직접 작성하면 인식되지 않습니다.

## 설치 방법

반드시 `claude mcp add` CLI를 사용합니다:

```bash
# 전역 등록 (모든 프로젝트에서 사용)
claude mcp add -s user <서버명> -- <command> [args...]

# 프로젝트 로컬 등록 (현재 프로젝트에서만 사용)
claude mcp add -s local <서버명> -- <command> [args...]
```

## 스코프 옵션 (-s)

| 스코프 | 저장 위치 | 적용 범위 |
|--------|-----------|-----------|
| `user` | `~/.claude.json` | 전역 (모든 프로젝트) |
| `local` | 프로젝트 `.claude/settings.local.json` | 현재 프로젝트만 |
| `project` | 프로젝트 `.mcp.json` | 프로젝트 (git 공유 가능) |

## 주의사항

- `~/.claude/settings.json`에 `mcpServers`를 수동 작성하지 말 것
- 환경 변수가 필요하면 `-e KEY=value` 옵션 사용
- 등록 후 확인: `claude mcp list`, `claude mcp get <서버명>`
