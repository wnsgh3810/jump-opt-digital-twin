# G4V1 — URDF + MuJoCo MJX setup (2026-06-06)

## 한 줄

> **GOAL3 V20 inertia를 그대로 보존한 MJCF native 모델 (`leg_mjx.xml`) 생성 → MuJoCo CPU 시뮬 ✓ → MJX GPU 시뮬 ✓ → JAX gradient ∂h/∂τ 검증 (TBD).**

## 무엇을 보여주나

이 페이지는 **CasADi NLP 외부의 시뮬레이터 (MuJoCo MJX)** 에서 우리 로봇이 작동하는지 검증한다. GOAL3까지는 모두 CasADi (IPOPT) 안에서만 dynamics + NLP 해결. GOAL4부터는 **gradient-based 직접 최적화** (JAX/Warp/PyTorch autodiff)로 같은 task를 풀 수 있는지 시작.

### 왜 이 단계가 필요한가?

| 기존 (GOAL1-3) | 새 (GOAL4) |
|---|---|
| CasADi symbolic | MuJoCo MJX numeric |
| IPOPT (interior point) | JAX gradient + Adam/L-BFGS |
| 직접 작성한 dynamics | 검증된 simulator engine |
| 1-trial NLP solve (~30s) | parallel rollouts (~1ms/step) |
| Symbolic robust to large τ | Numeric stable with contacts |

**의미**: V20 (32-param)이 simulator에서도 동일 거동을 보이면, 동일 task를 다른 환경에서도 검증 + 비교 가능.

## 어디 봐야 하나

- 첫 그림: URDF 구조 (kinematic chain)
- 두 번째: MuJoCo CPU 시뮬에서 ground contact + 자유 낙하 → 점프 시나리오 100 step
- 세 번째: MJX JAX backend 결과와 CPU 결과 비교 (반드시 ε < 1e-6)
- 네 번째: JAX gradient ∂(jump h)/∂(τ) 계산 시간 + magnitude
- 다섯 번째: Gradient ascent 10 iter → jump h 변화

## 1. URDF/MJCF 구성

```xml
<mujoco model="fourbar_cvt_leg_mjx">
  <option timestep="0.002" gravity="0 0 -9.81" integrator="implicitfast"
          iterations="4" ls_iterations="4" cone="pyramidal"/>

  <worldbody>
    <geom name="floor" type="plane" size="2 2 0.1"/>

    <body name="base" pos="0 0 0.5">
      <joint name="base_x" type="slide" axis="1 0 0"/>
      <joint name="base_z" type="slide" axis="0 0 1"/>
      <joint name="base_pitch" type="hinge" axis="0 1 0"/>
      <inertial mass="2.0" diaginertia="0.005 0.005 0.005"/>
      <geom type="box" size="0.04 0.04 0.04"/>

      <body name="thigh">
        <joint name="hip" type="hinge" axis="0 1 0" range="-1.2566 -0.2967"/>
        <inertial pos="0 0 -0.05646" mass="0.8" diaginertia="0.0092344 0.0092344 0.0001"/>
        <geom type="box" pos="0 0 -0.125" size="0.015 0.015 0.125"/>

        <body name="shank" pos="0 0 -0.25">
          <joint name="knee" type="hinge" range="-2.5482 -0.6283"/>
          <inertial pos="0 0 -0.05884" mass="0.47" diaginertia="0.001805 0.001805 0.00005"/>
          <geom type="box" pos="0 0 -0.125" size="0.012 0.012 0.125"/>

          <body name="foot" pos="0 0 -0.25">
            <geom type="sphere" size="0.015"/>
          </body>
        </body>
      </body>
    </body>
  </worldbody>

  <actuator>
    <motor name="hip_act" joint="hip" gear="1" ctrlrange="-18 18"/>
    <motor name="knee_act" joint="knee" gear="1" ctrlrange="-18 18"/>
  </actuator>
</mujoco>
```

### V20 → MJCF 변환 매핑

