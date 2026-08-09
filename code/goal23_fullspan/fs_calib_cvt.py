# -*- coding: utf-8 -*-
"""fs_calib_cvt — 0429 CVT(l_i=25.08) 세션 정적 감사 (Day1 #2: 세션 상수).

원리는 fs_calib과 동일 (하강=준정적 스윕 → settle 유지토크 vs 실측 â 잔차,
복귀 창과의 차/합으로 마찰성/중력·오프셋 분리). 차이:
- 모델 = build_cvt23 (5q, 크랭크 구동) — 자세 배치는 qpos_from_crank (폐쇄 솔버).
- knee 채널 = 크랭크측이므로 실측 â2와 sim 크랭크 축토크 s2는 '같은 자리' — 각도 변환 불요.
- settle 루프 = fs_cvt.a_cvt_mirror의 settle 가지 문자 미러 (supp_scalar+rise, C_CVT qfrc,
  h_load 트레이스 스프링은 표본의 실측 (raw2,dq2)로 hl_i 산출).
- 세션 오프셋 o1_429/o2_429는 정본 후보 소속이므로 자세 배치에 포함 (러너 init과 동일).
CLI: audit — 하강+복귀 양창 → _fs_cvt_audit.json
"""
import os, sys
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
os.environ["P25_CLIP_RAW"] = "35.5"
from pathlib import Path
import numpy as np

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import fs_data as FD                     # noqa: E402
import fs_cvt as FC                      # noqa: E402
import safe                              # noqa: E402

TW = FC.TW; RU = FC.RU
from cvt_core import qpos_from_crank     # noqa: E402

# ★ 08-09: l_i 하드코딩 폐지. trial 마다 `fs_data.cvt_li(trial폴더)` 로 읽는다.
#   (구 0.02499 는 "실측" 주석과 달리 센서 범위 25.06~25.10 **밖**이었다 — 점수 튜닝값)
L_I = 0.02508    # 폴백 기본값 — 결과 경로는 trial 값으로 덮어쓸 것


def _ctx():
    model_c, model_cf, ctx = FC.build_cvt_pair()
    tw = ctx["tw"]; nm = ctx["nm"]
    P = tw["P"]; mj = P.J._P["mj"]; S = P.J._P["S"]
    ks, kref, _ = RU.spr_resolve(model_c, tw["spr"]) if tw["spr"] is not None else (None, None, None)
    qg, rg = RU.rtab(L_I)
    return dict(model=model_c, tw=tw, nm=nm, P=P, mj=mj, S=S,
                ks=ks, kref=kref, qg=qg, rg=rg,
                o1=float(nm["o1_429"]), o2=float(nm["o2_429"]), cc=float(nm["C_CVT"]))


def hold_torque_cvt(C, q1_0, q2_0, hl_i, t_settle=0.5):
    """자세(사지각 q1_0, 크랭크각 q2_0) 정적 유지 축토크 (s1,s2) — settle 문자 미러."""
    P, mj, S, model = C["P"], C["mj"], C["S"], C["model"]
    law_a, law_b, law_v0 = C["tw"]["law"]; kr = C["tw"]["kr"]
    md = mj.MjData(model)
    dof_knee = safe.dofadr(model, "knee", mj)
    iq_k = safe.qadr(model, "knee", mj)
    sq1, sq2 = -q1_0 - np.pi / 2, -q2_0
    md.qpos[:] = qpos_from_crank(1.0, sq1, sq2, L_I)[0]
    mj.mj_forward(model, md)
    fg = mj.mj_name2id(model, mj.mjtObj.mjOBJ_GEOM, "foot")
    md.qpos[0] = 1.0 - float(md.geom_xpos[fg][2]) + S.FOOT_RADIUS
    md.qvel[:] = 0
    mj.mj_forward(model, md)
    dt = model.opt.timestep
    s1 = s2 = 0.0
    for k in range(int(round(t_settle / dt))):
        q1c = -md.qpos[1] - np.pi / 2; q2c = -md.qpos[2]
        v1c = -md.qvel[1]; v2c = -md.qvel[2]
        c1 = S.SETTLE_KP * (q1_0 - q1c) - S.SETTLE_KD * v1c
        c2 = S.SETTLE_KP * (q2_0 - q2c) - S.SETTLE_KD * v2c
        c1 = float(np.clip(c1, -TW.R19.CLIP, TW.R19.CLIP))
        c2 = float(np.clip(c2, -TW.R19.CLIP, TW.R19.CLIP))
        s1 = float(P.J.ahat(P.A_PAPER, np.array([c1]), np.array([v1c]))[0])
        s2 = float(P.J.ahat(P.A_PAPER, np.array([c2]), np.array([v2c]))[0])
        supp = RU.supp_scalar(s2, v2c, law_a, law_b, law_v0)
        if kr:
            supp += float(RU.rise_term(v2c, kr, law_v0))
        rr = float(np.interp(md.qpos[2], C["qg"], C["rg"]))
        amp = max(1.0 / max(abs(rr), 0.2) - 1.0, 0.0)
        vk = float(md.qvel[dof_knee])
        tql = -C["cc"] * abs(s2) * amp * float(np.tanh(vk / 1.0))
        if C["ks"] is not None:
            tql += C["ks"] * (C["kref"] - float(md.qpos[iq_k])) * hl_i
        md.ctrl[:] = [-(s1 + RU.hip_supp_scalar(s1, s2, v1c)), -(s2 + supp)]
        md.qfrc_applied[dof_knee] = tql
        mj.mj_step(model, md)
    ok = abs(md.qvel[1]) < 0.05 and abs(md.qvel[2]) < 0.05
    return s1, s2, bool(ok)


