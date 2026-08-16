# -*- coding: utf-8 -*-
"""fs_metric — GOAL23 채점 하네스: 전구간(앉기~이륙) CL/ModeA 양방향 + 바닥 + 베이스라인.

CL   = 앉기 개시(정지 상태)에서 settle 후 통짜 폐루프 (PD가 안정화 — 통짜 가능).
ModeA = mshoot 0.4s 창·0.3s 스트라이드·측정상태 리셋 (P19 규약 — 개루프 장구간 발산 방지, h14 교훈).
채널 = q1,q2 [°] · dq1,dq2 [rad/s] · τ1,τ2 [Nm] RMSE. 전구간(score)+서브(desc/push) 병기.
바닥(floor) = hold0/prehold 정지 창의 측정 std (센서 노이즈 한계).
베이스라인 = OLD α(fit 세션은 정본 R19.ALPH) vs 변형 C — 졸업 기준의 분모.
0429(CVT)는 Day2 러너 정비 후 편입. 0324(HO)는 ModeA만.
CLI: baseline · floor
"""
import os, sys, json
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
os.environ["P25_CLIP_RAW"] = "35.5"
from pathlib import Path
import numpy as np

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "goal22" / "p25_task0"))
sys.path.insert(0, str(HERE.parent / "goal22" / "p25_deploy"))
sys.path.insert(0, str(HERE.parent / "goal22" / "p26_sea"))
import fs_data as FD                     # noqa: E402
import p25_a_twin as TW                  # noqa: E402
from sea_twin2 import rollout_cl_sea2    # noqa: E402

TH = {60: 0.70, 120: 0.50, 150: 0.40}
TK = {60: 0.85, 120: 0.789, 250: 0.656, 500: 0.40}
R19A = getattr(TW.R19, "ALPH", {})
ALPH_SESS = {"26.04.24": R19A.get("jump_0424"), "26.06.02": R19A.get("jump_0602"),
             "26.04.21": R19A.get("jump_position_0421")}
MSHOOT_W, MSHOOT_S = 0.4, 0.3
L_SEG = 0.25   # h14b FK 근사 (창 리셋 초기화 전용 — 채점엔 영향 미미)

tw0 = TW.twin()
P = tw0["P"]; mj = P.J._P["mj"]; S = P.J._P["S"]


def st_from_meas(tw, q1_0, q2_0, dq1_0, dq2_0, r1, r2):
    """측정 상태로 sim 초기화 (h14b 미러: FK 발접지 + 베이스 속도 근사)."""
    model = tw["model"]; md = mj.MjData(model)
    sq1, sq2 = -q1_0 - np.pi / 2, -q2_0
    md.qpos[:] = [1.0, sq1, sq2, -sq2, sq2]
    mj.mj_forward(model, md)
    fg = mj.mj_name2id(model, mj.mjtObj.mjOBJ_GEOM, "foot")
    md.qpos[0] = 1.0 - float(md.geom_xpos[fg][2]) + S.FOOT_RADIUS
    c1, c12 = np.cos(q1_0), np.cos(q1_0 + q2_0)
    dbz = -L_SEG * (c1 * dq1_0 + c12 * (dq1_0 + dq2_0))
    md.qvel[:] = [dbz, -dq1_0, -dq2_0, dq2_0, -dq2_0]
    mj.mj_forward(model, md)
    return dict(qpos=md.qpos.copy(), qvel=md.qvel.copy(), c1f=float(r1), c2f=float(r2))


def _rmse6(d, m, q1s, q2s, dq1s, dq2s, t1s, t2s):
    return (float(np.degrees(np.sqrt(np.mean((d["q1"][m] - q1s[m]) ** 2)))),
            float(np.degrees(np.sqrt(np.mean((d["q2"][m] - q2s[m]) ** 2)))),
            float(np.sqrt(np.mean((d["dq1"][m] - dq1s[m]) ** 2))),
            float(np.sqrt(np.mean((d["dq2"][m] - dq2s[m]) ** 2))),
            float(np.sqrt(np.mean((d["a1"][m] - t1s[m]) ** 2))),
            float(np.sqrt(np.mean((d["a2"][m] - t2s[m]) ** 2))))


