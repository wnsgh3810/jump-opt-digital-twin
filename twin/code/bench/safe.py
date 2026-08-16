# -*- coding: utf-8 -*-
"""safe.py — 반복 footgun 방역 유틸 (연구 헌법 §철칙: 이 유틸 사용 의무).

발생 이력 기반:
  - xml_patch   : XML 문자열 치환 침묵 실패 (P18b iter5, "calf 승리"가 실제론 스프링 제거)
  - qadr/dofadr : qpos 인덱스 하드코딩 → 트리 변경 시 침묵 오염 (P20 SEA, rotor=idx4 사건.
                  평행사변형 축퇴가 버그를 위장했음)
  - atomic_json : 다중 워커 JSON write 레이스 (p10_pdlaw.json, CMA-6 크래시)
  - candidate_save : 후보 JSON 덮어쓰기 방지 (갱신은 bench promote로만)
  - utf8_console: cp949 콘솔에서 한글/유니코드(—, ≈ 등) 크래시
"""
import json
import os
import sys
import tempfile


def utf8_console():
    """cp949 콘솔 크래시 방지. 모든 스크립트 첫 줄에서 호출."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except Exception:
            pass


def xml_patch(xml, old, new, count=1):
    """검증된 XML 치환 — old가 정확히 count회 존재하지 않으면 raise.

    str.replace의 침묵 no-op을 구조적으로 차단한다.
    """
    n = xml.count(old)
    if n != count:
        raise ValueError(
            f"xml_patch: 패턴이 {n}회 발견됨 (기대 {count}회). "
            f"침묵 실패 방지를 위해 중단. 패턴: {old[:120]!r}")
    return xml.replace(old, new)


def qadr(model, joint_name, mj=None):
    """관절 이름 → qpos 인덱스 (하드코딩 금지)."""
    if mj is None:
        import mujoco as mj
    jid = mj.mj_name2id(model, mj.mjtObj.mjOBJ_JOINT, joint_name)
    if jid < 0:
        raise KeyError(f"qadr: joint {joint_name!r} 없음")
    return int(model.jnt_qposadr[jid])


def dofadr(model, joint_name, mj=None):
    """관절 이름 → qvel/dof 인덱스."""
    if mj is None:
        import mujoco as mj
    jid = mj.mj_name2id(model, mj.mjtObj.mjOBJ_JOINT, joint_name)
    if jid < 0:
        raise KeyError(f"dofadr: joint {joint_name!r} 없음")
    return int(model.jnt_dofadr[jid])


def atomic_json_write(path, obj, indent=1, retries=60, backoff=0.01):
    """원자적 JSON 쓰기 — tmp 파일 후 os.replace (다중 워커 레이스 방지).

    Windows에선 대상이 다른 프로세스에 열려 있는 순간 os.replace가
    PermissionError를 내므로 짧은 백오프로 재시도한다. 독자는 항상
    구버전 또는 신버전 전체 파일만 본다 (절단본 없음).
    """
    import time
    path = os.fspath(path)
    d = os.path.dirname(os.path.abspath(path))
    fd, tmp = tempfile.mkstemp(dir=d, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(obj, f, indent=indent, ensure_ascii=False)
        for attempt in range(retries):
            try:
                os.replace(tmp, path)
                return
            except PermissionError:
                if attempt == retries - 1:
                    raise
                time.sleep(backoff * (1 + attempt % 5))
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def read_json(path, retries=60, backoff=0.01):
    """레이스 내성 JSON 읽기 — 교체 순간의 PermissionError/부분 파일에 재시도.

    atomic_json_write와 짝. 다중 프로세스 환경의 표준 읽기 경로.
    """
    import time
    last = None
    for attempt in range(retries):
        try:
            with open(os.fspath(path), encoding="utf-8") as f:
                return json.load(f)
        except (PermissionError, json.JSONDecodeError) as e:
            last = e
            time.sleep(backoff * (1 + attempt % 5))
    raise last


def candidate_save(path, obj, force=False):
    """후보 JSON 저장 — 기존 파일 존재 시 거부 (새 pXX 파일을 만들 것).

    canonical 갱신은 bench promote 경유가 유일한 정규 경로.
    """
    path = os.fspath(path)
    if os.path.exists(path) and not force:
        raise FileExistsError(
            f"candidate_save: {path} 이미 존재. 후보 JSON은 불변 — "
            f"새 fourbar_pXX_candidate.json 파일명을 쓰거나 bench promote를 사용하라. "
            f"(의도적 덮어쓰기는 force=True)")
    atomic_json_write(path, obj)
