---
name: Sweep launch via .bat double-click only
description: User launches sweeps by double-clicking .bat files manually, NOT via PowerShell/Bash automation
type: feedback
originSessionId: cb42ed46-5d3f-447a-94f6-732ce10d7dfc
---
When starting a long parameter sweep, **user double-clicks the .bat file directly from Explorer** — this is non-negotiable.

**Do NOT**:
- Launch via `PowerShell Start-Process` (adds .NET pipeline overhead)
- Launch via `Bash cmd //c start ...` (similar wrapping)
- Use `Tee-Object` or `tee` for stdout (every print() pays pipeline cost — slows sweep meaningfully)

**Do**:
- Create `run_vXX_sweep.bat` with this exact pattern (cmd-native redirect, no pipeline):
  ```bat
  @echo off
  cd /d %~dp0
  start "PD sweep vXX (...)" cmd /k "python pd_sweep_mp_a1_vXX.py > pd_sweep_a1_vXX_results.txt 2>&1"
  echo vXX sweep launched.
  ```
- Tell the user to double-click the .bat
- Monitor via the redirected `*_results.txt` log + `*_checkpoint.npz` only

**Why:** User explicitly observed PowerShell-wrapped Tee-Object slows sweep ("모든 과정을 일일히 표시하던데 그래서 느린거 아냐"). Even `Start-Process cmd /c run.bat` is suspect — user said "원래 하던대로!!!! 하자고" after that. The user has a stable .bat workflow from v9~v15 (run_v9_sweep.bat … run_v15_sweep.bat all on Desktop). Stick with it.

**How to apply:** When sweep needs to start or restart, prepare the .bat file and tell the user the exact path to double-click. Verify python processes appeared via `Get-Process` after they confirm. Never auto-launch the python script myself.
