# -*- coding: utf-8 -*-
"""exp5_energy — 26.07.27 v9 7게인의 슬립·높이·일·파워 종합 분석.

측정 신호만 사용 (계획 정렬 불필요):
  · â = ahat(A_PAPER, raw, sgn(dq))
  · 일: W_abs=∫|τ·dq|dt (Real Data '절대 기계적 에너지'와 동일 정의), W_net=∫τ·dq (순 전달 에너지)
  · 파워: 평균 P=W_abs/t_stance, 순간피크 P_peak=max|τ·dq|
  · 슬립: 인코더 FK foot_x. net=끝점, absmax=최대편위, recovered=absmax−|net| (복귀량)
  · 스탠스 = [명령 onset, GRF 지속-이륙)
산출: _exp5_energy.json + graphs/exp5/exp5_energy.png (+ 상관 스캐터)
"""
# --- 실험 데이터 경로: 단일 출처 (code/bench/datapaths.py) ---
import os as _o, sys as _s
_d = _o.path.dirname(_o.path.abspath(__file__))
while _d != _o.path.dirname(_d) and not _o.path.isdir(_o.path.join(_d, 'code', 'bench')):
    _d = _o.path.dirname(_d)
if _o.path.join(_d, 'code', 'bench') not in _s.path:
    _s.path.append(_o.path.join(_d, 'code', 'bench'))
from datapaths import DATA_ROOT, CVT_ROOT  # noqa: E402
# ---------------------------------------------------------------
import os, json
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
from pathlib import Path
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
plt.rcParams["font.family"] = "Malgun Gothic"; plt.rcParams["axes.unicode_minus"] = False

HERE = Path(__file__).parent
DATA = Path((DATA_ROOT + "/26_07_27"))
OUT = HERE / "graphs" / "exp5"; OUT.mkdir(parents=True, exist_ok=True)
KT, GR, CF = 0.091, 9.0, 0.59
A = np.array([1.15605006, 4.17389589e-4, 0.26855607, 0.04904241])
L_SEG = 0.25
def ahat(raw, v):
    Iq = (CF/(GR*KT))*np.asarray(raw, float); s = np.sign(v)
    return A[0]*GR*KT*Iq - A[1]*GR*np.abs(Iq)*Iq - A[2]*s - A[3]*np.abs(Iq)*s
def realh(p):
    import re; m = re.search(r"실제 점프 높이\s*:\s*([\d.]+)m", Path(p).read_text(encoding="utf-8", errors="ignore"))
    return float(m.group(1)) if m else np.nan

GAINS = sorted([p.name for p in DATA.iterdir() if p.is_dir() and (p/"hip.xlsx").exists()],
               key=lambda s: float(s.split("_")[0]))
HIPKP = [float(g.split("_")[0]) for g in GAINS]
R = {}
for lab in GAINS:
    hip = pd.read_excel(DATA/lab/"hip.xlsx"); knee = pd.read_excel(DATA/lab/"knee.xlsx")
    grf = pd.read_excel(DATA/lab/"GRF.xlsx")
    n = min(len(hip), len(knee), len(grf)); hip, knee, grf = hip.iloc[:n], knee.iloc[:n], grf.iloc[:n]
    t = hip["Time"].to_numpy(float) - hip["Time"].iloc[0]
    q1, q2 = hip["currentAngle"].to_numpy(float), knee["currentAngle"].to_numpy(float)  # rad
    v1, v2 = hip["currentAngleVelocity"].to_numpy(float), knee["currentAngleVelocity"].to_numpy(float)  # rad/s
    a1 = ahat(hip["currentTorque"].to_numpy(float), v1)
    a2 = ahat(knee["currentTorque"].to_numpy(float), v2)
    # 스탠스 창: 명령 onset ~ GRF 지속-이륙
    qd2 = knee["desiredAngle"].to_numpy(float); on = np.where(np.abs(qd2-qd2[0]) > np.radians(0.5))[0]
    t0 = t[on[0]] if len(on) else 0.0
    g = grf["Current_GRF"].to_numpy(float); g0 = np.median(g[-5:]); thr = g0 + 0.06*(np.nanmax(g)-g0)
    ab = np.where(g >= thr)[0]; t_lo = t[min(int(ab[-1])+1, len(t)-1)] if len(ab) else t[-1]
    m = (t >= t0) & (t <= t_lo); ts = t[m]; dt_stance = float(ts[-1]-ts[0])
    # 일 (절대/순), 파워 (평균/순간피크)
    ph, pk = a1[m]*v1[m], a2[m]*v2[m]                       # 순간 파워 [W]
    Wh_abs, Wk_abs = float(np.trapezoid(np.abs(ph), ts)), float(np.trapezoid(np.abs(pk), ts))
    Wh_net, Wk_net = float(np.trapezoid(ph, ts)), float(np.trapezoid(pk, ts))
    Ph_avg, Pk_avg = Wh_abs/dt_stance, Wk_abs/dt_stance
    Ph_pk, Pk_pk = float(np.abs(ph).max()), float(np.abs(pk).max())
    # 슬립 (FK)
    fx = L_SEG*(np.cos(q1)+np.cos(q1+q2)); sl = fx[m]-fx[m][0]
    net = float(sl[-1])*1e3; amx = float(sl[np.argmax(np.abs(sl))])*1e3
    recov = abs(amx)-abs(net)
    R[lab] = dict(hipkp=float(lab.split("_")[0]), h=realh(DATA/lab/"Real Data.txt"),
                  t_stance=round(dt_stance,4), Wh_abs=round(Wh_abs,2), Wk_abs=round(Wk_abs,2),
                  Wtot=round(Wh_abs+Wk_abs,2), Wh_net=round(Wh_net,2), Wk_net=round(Wk_net,2),
                  Ph_avg=round(Ph_avg,1), Pk_avg=round(Pk_avg,1), Ph_pk=round(Ph_pk,1), Pk_pk=round(Pk_pk,1),
                  ratio_kh=round(Wk_abs/max(Wh_abs,1e-6),2), slip_net=round(net,1),
                  slip_absmax=round(amx,1), slip_recov=round(recov,1))
    print(f"{lab.split('_')[0]:>4}: h={R[lab]['h']:.2f} W(h/k/tot)={Wh_abs:.1f}/{Wk_abs:.1f}/{Wh_abs+Wk_abs:.1f}J "
          f"P_avg(h/k)={Ph_avg:.0f}/{Pk_avg:.0f}W P_peak(h/k)={Ph_pk:.0f}/{Pk_pk:.0f}W "
          f"k/h={R[lab]['ratio_kh']:.2f} slip net/max/복귀={net:.0f}/{amx:.0f}/{recov:.0f}mm", flush=True)

