# -*- coding: utf-8 -*-
"""build_notion_cd — 노션 차일드 ⑭(마라톤 C)·⑮(마라톤 D) 게시 (PLAYBOOK §10 템플릿).

허브: GOAL23 FULLSPAN (3acab81d-2550-8102-a9fc-f2723fe9e59f). CLI: python build_notion_cd.py
"""
import os, sys
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent / "bench"))
import notion_kit as N

HUB = "3acab81d25508102a9fcf2723fe9e59f"
PL = HERE / "_plots"


def child_c():
    pid = N.create_page(HUB, "⑭ 마라톤 C — 커맨드층 대발견 (dq_des·4ms 스큐·유령 소거)", icon="🕵️")
    B = []
    B.append(N.callout("💡", N.rt("추종 결손의 정체 3연쇄: ①0421만 dq_des=0 (실효 PD가 kp·e−kd·dq — push q2 8.42→4.05) "
                               "②'세션별 τ_lim'은 유령 (제한은 전류 포화 ~20Nm 단일 — 사용자 3연속 정답) "
                               "③push의 kp·e 25~30% 과대는 qd 채널 4ms 로깅 스큐 (δ보정 시 전 세션 계수→1.0, R²0.99).", bold=True)))
    B.append(N.h2("쉬운 설명"))
    B.append(N.para(N.rt("실기가 '명령보다 약하게 미는 것처럼' 보였던 것은 로봇 문제가 아니라 기록계의 4ms였다. "
                       "목표각(qd) 채널이 실측각(q)·토크(raw)보다 2샘플 먼저 적히는 바람에, 빠른 구간에서 목표와 실측을 "
                       "교차 계산하면 오차가 부풀어 보였다. 리밋·열·벨트 탄성 가설이 차례로 기각되고 (사용자 반증 4연타), "
                       "시계를 4ms 돌려 맞추자 모든 유령이 사라졌다.")))
    B.append(N.h2("수식/정의"))
    B.append(N.code_block("판별: raw2 ≈ a·kp2·(qd2(t−δ)−q2) + b·kd2·(dqd2(t−δ)−dq2), push 창 LSQ\n"
                          "δ=0: a 0.67~0.90 (세션별) → δ=4ms: a 1.04~1.10, R² 0.97~0.99 (전 세션)\n"
                          "0421 형태: M2 = kp·e − kd·dq (dq_des=0, 사용자 확정) — RMSE 2.15 vs M1 10.25\n"
                          "지연 주입 4연속 기각: 개루프 판독 tc의 폐루프 이식 금지 (철칙 10 실증)"))
    B.append(N.h2("그림 — 0429 CVT 3자 비교 (실측/old α/fs)"))
    k = 0
    for f, cap in ((PL / "cvt0429_modeA_150_2.2_250_3.png", "ModeA (측정 raw 주입) — 플랜트 건강 확인"),
                   (PL / "cvt0429_CL_150_2.2_250_3.png", "CL push 구간 — 커맨드 과도가 dq2 격차의 근원 (재생 특권 실증)")):
        if f.exists():
            B.append(N.img(str(f), cap)); k += 1
    B.append(N.h2("결과 표"))
    B.append(N.table([
        ["항목", "before", "after", "판정"],
        ["0421 push q2 (fs14 반영)", "8.42°", "4.05°", "dq_des=0 반영 (기록된 커맨드 구성)"],
        ["push kp·e 계수 (δ=0→4ms)", "0.67~0.90", "1.04~1.10", "스큐 확정 — 데이터 사전 등재"],
        ["τ_lim 서사", "세션별 15Nm 설정", "철회", "전류 포화 단일 ~20Nm (사용자 확인)"],
        ["CVT 0429 CL 편입", "미채점", "push q1 1.25·q2 3.43", "l_i 실측 24.99 반영"],
    ]))
    B.append(N.h2("한계/다음"))
    B.append(N.bullet(N.rt("스큐 보정의 CL 단독 주입은 공적응 파괴 (R9) — 재적합은 마라톤 D로")))
    B.append(N.bullet(N.rt("TK·kd0.2의 물리 해석(벨트)은 벨트 부재 확인으로 철회 — 스큐 흡수층으로 재해석")))
    B.append(N.callout("📁", N.rt("code/goal23_fullspan/MARATHON_C_TRACK.md · fs_track*.py · _fs_track*.json · _plots/cvt0429_*.png")))
    N.append(pid, B)
    assert N.verify_images(pid, expected=k), "이미지 검증 실패 (⑭)"
    print(f"⑭ OK ({k} imgs): {pid}")


