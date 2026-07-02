"""Generate Notion page content with actual file contents in toggles."""
from pathlib import Path

BASE = Path(__file__).parent / "code"

files = {
    "make_anim.py": ("🎬", "핵심 렌더러 (좌표 변환 + wrap + real-time pace + mj_step 1500 gnd)", "python"),
    "regen_all.py": ("🚀", "30 sub-folder 일괄 orchestrator", "python"),
    "gen_mode_B_pd.py": ("🔧", "PD sim 으로 pseudo mode_B 생성 (jump_0424, jump_0602)", "python"),
    "build_xml_i38_standalone.py": ("📐", "MuJoCo XML 생성기 (self-contained, 외부 의존 없음)", "python"),
    "leg.xml": ("📄", "시각화 XML (build_xml_i38 output, 실제 사용 파일)", "xml"),
    "iter38_best_params.json": ("⚙️", "iter38 best params + iter6 overrides (JSON)", "json"),
}

parts = []

parts.append("""> 🔒 **STATUS: LOCKED CANONICAL — 2026-07-01.** 앞으로 모든 시뮬레이션 렌더링은 이 코드 기준. 모델이 수정되어도 시각화 파이프라인은 그대로 사용.

> **File location**: `C:/Users/junho/Desktop/jump_opt/goal18_CANONICAL/`
> **Final output**: `goal18_v13/Iter6/` — 30/30 sub-folders, 217 gifs, 224 plots
> **Git tag**: `v14-canonical` (annotated) + `LOCKED-2026-07-01`
> **Commit**: `e2fc5ed9` (canonical folder), `f14ca44b` (dependency freeze)

## 🔑 핵심 원칙 (LOCK — 절대 변경 금지)

1. **좌표 변환** (CRITICAL): `mj_q1 = -q1_canonical - π/2`, `mj_q2 = -q2_canonical`
2. **Angle wrap** `(-π, +π]`
3. **카메라**: azim=135°, elev=-15°, dist=1.2, lookat=(0, 0, 0.3)
4. **색상**: base(0.5,0.5,0.5) / thigh(0.6,0.6,0.7) / calf(0.5,0.6,0.6) / foot(0.5,0.5,0.5)
5. **Real-time pace**: `n_frames = clamp(30, 200, round(cyc_dur / 0.04))`, 40ms/frame
6. **GND foot-on-floor**: `mj_step` × **1500회** (500 부족 → 29.3cm 정지 버그), PD kp=1000 kd=50
7. **AIR base**: `base_z = 0.55` 고정, overlay `\"base = 0 (air, fixed)\"`

## 📊 최종 결과

| Dataset | Subs | mode_A | mode_B | Total |
|---|---|---|---|---|
| sit2stand_0324 | 4 | 54 | 54 | 108 |
| sit2stand_air_0319 | 1 | 15 | 15 | 30 |
| sit2stand_gnd_0319 | 1 | 15 | 15 | 30 |
| jump_0424 | 9 | 10 | 9 | 19 |
| jump_0602 | 6 | 6 | 6 | 12 |
| jump_position_0421 | 6 | 6 | 6 | 12 |
| jump_torque_0422 | 3 | 3 | 3 | 6 |
| **TOTAL** | **30** | **109** | **108** | **217** gifs, 224 plots |

## 📝 Iteration History

| Version | 시도 | 결과 |
|---|---|---|
| v10 | Original jump XML | sit2stand 안 보임 |
| v11 | Camera 조정 | 여전히 문제 |
| v12 | v3 오렌지+그린 | 사용자 거부 |
| v13 rev1 | 좌표 변환 미적용 | leg 반대 방향 |
| v13 rev2 | 좌표 변환 + real-time | gnd 29.3cm 정지 |
| v13 rev3 | Wrap 추가 | 여전히 정지 |
| v13 rev4 | mj_step 500→1500 | ✓ 정상 안착 |
| **v14** | **mode_B 30/30 완비** | ✅ **최종 LOCKED** |

---

# 📜 CODE TOGGLES — 전체 파일 실제 내용 (절대 잊지 말 것)

이 토글들은 `goal18_CANONICAL/code/` 내부의 실제 파일 100% 복사. 파일이 사라져도 이거 보면 복구 가능.

""")

for filename, (icon, desc, lang) in files.items():
    content = (BASE / filename).read_text(encoding="utf-8")
    parts.append(f"+++ {icon} `{filename}` — {desc}\n```{lang}\n{content}\n```\n+++\n\n")

parts.append("""
---

## 🔧 사용법

**한 cycle 렌더**:
```python
import sys
sys.path.insert(0, 'C:/Users/junho/Desktop/jump_opt/goal18_CANONICAL/code')
from make_anim import render_sit2stand

render_sit2stand(
    canon_npz_path='.../cycle01.npz',
    model_xml_path='C:/Users/junho/Desktop/jump_opt/goal18_CANONICAL/code/leg.xml',
    out_gif_path='.../cycle01.gif',
    trial_label='sit2stand_0324 P20_D1 mode_A cyc01',
    kind='air'   # or 'gnd'
)
```

**leg.xml 재생성** (모델 params 변경 시):
```python
from build_xml_i38_standalone import build_xml_i38, ITER38_BEST_PARAMS_ITER6
xml = build_xml_i38(**ITER38_BEST_PARAMS_ITER6)
open('leg.xml', 'w').write(xml)
```

**전체 재생성**:
```
python C:/Users/junho/Desktop/jump_opt/goal18_CANONICAL/code/regen_all.py
```

## ⚠️ 알려진 이슈

- **jump_0424/0602 mode_B (15 subs)**: canonical 없음 → PD sim으로 pseudo 생성. `[pseudo]` prefix 표시.
- **canonical GND 후반부 발산** (sit2stand_gnd cycle01 t>4.4s): sim tracking 잃고 q wrap → wrap_pi로 시각적 복구
- **base_z 29.3cm 정지 버그**: mj_step 500 부족. **1500회 필수**.
- **좌표 변환 안 하면 무릎 반대**: 반드시 `mj_q = -q_canonical - offset` 적용

## 🔗 Related

- Memory: `goal18_canonical_pipeline.md`, `feedback_animation_standard.md`
- Git tag: `v14-canonical` (annotated commit `e2fc5ed9`)
- Root marker: `C:/Users/junho/Desktop/jump_opt/CANONICAL_LOCK.md`
""")

output = "".join(parts)
Path(__file__).parent / "notion_payload.md"
out_path = Path(__file__).parent / "notion_payload.md"
out_path.write_text(output, encoding="utf-8")
print(f"Generated {len(output)} chars → {out_path}")