def _win_rows(C, d, idx, step_s=0.10):
    t = d["t"]
    dt = float(np.median(np.diff(t)))
    stride = max(1, int(step_s / dt))
    spr = C["tw"]["spr"]
    rows = []
    for i in idx[::stride]:
        if abs(d["dq1"][i]) > 0.6 or abs(d["dq2"][i]) > 1.2:   # 크랭크측은 무릎보다 빠름 — 완화
            continue
        hl_i = float(RU.hl_vec(np.array([d["raw2"][i]]), np.array([d["dq2"][i]]), spr)[0]) if spr is not None else 0.0
        s1, s2, ok = hold_torque_cvt(C, float(d["q1"][i]) + C["o1"], float(d["q2"][i]) + C["o2"], hl_i)
        rows.append(dict(t=float(t[i]), q1=float(d["q1"][i]), q2=float(d["q2"][i]),
                         a1=float(d["a1"][i]), a2=float(d["a2"][i]), s1=s1, s2=s2, ok=ok))
    return rows


def main():
    C = _ctx()
    OUT = {}
    for s, p, g, cvt, ho in FD.registry():
        if not cvt:
            continue
        try:
            d = FD.load2(p); seg = FD.segment(d)
        except Exception as ex:
            print(f"{p.name}: 로드 FAIL {type(ex).__name__} {ex}", flush=True)
            continue
        t = d["t"]
        down = _win_rows(C, d, np.where(seg["desc"])[0])
        up = _win_rows(C, d, np.where(t >= seg["t_land"] + 0.4)[0])
        if not down:
            print(f"{p.name}: 하강 표본 없음", flush=True)
            continue
        r1d = np.array([r["a1"] - r["s1"] for r in down if r["ok"]])
        r2d = np.array([r["a2"] - r["s2"] for r in down if r["ok"]])
        OUT[p.name] = dict(down=down, up=up)
        msg = f"{p.name}: 하강 n={len(down)}(수렴 {sum(r['ok'] for r in down)}) r1 {r1d.mean():+.2f}±{r1d.std():.2f} | r2 {r2d.mean():+.2f}±{r2d.std():.2f}"
        if up:
            r1u = np.array([r["a1"] - r["s1"] for r in up if r["ok"]])
            if len(r1u):
                r2u = np.array([r["a2"] - r["s2"] for r in up if r["ok"]])
                msg += f" || 복귀 n={len(r1u)} r1 {r1u.mean():+.2f} | r2 {r2u.mean():+.2f}"
        print(msg, flush=True)
    safe.atomic_json_write(HERE / "_fs_cvt_audit.json", OUT)
    # 세션 종합 + 마찰/바이어스 분리
    def _cat(w, key):
        return np.array([r["a" + key] - r["s" + key] for tr in OUT.values() for r in tr[w] if r["ok"]])
    r1d, r2d, r1u, r2u = _cat("down", "1"), _cat("down", "2"), _cat("up", "1"), _cat("up", "2")
    print(f"\n=== 0429 세션 종합 [Nm] ===")
    print(f"하강: r1 {r1d.mean():+.2f}±{r1d.std():.2f} (n={len(r1d)}) | r2 {r2d.mean():+.2f}±{r2d.std():.2f}")
    if len(r1u):
        print(f"복귀: r1 {r1u.mean():+.2f}±{r1u.std():.2f} (n={len(r1u)}) | r2 {r2u.mean():+.2f}±{r2u.std():.2f}")
        print(f"분리: hip 마찰성 {(r1d.mean()-r1u.mean())/2:+.2f} · 중력/오프셋 {(r1d.mean()+r1u.mean())/2:+.2f} || "
              f"crank 마찰성 {(r2d.mean()-r2u.mean())/2:+.2f} · 중력/오프셋 {(r2d.mean()+r2u.mean())/2:+.2f}")
    print("done → _fs_cvt_audit.json")


if __name__ == "__main__":
    main()
