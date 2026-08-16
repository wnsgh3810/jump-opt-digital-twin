# Locks and Prohibitions

## 🔒 절대 금지

- ❌ `tau_scale`
- ❌ `motor_tm` LPF
- ❌ CAD 값 변경 (L1=L2=0.25m, LC=0.03m, foot 21mm×13mm)
- ❌ Mode B
- ❌ CSV `kneeCurrentTorquePaper`
- ❌ `v14 canonical rendering pipeline` 수정

## ✅ 필수

- Base-up (Pure CAD → axis 1개씩)
- Drop-test 매 phase
- 외부 출처 ≥ 3 per axis
- Pure Paper sgn(v) only
