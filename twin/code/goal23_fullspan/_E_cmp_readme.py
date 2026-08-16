# -*- coding: utf-8 -*-
"""_E_cmp_readme — 비교 폴더 README 보강 (자동 생성 표 + 구조·커버리지·규약·레시피 머리말).
fs_compare_plot 재실행 시 자동 README가 덮어쓰므로 그 뒤에 이어서 호출한다.
CLI: python _E_cmp_readme.py <폴더> <스택태그>
"""
import sys
from pathlib import Path
HERE = Path(__file__).parent
OUT = HERE / (sys.argv[1] if len(sys.argv) > 1 else "_compare_fs16")
TAG = sys.argv[2] if len(sys.argv) > 2 else "fs16"
auto = (OUT / "README.md").read_text(encoding="utf-8")
if auto.lstrip().startswith("# " + TAG) or "## 1. 무엇을 비교하는가" in auto:
    print("이미 보강됨 — skip"); sys.exit(0)
key = "|---|---|---|---|---|---|---|---|\n"
table = auto.split(key, 1)[1].rstrip() if key in auto else ""
RECIPE = {"fs16": ("FS_PRESLIDE=0.86,0.85          # 마라톤E 신규 (발 Karnopp stick-slip 이력 마찰)",
                   "fs15와의 차이는 마지막 한 줄뿐."),
          "fs15": ("# (FS_PRESLIDE 없음 — 발 마찰 μ=1.0 규제화 쿨롱)",
                   "마라톤 D까지의 스택 = fs16의 직전 기준선.")}
extra, note = RECIPE.get(TAG, ("", ""))
head = f"""# {TAG} vs 배포모델(OLD α) 3자 비교 그래프 — 전 데이터 색인

스크립트 `fs_compare_plot.py` + `fs_compare_cvt.py` (정본, `FS_CMP_OUT`/`FS_STACK_TAG`로 스택별 분리)

## 1. 무엇을 비교하는가
각 그림은 **6패널(q1 · q2 · dq1 · dq2 · τ1 · τ2)** 이고, 한 패널에 세 선이 겹칩니다.

| 선 | 뜻 |
|---|---|
| 실측 | 로봇 로그 (hip/knee xlsx, 모터측 인코더 · 축토크 환산) |
| 배포모델 OLD α | **현행 CURRENT_STACK(p24) + α 커맨드층** = 배포된 트윈 |
| 현행 {TAG} | 이 폴더의 스택 (아래 레시피) |
| 명령(qd) | 실제로 로봇에 나간 목표값 — 참고선 (계획선은 기본 미표시) |

## 2. 폴더 구조
```
{OUT.name}/
├─ CL/<세션>/<trial>.png        폐루프 (PD가 오차를 흡수하는 실제 운용 조건)
│  └─ _summary.png              그 세션 채널별 평균 RMSE 막대 (OLD vs {TAG})
├─ ModeA/<세션>/<trial>.png     측정 토크 주입 개루프 재생 (플랜트 순수 검증)
│  └─ _summary.png
├─ CVT_CL/<trial>.png           26.04.29 CVT 세션 (l_i=25.08mm, 모델 경로 상이)
├─ CVT_ModeA/<trial>.png
└─ README.md                    이 파일
```

## 3. 커버리지 (등록 56 trial 전부)
| 세션 | 구분 | trial | CL | ModeA |
|---|---|---|---|---|
| 26.03.24 | **held-out** (fit 미포함) | 3 | — (게인 미기록) | 3 |
| 26.04.21 | fit (위치제어, dq_des=0) | 6 | 6 | 6 |
| 26.04.24 | fit | 9 | 9 | 9 |
| 26.04.29 | fit (CVT l_i=25.08mm) | 10 | 10 | 10 |
| 26.06.02 | fit | 6 | 6 | 6 |
| 26.07.22 | fit | 5 | 5 | 5 |
| 26.07.23 | fit (**슬립날**) | 3 | 3 | 3 |
| 26.07.24 | fit (**슬립날**) | 3 | 3 | 3 |
| 26.07.25 | fit | 4 | 4 | 4 |
| 26.07.27 | fit (**배포 검증날**) | 7 | 7 | 7 |
| **합계** | | **56** | 53 | 56 |
총 PNG 126장 (trial 109 + 세션 _summary 17).

## 4. 그리기 규약 (perf_plot_guard 6규칙)
1. **창**: 원본 hip/knee/GRF.xlsx 스팬(점프 ~0.2~0.3s) — `fs_data.plot_window`
2. **통짜**: 창 중간 리셋 금지 (ModeA도 단일 샷)
3. **앵커**: 창 시작 실측 1회 초기화, thm1(모터측)을 실측 q1에
4. **α**: OLD는 게인 의존 보간 (상수 fallback 금지)
5. **형식**: 6패널 · 색 리터럴 금지(기본 사이클)
6. **계획선**: 기본 미표시 (진단은 FS_PLAN=1)

## 5. 스택 레시피 ({TAG})
```
FS_FIXED=1 FS_FADE=1 FS_TAUOBS=lpf FS_TC=0.002 FS_KNEE_REL=0.1 FS_KNEE_LOAD=1
FS_TAULIM=20.5 FS_VDES0=26.04.21 FS_QDSHIFT=2 FS_TKOVR=1.0 FS_KDSC=1.0
{extra}
```
{note}

## 6. 세션·모드별 상세 (OLD → {TAG}, trial 평균)
| 모드 | 세션 | trial | q1 | q2 | dq1 | dq2 | τ1 | τ2 |
|---|---|---|---|---|---|---|---|---|
"""
(OUT / "README.md").write_text(head + table + "\n", encoding="utf-8")
print(f"README 보강 완료 → {OUT.name}")
