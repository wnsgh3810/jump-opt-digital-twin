@echo off
REM ============================================================================
REM  마라톤G G21 — 공적합(joint) 그리드 스윕
REM  사용자 지적(08-08): "p24 에서 적용됐던 모델들도 전부 a_hat 에 과적합됐던 애들이니까
REM                       다 검토 다시 해봐야하는거 아냐? MCG 도 그렇고"
REM  → G19/G20 이 실증: 일인자별로는 도달 불가 (나머지 축이 저항). 동시 최적화가 필요.
REM
REM  고정 (G20 확정): 인공 지지층 OFF · 부하연동 무릎 스프링 OFF · 정본곡선 포화캡
REM  자유:  무릎캡 × 힙캡 × 허벅지 CoM(중력) — 27 조합
REM  현재 최고: 무릎 2.9 / 힙 2.4 / comz 0 → J_G 0.9739 (게이트 PASS)
REM  예상 소요: 약 80~90분 (조합당 ~3분)
REM ============================================================================
setlocal
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8
set P25_CLIP_RAW=35.5
set FS_TMAP=canon_cap
set FS_NOSUPP=1
set FS_NOSPR=1

echo ============================================================
echo  G21 joint sweep 시작 — 27 조합
echo  결과는 _G13_board_Q_*.json 및 화면에 기록됩니다
echo ============================================================

for %%K in (2.7 2.9 3.1) do (
  for %%H in (2.2 2.4 2.6) do (
    for %%C in (0.0 0.015 0.027) do (
      echo.
      echo ### Q_k%%K_h%%H_c%%C
      set FS_TDCAP=%%K,%%H
      if "%%C"=="0.0" ( set "FS_COMZ=" ) else ( set "FS_COMZ=thigh=%%C" )
      call :run %%K %%H %%C
    )
  )
)
echo.
echo ============================================================
echo  완료. 아래 명령으로 요약표를 뽑으세요:
echo    python _G21_summary.py
echo ============================================================
pause
exit /b

:run
setlocal enabledelayedexpansion
set FS_TDCAP=%1,%2
if "%3"=="0.0" ( set "FS_COMZ=" ) else ( set "FS_COMZ=thigh=%3" )
python _G13_board.py Q_k%1_h%2_c%3 2>&1 | findstr /C:"J_G" /C:"게이트"
endlocal
exit /b