def score_cl(d, seg, model_kind, gains):
    """CL 통짜 (앉기 개시~이륙). model_kind: 'OLD'|'C'. 반환 {win: 6채널} | None."""
    i0 = max(0, seg["i_desc"] - 5)
    sl = slice(i0, None)
    t = d["t"][sl] - d["t"][i0]
    t_end = seg["t_lo"] - d["t"][i0]
    qd1, qd2 = d["qd1"][sl], d["qd2"][sl]
    dqd1, dqd2 = d["dqd1"][sl], d["dqd2"][sl]
    if model_kind == "OLD":
        sess_al = ALPH_SESS.get(d.get("_sess"))
        alphas = tuple(sess_al) if sess_al else (TH.get(gains[0], 0.40), 0.20, TK.get(gains[2], 0.656), 0.20)
        L = TW.rollout_cl(tw0, t, qd1, qd2, dqd1, dqd2, tuple(gains), alphas=alphas,
                          t_end=t_end, t_after=0.05)
        if L is None:
            return None
        gi = lambda k: np.interp(t, L["t"], L[k])
        q1s, q2s, dq1s, dq2s, t1s, t2s = (gi(k) for k in ("q1", "q2", "dq1", "dq2", "sh1", "sh2"))
    else:
        gm = (gains[0], gains[1], gains[2] * TK.get(gains[2], 0.656), gains[3] * 0.20)
        L = rollout_cl_sea2(tw0, t, qd1, qd2, dqd1, dqd2, gm, t_end=t_end, t_after=0.05,
                            ks1=96.0, ks1_hi=323.0, tau0_1=9.0, bs1=1.5, jm1=0.01, ks2=None)
        if L is None:
            return None
        q1s = np.interp(t, L["t"], L["thm1"])
        q2s = np.interp(t, L["t"], L["q2"])
        dq1s = np.interp(t, L["t"], np.gradient(L["thm1"], L["t"]))
        dq2s = np.interp(t, L["t"], np.gradient(L["q2"], L["t"]))
        t1s = np.interp(t, L["t"], L["tsp1"])
        t2s = np.interp(t, L["t"], L["tsp2"])
    dd = {k: (v[sl] if hasattr(v, "__len__") and len(v) == len(d["t"]) else v) for k, v in d.items()
          if k in ("q1", "q2", "dq1", "dq2", "a1", "a2")}
    out = {}
    n0 = i0
    for win in ("score", "desc", "push"):
        m = seg[win][sl.start:] if sl.start else seg[win]
        m = m[: len(t)]
        if m.sum() < 10:
            out[win] = None
            continue
        out[win] = _rmse6(dd, m, q1s, q2s, dq1s, dq2s, t1s, t2s)
    return out


def score_modea(d, seg):
    """ModeA mshoot (0.4s 창, 측정상태 리셋) — 앉기 개시~이륙. 창별 6채널을 창 평균으로."""
    t = d["t"]
    t0, t1 = seg["t_desc"], seg["t_lo"]
    rows = {"score": [], "desc": [], "push": []}
    w0 = t0
    while w0 + 0.05 < t1:
        wl = min(MSHOOT_W, t1 - w0)
        m = (t >= w0) & (t <= w0 + wl)
        if m.sum() < 20:
            w0 += MSHOOT_S
            continue
        i0 = int(np.argmax(m))
        st = st_from_meas(tw0, float(d["q1"][i0]), float(d["q2"][i0]),
                          float(d["dq1"][i0]), float(d["dq2"][i0]),
                          float(d["raw1"][i0]), float(d["raw2"][i0]))
        tg = t[m] - w0
        L = TW.rollout_ol(tw0, tg, d["raw1"][m], d["raw2"][m], st,
                          t_end=float(tg[-1] - 0.004), t_after=0.004)
        if L is None:
            w0 += MSHOOT_S
            continue
        gi = lambda k: np.interp(tg, L["t"], L[k])
        q1s, q2s, dq1s, dq2s, t1s, t2s = (gi(k) for k in ("q1", "q2", "dq1", "dq2", "sh1", "sh2"))
        mm = (tg >= 0.02)
        dd = {k: d[k][m] for k in ("q1", "q2", "dq1", "dq2", "a1", "a2")}
        r = _rmse6(dd, mm, q1s, q2s, dq1s, dq2s, t1s, t2s)
        rows["score"].append(r)
        mid = w0 + wl / 2
        sub = "push" if mid >= seg["t_push"] else ("desc" if mid < t[seg["i_bot"]] else None)
        if sub:
            rows[sub].append(r)
        w0 += MSHOOT_S
    return {k: (list(np.mean(v, axis=0)) if v else None) for k, v in rows.items()}


