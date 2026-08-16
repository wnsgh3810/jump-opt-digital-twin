"""실험 데이터 폴더의 위치를 정하는 **단 하나의 자리**.

왜 이 파일이 있나
-----------------
예전에는 실험 데이터 폴더의 절대 경로가 파이썬 파일 71개에 문자열로 그대로 박혀 있었다.
그래서 폴더 이름이 `4-Bar Link CVT` → `4-Bar_Link_CVT` 로 바뀌었을 때 코드가 깨졌고,
어디를 고쳐야 하는지 찾느라 시간이 들었다. 이제 위치는 여기 한 곳에서만 정한다.

폴더를 옮겼다면
---------------
둘 중 하나만 하면 된다.
  1. 환경변수 ``JUMP_CVT_ROOT`` 를 새 위치로 설정한다 (코드를 안 고쳐도 된다). 또는
  2. 아래 ``_DEFAULT_CVT_ROOT`` 한 줄을 고친다.

쓰는 법
-------
    from datapaths import DATA_ROOT, CVT_ROOT, data
    p = data("26_07_27", "250_3_250_3", "hip2.xlsx")   # 슬래시 걱정 없이 이어 붙인다

주의 1: 실험 데이터는 **읽기 전용**이다. 이 경로 아래의 xlsx/txt 원본을 수정하지 않는다.
주의 2: 이 파일 자체에는 부트스트랩(경로 찾아 올라가는 코드)을 넣지 않는다.
        여기가 원본이라 자기 자신을 import 하게 되면 무한히 돈다.
"""

import os

# 데이터가 실제로 있는 곳 (Data 폴더의 한 단계 위).
# 이 문자열이 저장소 전체에서 실험 데이터 경로가 적힌 유일한 자리다.
# 2026-08-16: Desktop/Research/4-Bar_Link_CVT 에서 여기로 옮겼다.
#   옛 자리에는 빈 폴더와 안내문(MOVED_TO_C_Users_junho_CVT.txt)만 남아 있다.
_DEFAULT_CVT_ROOT = "C:/Users/junho/CVT"

CVT_ROOT = os.environ.get("JUMP_CVT_ROOT", _DEFAULT_CVT_ROOT).replace("\\", "/").rstrip("/")
DATA_ROOT = CVT_ROOT + "/Data"

# 이 저장소 자신의 위치. 이 파일은 항상 <저장소>/code/bench/ 에 있으므로 두 단계 올라가면 된다.
# 절대경로를 적어 두지 않으므로 저장소를 어디로 옮기든 저절로 따라온다.
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))).replace("\\", "/")


def data(*parts):
    """``DATA_ROOT`` 아래의 경로를 만든다. 슬래시 중복·역슬래시를 알아서 정리한다."""
    out = DATA_ROOT
    for p in parts:
        out += "/" + str(p).replace("\\", "/").strip("/")
    return out


def cvt(*parts):
    """``CVT_ROOT`` 아래의 경로를 만든다 (Data 바깥, 예: FKnIK)."""
    out = CVT_ROOT
    for p in parts:
        out += "/" + str(p).replace("\\", "/").strip("/")
    return out


def check():
    """데이터 폴더가 실제로 있는지 확인한다. 없으면 무엇을 해야 하는지 알려 주고 멈춘다."""
    if not os.path.isdir(DATA_ROOT):
        raise FileNotFoundError(
            "실험 데이터 폴더를 찾을 수 없다: %s\n"
            "  폴더를 옮겼다면 환경변수 JUMP_CVT_ROOT 를 새 위치로 설정하거나,\n"
            "  code/bench/datapaths.py 의 _DEFAULT_CVT_ROOT 한 줄을 고쳐라." % DATA_ROOT
        )
    return DATA_ROOT


if __name__ == "__main__":
    print("CVT_ROOT  =", CVT_ROOT)
    print("DATA_ROOT =", DATA_ROOT)
    print("존재 여부  =", os.path.isdir(DATA_ROOT))