json.dump(R, open(HERE/"_exp5_energy.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

def col(k): return [R[g][k] for g in GAINS]
def rr(a, b):
    a, b = np.array(a), np.array(b); return float(np.corrcoef(a, b)[0, 1])

fig, ax = plt.subplots(2, 3, figsize=(19, 10))
kp = HIPKP
# ① 높이
ax[0,0].plot(kp, col("h"), "o-"); ax[0,0].axhline(0.878, ls=":", color="gray")
ax[0,0].text(kp[0], 0.879, "계획 0.878", fontsize=8, color="gray")
ax[0,0].set_title("① 점프 높이 [m] — U자 (양끝 높고 중간 낮음)")
# ② 일 per joint
ax[0,1].plot(kp, col("Wh_abs"), "o-", label="hip")
ax[0,1].plot(kp, col("Wk_abs"), "s-", label="knee")
ax[0,1].plot(kp, col("Wtot"), "^--", label="합계")
ax[0,1].set_title("② 일 ∫|τ·dq| [J] — hip 램프↑ / knee 저게인서 보상↑"); ax[0,1].legend(fontsize=8)
# ③ 파워
ax[0,2].plot(kp, col("Ph_avg"), "o-", label="hip 평균")
ax[0,2].plot(kp, col("Pk_avg"), "s-", label="knee 평균")
ax[0,2].plot(kp, col("Pk_pk"), "^--", label="knee 순간피크")
ax[0,2].plot(kp, col("Ph_pk"), "v--", label="hip 순간피크")
ax[0,2].set_title("③ 파워 [W] — knee가 파워 관절 (피크 2배+)"); ax[0,2].legend(fontsize=8)
# ④ 슬립
ax[1,0].plot(kp, [abs(x) for x in col("slip_net")], "o-", label="순(끝점)")
ax[1,0].plot(kp, [abs(x) for x in col("slip_absmax")], "s-", label="최대편위")
ax[1,0].plot(kp, col("slip_recov"), "^--", label="복귀량(가역)")
ax[1,0].set_title("④ 슬립 [mm] — 저게인=가역(복귀), 고게인=영구"); ax[1,0].legend(fontsize=8)
# ⑤ 슬립 vs hip 일 (슬립세 가설)
ax[1,1].scatter(col("Wh_abs"), [abs(x) for x in col("slip_net")])
for g in GAINS: ax[1,1].annotate(g.split("_")[0], (R[g]["Wh_abs"], abs(R[g]["slip_net"])), fontsize=8)
ax[1,1].set_title(f"⑤ 순슬립 vs hip 일 (r={rr(col('Wh_abs'),[abs(x) for x in col('slip_net')]):.2f}) — hip 일=슬립세")
ax[1,1].set_xlabel("hip 일 [J]"); ax[1,1].set_ylabel("|순슬립| [mm]")
# ⑥ 높이 vs 총일 / knee일 (엔진)
ax[1,2].scatter(col("Wtot"), col("h"), label="총일")
for g in GAINS: ax[1,2].annotate(g.split("_")[0], (R[g]["Wtot"], R[g]["h"]), fontsize=8)
ax[1,2].set_title(f"⑥ 높이 vs 총일 (r={rr(col('Wtot'),col('h')):.2f}) / knee일-높이 r={rr(col('Wk_abs'),col('h')):.2f}")
ax[1,2].set_xlabel("총 일 [J]"); ax[1,2].set_ylabel("점프 높이 [m]")
for a_ in ax.flat:
    a_.grid(alpha=.3)
    if a_ not in (ax[1,1], ax[1,2]): a_.set_xlabel("hip kp (knee 250/3 고정)"); a_.set_xticks(kp)
fig.suptitle("exp5 (26.07.27, v9 7게인) — 슬립·높이·일·파워 종합", fontsize=14)
fig.tight_layout(); fig.savefig(OUT/"exp5_energy.png", dpi=115); plt.close(fig)
print("상관: 순슬립~hip일 r=%.2f | 높이~총일 r=%.2f | 높이~knee일 r=%.2f | 높이~hip일 r=%.2f" % (
    rr(col("Wh_abs"), [abs(x) for x in col("slip_net")]), rr(col("Wtot"), col("h")),
    rr(col("Wk_abs"), col("h")), rr(col("Wh_abs"), col("h"))))
print("done →", OUT/"exp5_energy.png")
