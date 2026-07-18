# -*- coding: utf-8 -*-
"""t0_rollout_long — long 캠페인 최종 결정론 롤아웃 (기존 롤아웃 스크립트 재사용 래퍼).

사용: python t0_rollout_long.py nc|wc|wc2
- T0_TAG = _long(nc/wc) | _long2(wc2) 설정 후 t0nc_rollout / t0wc_rollout .main() 호출
  (nc: t0nc_ppo_long.npz/_audit_long.json/_traj_long.png,
   wc/wc2: t0wc_ppo_long*.npz/_audit_long*.json/_licurve_long*.png — h(l_i) 1mm 그리드).
- 학습과 동일한 crouch 주입 (nc: G["CROUCH"]=티처 q0 / wc: CROUCH_FN l_i별 보간;
  wc2는 liopt 26.25 앵커 포함) — 이것 없이는 정책이 학습한 시작자세와 달라 h가 왜곡.
- 골든·감사 규약은 각 롤아웃 스크립트가 수행 (run_golden + t0_spec.audit).
"""
import os
import sys

camp = sys.argv[1] if len(sys.argv) > 1 else "nc"
assert camp in ("nc", "wc", "wc2"), "usage: python t0_rollout_long.py nc|wc|wc2"
os.environ["T0_TAG"] = "_long2" if camp == "wc2" else "_long"

import t0_train_long as TL


def main(campaign):
    TL.load_env_module(campaign)     # env import + crouch 패치 (롤아웃 전 필수)
    if campaign == "nc":
        import t0nc_rollout as RO
    else:
        import t0wc_rollout as RO
    RO.main()


if __name__ == "__main__":
    main(camp)
