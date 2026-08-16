# -*- coding: utf-8 -*-
"""P22 노션 4탄 — P22-6 최종 후보 p22b: 성적표·오버레이·남은 것."""
# --- 옛 결과 폴더 위치: 단일 출처 (code/bench/datapaths.py) ---
import os as _o3, sys as _s3
_d3 = _o3.path.dirname(_o3.path.abspath(__file__))
while _d3 != _o3.path.dirname(_d3) and not _o3.path.isdir(_o3.path.join(_d3, 'code', 'bench')):
    _d3 = _o3.path.dirname(_d3)
if _o3.path.join(_d3, 'code', 'bench') not in _s3.path:
    _s3.path.append(_o3.path.join(_d3, 'code', 'bench'))
from datapaths import LEGACY_ROOT  # noqa: E402
# ---------------------------------------------------------------
import sys
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent.parent / "bench"))
import notion_kit as N

ROOT = "39eab81d-2550-812c-9336-c48ab4af0dec"
FIG = Path((LEGACY_ROOT + "/g22_p22_results"))


def loc(txt):
    return N.callout("📁", N.rt("산출물 위치: ", bold=True), N.rt(txt, code=True))


def main():
    p = N.create_page(ROOT, "P22-6 최종 후보 p22b — 관성 동결 + 소산 재배치 (승격 판단 자료)", icon="🎯")
    N.append(p, [
        N.callout("💡", N.rt("3줄 요약: ", bold=True),
                  N.rt("마지막 세그먼트(널 나사 동결 + CLdq 제약 정렬)에서 20개 개체가 전원 엄격 게이트를 "
                       "통과했고, 그중 종합점수 최고인 p22b를 등록했다. 정체는 '소산의 재배치' — hip 점성을 "
                       "줄이고 knee 점성·쿨롱과 부드러운 접촉으로 옮긴 것으로, 에너지 원장의 판정(과잉이 "
                       "아니라 오배분)이 파라미터에 그대로 구현됐다. 관성 나사들은 P19 값에 동결돼 있어 "
                       "물리적 신뢰성이 보존된다.")),
        N.h2("① p22b 성적표 (전부 P19 대비, 심판 정합·REPRODUCED)"),
        N.table([
            ["지표", "P19", "p22b", "판정"],
            ["폐루프 τ-갭 FIT", "38.1%", "37.0%", "개선 (전 세션: 0421 33.4 / 0424 33.6 / 0602 34.2 / 0429 43.9)"],
            ["held-out 폐루프 (0324)", "35.7%", "34.5%", "−1.2%p 개선 (fit 미포함 세션)"],
            ["재생 dq — 0424", "1.89", "1.72", "−9.2%"],
            ["재생 dq — 0602", "1.26", "1.18", "−6.4%"],
            ["재생 dq — 0421", "1.48", "1.37", "−7.5%"],
            ["재생 dq — 0429", "3.31", "3.45", "+4.3% (정직: 소폭 후퇴)"],
            ["점프높이 오차 평균", "4.8%", "3.8%", "개선"],
            ["종합 J_v5", "1.000", "0.949", "−5.1%"],
        ]),
        N.img(str(FIG / "overlay_p19_p22b.png"),
              "고게인 대표 4 trial의 통짜 재생 오버레이: 0424/0602에서 p22b(점선)가 실측 피크를 P19(파선)보다 잘 추적. 0429는 둘 다 과속(공통 미해결 — CVT 손실 부재), 0421은 둘 다 과소속(공통 미해결 — 동적 부족분)."),
        N.h2("② 무엇이 바뀌었나 — 소산의 재배치"),
        N.table([
            ["나사", "P19 → p22b", "의미"],
            ["hip 점성 감쇠", "0.69 → 0.46 (−34%)", "민감도 지도의 스타 무브 — τ·창·높이 동반 개선의 원천"],
            ["knee 점성/쿨롱", "+37% / 0.001→0.021", "hip에서 뺀 소산을 무릎으로 — 오배분 교정"],
            ["접촉 시정수 solref", "+35% (부드럽게)", "착지·이륙 전이 개선"],
            ["프리로드 pre30", "2.25 → 1.95 (−13%)", "담요 축소 (어시스트 6%가 일부 대체)"],
            ["관성 4종 (M_c·I_th·I_ca·dz_ca)", "동결 (P19 값)", "널스페이스 차단 — 물리성 보존"],
        ]),
        N.h2("③ 정직: 남은 것"),
        N.bullet(N.rt("0429 재생 +4.3% 후퇴 — CVT 실손실(원장이 증명)이 모델에 없어서 P19도 p22b도 "
                      "과속하며, p22b가 약간 더 과속. 단독 주입은 실패했으므로(P22-4) 이 축은 벤치 "
                      "실측(4-bar 입출력 토크) 후 공동적합으로만 풀린다.")),
        N.bullet(N.rt("held-out 개루프 재생 2.93→3.9 (+31%): 감쇠 삭감 방향의 숨은 비용 (동결로도 잔존 "
                      "— 널 착시가 아님). 같은 세션의 폐루프는 개선(34.5%)이라 개루프/폐루프가 갈렸다. "
                      "이 수치는 진단 전용(held-out 유출 방지)이며, 승격 판단자가 알아야 할 정보라 명기.")),
        N.bullet(N.rt("0421 동적 과소속도(실측 22 vs 재생 13.5)는 P19와 p22b가 사실상 동일 — 이 마라톤이 "
                      "건드리지 못한 공통 미해결 (P20의 '상승 성분' 문제 그대로).")),
        N.h2("④ 승격 판단 (사용자)"),
        N.para(N.rt("선택지: (a) p22b 승격 — 지표 v5 전승 + held-out 폐루프 개선 + 관성 물리성 보존, "
                    "비용은 0429 재생 +4.3%와 held-out 개루프 진단 열화 (b) P19 유지 — 재생 그래프의 "
                    "보수성 우선. 판단 자료: g22_p22b_all_results의 79 그래프/GIF를 g22_p19_all_results와 "
                    "나란히 보면 된다. 승격 시: bench promote (게이트 자동 검증) → CURRENT_STACK 갱신.")),
        loc("후보 fourbar_p22b_candidate.json (judge p22, REPRODUCED) · 그래프 "
            "CVT/jump_opt/g22_p22b_all_results/ · 비교 그림 g22_p22_results/overlay_p19_p22b.png"),
    ])
    ok = N.verify_images(p)
    print("P22-6", p, "images:", ok)


if __name__ == "__main__":
    main()