def child_d():
    pid = N.create_page(HUB, "⑮ 마라톤 D — 배포 정합 fs15 (스큐+실게인) & 에너지 백도어", icon="🚀")
    B = []
    B.append(N.callout("💡", N.rt("fs15 = 스큐 보정 + 실게인(TK=1·kd=1) + 관측 TC 2ms: push q2 −38%·dq2 −44%·τ1 −16% "
                               "(J 0.854). sim 커맨드 법칙이 실기와 문자 동일해짐 — 배포 전이성의 근본. "
                               "잔여: τ2 +15% (실게인의 상태오차 증폭 — dq2 절감으로 일원화) · 점프높이 sim 과대 "
                               "+8~25cm = 실기 소산 ~5J 누락 (지지층 에너지 백도어로 주입 3종 전패 — 보존화 재설계 필요).", bold=True)))
    B.append(N.h2("쉬운 설명"))
    B.append(N.para(N.rt("구 스택은 무릎 게인을 0.66×/0.2×로 깎아 쓰며 '점수'를 지켰는데, 그 깎임의 정체가 4ms 스큐 보상이었다. "
                       "스큐를 고치고 진짜 게인을 넣자 움직임 정확도가 뛰었다. 대신 이제 sim은 남은 상태 오차를 실기 게인 그대로 "
                       "증폭해 τ2에 정직하게 드러낸다. 또 하나: sim이 실기보다 5~15cm 더 높이 뛴다 — 실기는 push 일의 절반(~10J)을 "
                       "잃는데 sim은 절반만 잃는다. 손실을 넣어 보면 지지법칙 층이 '체류가 길어진 만큼 더 밀어줘서' 도로 벌충한다 — "
                       "이 백도어(비보존 적층)를 보존형 스프링으로 재설계하는 것이 다음 마라톤.")))
    B.append(N.h2("수식/정의"))
    B.append(N.code_block("J_push = mean_ch( Σ_s RMSE_ch(s) / Σ_s RMSE_ch^fs14(s) ), push 창·8 fit 세션·thm1 기준\n"
                          "fs15 env: FS_FIXED FS_FADE FS_TAUOBS=lpf FS_TC=0.002 FS_KNEE_REL=0.1 FS_KNEE_LOAD=1\n"
                          "         FS_TAULIM=20.5 FS_VDES0=26.04.21 FS_QDSHIFT=2 FS_TKOVR=1.0 FS_KDSC=1.0\n"
                          "게이트: MA 전 세션 +0.05° 밴드 · HO 0324 · 배포 앵커 27일/100_1.5_250_3 6채널 비악화 (사용자 지정)\n"
                          "원장: W_push 실측 ≈ sim (~20J) · KE_이륙 실측 7.5~11.4J vs sim 13.6~17.6J → 소산 ~5J 누락"))
    B.append(N.h2("그림"))
    k = 0
    f = PL / "marathonD_summary.png"
    if f.exists():
        B.append(N.img(str(f), "좌: 6채널 before/after (J 0.854) · 우: 점프높이 sim 과대 (백도어 지표)")); k += 1
    B.append(N.h2("결과 표"))
    B.append(N.table([
        ["채널 (push 합)", "fs14", "fs15", "Δ"],
        ["q1", "13.11", "12.83", "−2%"],
        ["q2", "18.82", "11.64", "−38%"],
        ["dq1", "7.11", "6.93", "−3%"],
        ["dq2", "12.04", "6.74", "−44%"],
        ["τ1", "19.60", "16.47", "−16%"],
        ["τ2", "21.65", "24.95", "+15% (실질 — dq2 경로로 회수)"],
        ["배포 앵커 (27일 kp1=100)", "q2 1.59·dq2 1.20·τ2 2.65", "0.76·0.58·1.88", "무릎 3채널 통과"],
    ]))
    B.append(N.h2("한계/다음"))
    B.append(N.bullet(N.rt("τ2 +15%는 저주파에도 잔존 (노이즈 주장 철회 이력) — 실게인×상태오차 증폭, dq2 말기 과속이 지배항")))
    B.append(N.bullet(N.rt("손실 주입 3종(레일 쿨롱·제곱 소산·η^sign) 전패 — 지지 적층 비보존 백도어 (REJECTED #62~64)")))
    B.append(N.bullet(N.rt("ramp 재심: fs15 CL 순개선이나 MA 가드 4건 위반 — 보존화 재설계와 함께 재도전")))
    B.append(N.bullet(N.rt("CURRENT_STACK 승격 보류 (τ2 밴드 + 사용자 판단 대기) — fs15는 마라톤 작업 기준")))
    B.append(N.callout("📁", N.rt("code/goal23_fullspan/MARATHON_D_DEPLOY.md · fs_secondary.py · _D_*.json/_D_*.log · _plots/marathonD_summary.png")))
    N.append(pid, B)
    assert N.verify_images(pid, expected=k), "이미지 검증 실패 (⑮)"
    print(f"⑮ OK ({k} imgs): {pid}")


if __name__ == "__main__":
    child_c()
    child_d()
    print("done")