def floor_of(d, seg):
    """정지 창 측정 std = 채널별 노이즈 바닥. 창별(hold0, prehold) 따로 계산 후 평균
    (자세가 다른 두 창을 합치면 자세 차가 노이즈로 오염되므로 분리 필수)."""
    outs = []
    for key in ("hold0", "prehold"):
        m = seg[key]
        if m.sum() < 50:
            continue
        dt = lambda x: x - np.mean(x)
        outs.append((float(np.degrees(np.std(dt(d["q1"][m])))), float(np.degrees(np.std(dt(d["q2"][m])))),
                     float(np.std(d["dq1"][m])), float(np.std(d["dq2"][m])),
                     float(np.std(dt(d["a1"][m]))), float(np.std(dt(d["a2"][m])))))
    return tuple(np.mean(outs, axis=0)) if outs else None


LAB = ("q1", "q2", "dq1", "dq2", "t1", "t2")


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "baseline"
    reg = FD.registry()
    if mode == "floor":
        rows = []
        for s, p, g, cvt, ho in reg:
            d = FD.load2(p); seg = FD.segment(d)
            f = floor_of(d, seg)
            if f:
                rows.append(f)
        a = np.array(rows)
        print("채널별 노이즈 바닥 (정지 창 std, 전 trial 평균/최대):")
        for i, l in enumerate(LAB):
            print(f"  {l}: 평균 {a[:, i].mean():.4f} / 최대 {a[:, i].max():.4f}")
        return
    # baseline
    OUT = {}
    for s, p, g, cvt, ho in reg:
        if cvt:
            continue                     # 0429 — Day2 러너 후
        try:
            d = FD.load2(p); seg = FD.segment(d)
        except Exception as ex:
            print(f"{s}/{p.name}: 로드/분할 FAIL {ex}", flush=True)
            continue
        d["_sess"] = s
        ent = {"gains": g, "ho": ho}
        ent["modea"] = score_modea(d, seg)
        if (not ho) and g:
            for mk in ("OLD", "C"):
                try:
                    ent[f"cl_{mk}"] = score_cl(d, seg, mk, g)
                except Exception as ex:
                    ent[f"cl_{mk}"] = None
                    print(f"{s}/{p.name} CL {mk}: ERR {type(ex).__name__}", flush=True)
        OUT.setdefault(s, {})[p.name] = ent
        ma = ent["modea"]["score"]
        cs = ent.get("cl_C", {}) or {}
        cw = (cs or {}).get("score")
        print(f"{s}/{p.name}: ModeA q1 {ma[0]:.2f}° q2 {ma[1]:.2f}°" +
              (f" | CL(C) q1 {cw[0]:.2f} τ1 {cw[4]:.2f}" if cw else " | CL 생략/실패"), flush=True)
    jp = HERE / "_fs_baseline.json"
    json.dump(OUT, open(jp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    # 세션 요약표
    print("\n=== 세션 요약 (score 창 평균: OLD → C / ModeA) ===")
    for s, trials in OUT.items():
        for tag in ("cl_OLD", "cl_C", "modea"):
            rows = [tr[tag]["score"] for tr in trials.values() if tr.get(tag) and tr[tag].get("score")]
            if rows:
                a = np.mean(rows, axis=0)
                print(f"{s} {tag}: " + " ".join(f"{l} {v:.2f}" for l, v in zip(LAB, a)))
    print("done →", jp)


if __name__ == "__main__":
    main()
