# -*- coding: utf-8 -*-
"""t0wc_nlp_diag — NLP-CMA h 격차 정량 진단 (t0wc_nlp 부속, audit 'diagnosis' 필드 추가).

가설: NLP 대리 플랜트의 선형 스프링-댐퍼 접촉(k_c=1.3e5, b_c=180 — G20 레시피,
완만한 레짐에서 캘리브레이션)이 CMA의 충격형 단스탠스(0.04~0.10s) 푸시에서 트윈
MuJoCo 접촉(solimp 임피던스)과 괴리 → 댐퍼 에너지 세금/힘 불일치로 짧은 스탠스
전략을 저평가.

방법: CMA liopt 해의 트윈 â 재생 궤적(상태 시계열)을 그대로 두고, 그 궤적 위에서
NLP 접촉법칙이 내는 수직력 fz_model(t)을 계산해 트윈 실측 GRF와 비교 + 댐퍼 소산
에너지 E_damp = ∫ b_c·δ̇²·w dt 적분. 대조군 = NLP 자기 해 (t0wc_nlp.npz) 동일 계산.

실행: PYTHONIOENCODING=utf-8 python t0wc_nlp_diag.py   (t0wc_nlp 완주 후)
"""
import numpy as np

import t0wc_nlp as T
import safe

HERE = T.HERE


def contact_along(li, t, q1, q2, bz, grf_ref, label):
    """측정 프레임 궤적 → NLP 접촉법칙 fz_model + 댐퍼 소산 (스탠스 창)."""
    f = T.fit_li(li)
    npf = T.NpF([f] * 5, li)
    j1 = -np.asarray(q1) - np.pi / 2
    j2 = -np.asarray(q2)
    fk = npf.fk(j1, j2, li)                     # (n, 3)
    foot_z = np.asarray(bz) + fk[:, 1]
    delta = f["R"] - foot_z
    ddelta = -np.gradient(foot_z, t)
    eps = T.B.EPS_C
    dpos = 0.5 * (delta + np.sqrt(delta * delta + eps * eps))
    w = dpos / (dpos + eps)
    fz_m = T.B.K_C * dpos + T.B.B_C * ddelta * w
    # 접촉 창: t ∈ (0, 0.5) 전체 접촉 샘플 (grf>1 ∪ 모델 침투>0.1mm) — 임펄스형 해는
    # 언로드-재푸시로 다중 세그먼트라 첫 dip이 진짜 이지가 아님 (v1 창 함정 수정)
    tt = np.asarray(t)
    gr_all = np.asarray(grf_ref)
    m = (tt > 0) & (tt < 0.5) & ((gr_all > 1.0) | (dpos > 1e-4))
    if not m.any():
        return None
    dt = float(np.median(np.diff(tt)))
    P_damp = T.B.B_C * ddelta ** 2 * w
    E_damp = float(np.sum(P_damp[m]) * dt)
    imp_twin = float(np.sum(gr_all[m]) * dt)
    imp_model = float(np.sum(fz_m[m]) * dt)
    t_lift_true = float(tt[m][-1])
    out = dict(
        label=label, l_i_mm=li * 1000,
        contact_samples_s=float(m.sum() * dt), t_last_contact_s=t_lift_true,
        grf_twin_peak_N=float(gr_all[m].max()), fz_model_peak_N=float(fz_m[m].max()),
        fz_rms_mismatch_N=float(np.sqrt(np.mean((fz_m[m] - gr_all[m]) ** 2))),
        fz_model_min_N=float(fz_m[m].min()),
        impulse_twin_Ns=imp_twin, impulse_model_Ns=imp_model,
        damper_dissipation_J=E_damp,
        jump_energy_scale_J=float(f["Mtot"] * T.B.GG * 0.9),
        note="fz_model = NLP 선형 k_c·δ⁺+b_c·δ̇·w 를 트윈 재생 궤적 위에서 평가; "
             "창 = 전 접촉 샘플 (다중 세그먼트 포함)")
    print(f"[{label}] contact {out['contact_samples_s']:.3f}s (last {t_lift_true:.3f})  "
          f"GRF twin peak {out['grf_twin_peak_N']:.0f} N vs model "
          f"{out['fz_model_peak_N']:.0f} N  rms {out['fz_rms_mismatch_N']:.0f} N  "
          f"impulse {imp_twin:.2f} vs {imp_model:.2f} N*s  "
          f"E_damp {out['damper_dissipation_J']:.2f} J", flush=True)
    return out


def main():
    safe.utf8_console()
    T.W.setup()
    rows = []
    # ① CMA liopt 해 (충격형, 이지 0.044s) — 트윈 â 재생 궤적
    z = np.load(HERE / "t0wc_cl_liopt.npz")
    aj = safe.read_json(HERE / "t0wc_cl_liopt_audit.json")
    li = float(z["l_i"]) / 1000.0
    q0 = (float(aj["params"]["knots_qd1"][0]), float(aj["params"]["knots_qd2"][0]))
    t = np.asarray(z["t"], float)
    m = (t >= -1e-12) & (t <= T.W.T_END + 1e-12)
    L = T.rollout_ahat(li, t[m], np.asarray(z["tau1_nm"])[m],
                       np.asarray(z["tau2_nm"])[m], q0)
    assert L is not None
    h_rep = float(L["bz"][L["t"] > 0].max())
    print(f"[재생] CMA liopt â → twin h={h_rep:.4f} (기록 {float(z['h_plan']):.4f})",
          flush=True)
    rows.append(contact_along(li, L["t"], L["q1"], L["q2"], L["bz"], L["grf"],
                              "cma_liopt_replay(impulsive)"))
    # ② NLP 자기 해 (완만형) — 자기 트윈 재생 궤적
    zn = np.load(T.OUT_NPZ)
    li_n = float(zn["l_i"]) / 1000.0
    rows.append(contact_along(li_n, np.asarray(zn["t_twin"], float),
                              zn["q_twin"][:, 0], zn["q_twin"][:, 1],
                              np.asarray(zn["bz_twin"], float),
                              np.asarray(zn["grf_twin"], float),
                              "nlp_solution_replay(gentle)"))
    diag = dict(
        hypothesis="선형 k_c/b_c 접촉(G20, 완만 레짐 캘리브레이션)이 충격형 단스탠스에서 "
                   "트윈 solimp 접촉과 괴리 — NLP가 CMA식 전략을 저평가 (홉 사다리에서 "
                   "t_f 짧아질수록 h 하락과 정합)",
        replay_golden=dict(cma_liopt_ahat_replay_h=h_rep,
                           cma_liopt_recorded_h=float(z["h_plan"])),
        contact_eval=rows)
    d = safe.read_json(T.OUT_JSON)
    d["diagnosis"] = diag
    safe.atomic_json_write(T.OUT_JSON, d)
    print("audit 'diagnosis' 필드 추가 완료", flush=True)


if __name__ == "__main__":
    main()
