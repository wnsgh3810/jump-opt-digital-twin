# Jump-Opt Digital Twin

**GOAL19**: Unified 7-dataset Mode A digital twin for 2-DoF single-leg jump robot.

## 📊 Datasets

7 experimental datasets, 31 sub-experiments total:

| Date | Dataset | Subs | Description |
|---|---|---|---|
| 03.19 | sit2stand_air_0319 | 1 | 공중, base 고정 |
| 03.19 | sit2stand_gnd_0319 | 1 | 지면, base slide |
| 03.24 | sit2stand_0324 | 4 | PD firmware × 4 gain |
| 04.21 | jump_position_0421 | 6 | Position PD × 6 |
| 04.22 | jump_torque_0422 | 3 | Torque control × 3 |
| 04.24 | jump_0424 | 9 | Mixed × 9 |
| 06.02 | jump_0602 | 6 | Mixed × 6 |

## 🎯 미션

Base 모델 (Pure CAD) → axis-by-axis 물리 검증 → unified single param set이 31 experiment 전부 재현.

**Mode A**: `ctrl = -tau_real` (measured motor τ → sim reproduces real q/dq/GRF)

## 📁 구조

- `code/goal19/` — Phase runners, data loader, sim engine templates
- `code/goal18_CANONICAL/` — v14 LOCKED rendering pipeline (never modify)
- `docs/` — MkDocs Material vault (Phase logs + per-sub details)
- `MASTER_INSIGHTS_G19.md` — 누적 발견
- `GOAL19_PROMPT.md` — 미션 spec
- `CANONICAL_LOCK.md` — v14 rendering LOCK 원칙

## 🌐 Docs

Live docs at: https://wnsgh3810.github.io/jump-opt-digital-twin/

**만약 사이트가 구버전이면** (배포는 성공했으나 서빙 안 될 때):
GitHub → repo **Settings → Pages → Build and deployment → Source** 를 확인:
- **"GitHub Actions"** 로 설정 (현 workflow `.github/workflows/deploy.yml`가 이걸로 배포) — 권장
- 또는 **"Deploy from a branch → `gh-pages` / (root)"** (gh-pages 브랜치에 빌드본 존재)

둘 중 하나로 맞추면 최신 콘텐츠(ablation, 15,182)가 즉시 서빙됨. 모든 콘텐츠는 `main`(소스) + `gh-pages`(빌드본) 브랜치에 안전.

Build locally:
```bash
mkdocs serve   # http://localhost:8000
```

## 🔒 절대 금지

1. `tau_scale` 사용
2. `motor_tm` LPF (delay 유발)
3. CAD 값 변경 (L1=L2=0.25m, LC=0.03m, foot 21mm×13mm)
4. v14 canonical rendering pipeline 수정
5. Mode B
6. CSV `kneeCurrentTorquePaper` 사용
