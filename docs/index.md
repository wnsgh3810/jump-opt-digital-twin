# Jump-Opt Digital Twin — GOAL19

**Unified 7-dataset Mode A digital twin for 2-DoF single-leg jump robot.**

## 🎯 Current Status

!!! info "진행 중"
    - **Phase 0**: ✅ Pure CAD Baseline (inherited from GOAL18 iter0R) — score **59,736**
    - **Phase 1**: ⏳ 로봇 동역학 (mass + inertia + CoM per part, 7-10D NM)
    - **Alarm**: 2026-07-03 22:00 KST cron

## 📊 Datasets (7 × 31 sub-experiments)

<div class="grid cards" markdown>

- **sit2stand_air_0319** (03.19)  
  1 sub — 공중 sit-to-stand
- **sit2stand_gnd_0319** (03.19)  
  1 sub — 지면 sit-to-stand
- **sit2stand_0324** (03.24)  
  4 subs — firmware PD ×4
- **jump_position_0421** (04.21)  
  6 subs — Position PD
- **jump_torque_0422** (04.22)  
  3 subs — Torque control
- **jump_0424** (04.24)  
  9 subs — Mixed
- **jump_0602** (06.02)  
  6 subs — Mixed

</div>

## 🔑 접근법

**Base-up 검증**: Pure CAD baseline → axis 1개씩 물리적 근거로 추가 → drop-test → keep/drop.

```mermaid
graph LR
    P0[Pure CAD<br/>59,736] --> P1[로봇 동역학<br/>mass+inertia+CoM]
    P1 --> P2[joint friction<br/>fv/fc]
    P2 --> P3[armature<br/>reflected inertia]
    P3 --> P4[contact<br/>solref/imp0]
    P4 --> Final[Unified single param set]
```

## 🔒 절대 금지

- ❌ `tau_scale` 사용
- ❌ `motor_tm` LPF (delay 유발)
- ❌ CAD 값 변경
- ❌ Mode B
- ❌ `kneeCurrentTorquePaper` CSV
- ❌ 좌표 변환 없이 canonical q 사용

## 📖 다음 단계

- [Phase 0 baseline](phase_0/index.md) — 인계 받은 iter0R 상세
- [Phase 1 로봇 동역학](phase_1/index.md) — 진행 중
- [MASTER 발견 통합](insights/master.md)
- [Score function](overview/score.md)

## 🔗 Repository

- Source: [GitHub](https://github.com/example/jump-opt-digital-twin)
- Data: `C:/Users/junho/Desktop/jump_opt/goal18_v13/Iter6/` (로컬 canonical)
