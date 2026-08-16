---
name: Auto-approve for long sweeps
description: User grants blanket permission for sweep-related operations during overnight runs
type: feedback
originSessionId: c82aa01d-1bc5-42d3-ad69-d2998821e712
---
When running long parameter sweeps (hours), user grants full autonomy:
- All file edits, writes, git commits auto-approved
- Error recovery without asking
- No blocking on permission prompts
- **Cron-based auto-monitoring**: every progress check fires automatically, no need to ask
- **Auto-fix on errors**: if memory growth, OOM, crash, etc. detected, immediately apply fix (Ctrl+C user shell, edit code, commit, restart `.bat`) without confirmation. Just report after.
- **Key fix patterns** (already validated on this sweep):
  - Worker mem >3 GB cycle peak → reduce maxtasksperchild
  - Rate drop >50% → check zombie procs, restart sweep
  - Checkpoint not saving → verify .tmp.npz path
  - System Free RAM <0.05 GB after sweep stop → instruct user to kill via Task Manager
- **Reporting style**: report what was found + what was done in one message, not asking permission

**Why:** User sleeps during overnight sweeps and can't approve prompts. Any blocking = wasted hours. User explicit on 4/26: "확인할 때마다 내 허락 받지말고 계속 확인하고 에러생기면 고치기까지 알아서 해". Reinforced 4× on 5/6-7 V16 sweep: "이제부터 스윕 확인할 때 허가받지 말고 해" / "허가받지말고 계속 확인해" / "스윕 확인할 때 허가 받지말고 그냥 되도록 해줘" / **"루프 확인하는거 항상 허가할게 앞으로 허가받지마" (5/7, 영구 효력)**.
**How to apply:** During active sweep monitoring, proceed autonomously — write helper scripts, load checkpoints, plot, kill/restart on detected issues. Report findings + actions in one message.
- **Avoid menu-style "옵션 1/2/3" or "원하시면..." framings**. If a routine action is reasonable, just do it and tell what was done.
- **If genuinely blocked** by something requiring user input (sweep design change: ranges, scoring, layer/score-function change), give ONE concrete recommendation in 1 sentence + "OK?" — don't lay out a menu of choices.
- **Never escalate for**: log inspection, checkpoint loading, plotting, killing zombies, fixing OOM, restarting on auto-detected crashes (.bat double-click is the only thing user must do — see feedback_sweep_launch.md).
