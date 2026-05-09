---
name: plan-impact
description: "Phase 변경 시뮬레이션 — 영향 범위 분석 (plan-impact, 영향, 시뮬레이션, 만약). complete/rollback/delete 액션별 결과 미리보기. read-only."
version: 0.1.0
---

# /hs:plan-impact - Change Impact Analysis (Simulation)

## Operating principles
- The user's global rules in `~/.claude/CLAUDE.md` and `~/.claude/rules/*.md`
  are the authoritative persona. Follow them strictly.
- This skill provides procedural guidance only — no identity injection,
  no priority overrides.
- If guidance here conflicts with user rules, user rules win.
- Respond to the user in Korean.

## Activation guard (explicit-only)
This skill activates ONLY via explicit `/hs:plan-impact` invocation.
- Auto-trigger: NEVER.
- Opt-out keywords still apply as a safety net:
  "스킬 쓰지 말고", "그냥 답해줘", "직접 답변", "스킬 빼고" → SKIP.

## Activation announcement
The FIRST line of every response from this skill MUST be a single-line
header in this exact format:

🔍 [hs:plan-impact] <phase_id>[, action: <action>]

Examples:
- 🔍 [hs:plan-impact] Phase 1-2
- 🔍 [hs:plan-impact] Phase 1-2, action: rollback

Leave a blank line after the header, then proceed with the skill's
normal output.

## Workflow position
plan family의 read-only 분석 명령. **상태 변경 없음**.

주된 용도: rollback / delete 같은 위험한 명령 실행 전 영향 범위
미리 확인.

## Triggers
- "Phase X-Y 영향 분석", "이거 롤백하면 어떻게 돼?", "삭제하면 영향?".
- 명시 `/hs:plan-impact <phase_id>` 호출.

## Usage
```
/hs:plan-impact <phase_id> [--action complete|rollback|delete]
```

자연어 추론:
- 첫 인자 = phase_id (필수).
- "완료하면" → `--action complete`
- "롤백하면", "되돌리면" → `--action rollback`
- "삭제하면", "지우면" → `--action delete`
- 액션 없음 → 일반 의존성 분석만.

## Behavioral Flow

### Step 1 — Invoke plan_state.py impact
```bash
python {PLUGIN_ROOT}/scripts/plan_state.py impact <phase_id> [--action <action>]
```

### Step 2 — Parse JSON

### Step 3 — Handle errors
- `plan_not_found`, `phase_not_found` → 한국어 안내.

### Step 4 — Render base dependency analysis (모든 호출 공통)

```
📊 Phase {phase_id} 영향 분석: {phase_name}
현재 상태: {current_status_kr}

🔗 의존성 관계:
   ⬆️ 선행 Phase ({upstream count}개):
   {각 upstream 항목}
   - Phase {id}
   {end}

   ⬇️ 직접 후행 Phase ({direct count}개):
   {각 direct 항목}
   - Phase {id}
   {end}

   🔄 간접 영향 ({indirect count}개):
   {각 indirect 항목}
   - Phase {id}
   {end}

📍 크리티컬 패스: {예/아니오}
```

### Step 5 — Render simulation (action 있을 때)

**`--action complete`**:
```
🔮 완료 시뮬레이션:

해제될 Phase: {released_phases}

진행률 변화:
   현재: {progress_before bar} {percent}%
   예상: {progress_after_estimate bar} {percent}%
```

**`--action rollback`**:
```
🔮 롤백 시뮬레이션:

차단될 Phase ({rework_count}개):
{would_block 각 항목}
- Phase {id}
{end}

⚠️ 재작업 부담: {rework_count}개 Phase 다시 진행 필요.
```

**`--action delete`**:
```
🔮 삭제 시뮬레이션:

고아가 될 Phase ({phases_orphaned 개수}개):
{phases_orphaned 각 항목}
- Phase {id}
{end}

손실될 태스크: {tasks_lost}개

⚠️ {warning 텍스트}
권장: PLAN.md 수정 후 /hs:plan-redesign 사용.
```

### Step 6 — Output policy
- read-only. 어떤 상태도 변경하지 않음.
- 결과는 대화로만.

## Tool coordination
- **Bash** — `plan_state.py impact` 호출.

## Boundaries

**Will:**
- 명시된 Phase의 의존성 그래프 분석 (선행 / 직접 후행 / 간접).
- 액션별 시뮬레이션 (complete / rollback / delete).
- 크리티컬 패스 여부 표시.

**Will Not:**
- 어떤 상태도 변경 (read-only).
- 시뮬레이션 결과를 자동 적용하지 않음 (사용자가 별도 plan-rollback
  등 호출 필요).
- 결과를 파일로 저장하지 않음.
- 다른 스킬 자동 호출.

## Examples

### 기본 영향 분석
```
/hs:plan-impact Phase 1-3
```
→ 의존성 그래프만 표시.

### 롤백 시뮬레이션
```
/hs:plan-impact Phase 1-1 롤백하면
```
→ "/hs:plan-impact Phase 1-1 --action rollback" 추론.
→ 차단될 Phase 미리보기.

### 삭제 시뮬레이션
```
/hs:plan-impact Phase 2-1 삭제하면
```
→ 고아 Phase + 손실 태스크 표시.

## Next Step
- 안전 확인 후 실제 액션 → `/hs:plan-rollback`, `/hs:plan-complete`,
  PLAN.md 수정 + `/hs:plan-redesign` 등.
- 다른 Phase 분석 → 같은 스킬 다시 호출.
- 전체 진행 확인 → `/hs:plan-status`.