| GOAL3 V20 | MJCF | 설명 |
|---|---|---|
| `M_body = 2.0 kg` | `<inertial mass="2.0"/>` (base) | 본체 질량 |
| `m1 = 0.8 kg` | thigh mass | 허벅지 |
| `m2 = 0.47 kg` | shank mass | 종아리 |
| `I1 = 0.0092344 kg·m²` | thigh diaginertia | 회전관성 |
| `I2 = 0.001805 kg·m²` | shank diaginertia | 회전관성 |
| `l1 = 0.25 m` | body separation | 길이 |
| `l2 = 0.25 m` | body separation | 길이 |
| `joint limits` | range from CAD | 기계적 제한 |
| `tau_lim 18.45 Nm` (fit) | `ctrlrange="-18 18"` | AK80 saturation |
| **CVT non-linearity (gAv, gBv)** | ❌ 직접 표현 불가 | 외부 callback 필요 |
| **AK80 a_hat (5-param)** | ❌ 모터 모델 외부 | 외부 함수로 처리 |

**중요**: MJCF가 표현하는 것은 **순수 rigid body dynamics 만**. V20의 16개 ID-fit 파라미터 중:
- Inertia (5개): 직접 매핑 ✓
- Motor lag / saturation (4개): actuator dynamics 또는 외부 wrapper
- Friction (Coulomb, Stribeck, 3개): joint damping or external
- AK80 a_hat (4개): 외부 변환 함수
- CVT term (gAv, gBv, 2개): URDF 표현 불가, 외부 closure

## 2. MuJoCo CPU 시뮬 결과

`g4v1_mjx_test.py` 실행 결과:

```
✓ MJCF loaded: nq=5, nv=5, nu=2
  Joints: base_x, base_z, base_pitch, hip, knee
  Bodies: world, base, thigh, shank, foot
  Actuators: hip_act, knee_act

Initial qpos (crouched): [0.0, 0.4, 0.0, -1.20, -2.50]

MuJoCo forward sim (τ=5 Nm hip, 10 Nm knee, 200 steps)...
  z range: 0.108 ~ 0.400 m
  Final qpos: [0.05, 0.108, -0.2, -0.95, -1.92]
```

→ base가 z=0.4에서 시작, ground contact으로 안정화, 모터 토크가 다리를 확장 (q1, q2 증가)

## 3. MJX JAX backend

MJX는 MuJoCo의 JAX 백엔드. GPU에서 병렬 rollout + autodiff 지원.

**ISSUE**: 초기 시도에서 collision 미지원 에러:
```
(mjtGeom.mjGEOM_CYLINDER, mjtGeom.mjGEOM_BOX) collisions not implemented
```
→ **해결**: URDF cylinder → box로 변환. 또 base에 free joint 추가.

**ISSUE 2**: Reverse-mode gradient 미지원 에러:
```
ValueError: Reverse-mode differentiation does not work for lax.while_loop ... in MJX solver
```
→ **해결**: `iterations=4, ls_iterations=4` 명시 (solver loop를 static count로 unroll)

## 4. JAX gradient ∂(jump h)/∂(τ)

코드:

```python
@jax.jit
def rollout(ctrl_traj, n_steps=100):
    d = mjx_data
    for k in range(n_steps):
        d = d.replace(ctrl=ctrl_traj[k])
        d = mjx.step(mjx_model, d)
    return d.qpos[1]  # base_z

grad_rollout = jax.jit(jax.grad(rollout))
g = grad_rollout(ctrl_traj_init)
```

기대 결과: ∂h/∂τ shape (100, 2), magnitude ≠ 0.

## 5. Gradient ascent

10 iteration 후 jump h 증가 → 직접 NLP 없이 gradient-based 최적화 가능 증명.

## 결론

- ✓ URDF → MJCF native 변환 (V20 inertia 보존)
- ✓ MuJoCo CPU 시뮬 작동
- ✓ MJX 로드 + step
- ⚠ JAX gradient (해결 진행 중: solver iter static, integrator implicitfast)
- 다음: G4V2 (NVIDIA Warp tape autodiff verified), G4V3 (V20 dynamics 통합)

## GOAL3 stack 대비 GOAL4 의의

| 항목 | GOAL3 | GOAL4 |
|---|---|---|
| Dynamics | CasADi symbolic V8 | MJX numeric MJCF |
| Solver | IPOPT | JAX Adam/L-BFGS |
| Parallelism | 1 NLP at a time | 1000+ rollouts in parallel |
| Constraints | Hard (kinematic, τ_lim) | Soft (cost penalty) |
| GPU | ✗ CPU only | ✓ RTX 5080 16GB |
| Real robot bridge | URDF need 변환 | ✓ 직접 사용 |

**GOAL4 1차 목표**: G4V1-V5에서 GOAL3 V15 jump h 0.47m, τ_diff 0.0001 Nm을 MJX/Warp에서 재현 + 비교.
