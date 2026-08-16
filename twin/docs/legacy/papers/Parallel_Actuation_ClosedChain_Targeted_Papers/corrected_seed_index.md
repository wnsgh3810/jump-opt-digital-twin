# Corrected Seed-Based Paper Set

사용자가 지적한 seed 논문 기준으로 다시 좁힌 목록입니다. 기준은 `parallel actuation/closed-chain mechanism을 시뮬레이션, 제어, RL, simulator validation에 어떻게 구현했는가`입니다.

## 제외 기준

- 일반 HZD/MPC 보행 논문 제외
- 일반 SEA/QDD/gear ratio 논문 제외
- 단순 mechanism synthesis 논문 제외
- parallel/closed-chain 구현, contact/impact simulator validation, RAMIEL/Kangaroo-like hybrid mechanism에 직접 닿는 것만 유지

## User seed / exact

### Mechanical Intelligence-Aware Curriculum Reinforcement Learning for Humanoids with Parallel Actuation

- arXiv: https://arxiv.org/abs/2507.00273
- PDF: `pdfs/2507.00273_mechanical_intelligence_parallel_actuation_bruce_mjx.pdf`
- 상태: `already_exists`
- 관련성: BRUCE humanoid. differential pulley, five-bar, four-bar를 MJX/MuJoCo에서 native closed-chain constraints로 직접 시뮬레이션하고 RL curriculum에 넣음.

### Control of Humanoid Robots with Parallel Mechanisms using Kinematic Actuation Models

- arXiv: https://arxiv.org/abs/2503.22459
- PDF: `pdfs/2503.22459_kinematic_actuation_models_parallel_mechanisms.pdf`
- 상태: `already_exists`
- 관련성: 사용자가 말한 Efficient/Differential Actuation 계열로 확인되는 실제 공개 제목. four-bar knee, parallel 2-DoF ankle을 analytical IK + motor-joint Jacobian map으로 DDP/PPO에 통합.

### Optimal Control of Walkers with Parallel Actuation

- arXiv: https://arxiv.org/abs/2504.00642
- PDF: `pdfs/2504.00642_optimal_control_walkers_parallel_actuation.pdf`
- 상태: `already_exists`
- 관련성: closed-loop kinematic chain을 OCP 안에 직접 넣고 closure condition과 analytical derivatives를 제약으로 사용.

### Extended URDF: Accounting for parallel mechanism in robot description

- arXiv: https://arxiv.org/abs/2504.04767
- PDF: `pdfs/2504.04767_extended_urdf_parallel_mechanism_robot_description.pdf`
- 상태: `already_exists`
- 관련성: URDF/tree 구조가 표현 못 하는 parallel mechanism/closed-loop kinematics를 robot description에 넣는 방법.

### Validating Robotics Simulators on Real-World Impacts

- arXiv: https://arxiv.org/abs/2110.00541
- PDF: `pdfs/2110.00541_validating_robotics_simulators_real_world_impacts.pdf`
- 상태: `downloaded`
- 관련성: Drake/MuJoCo/Bullet를 실제 impact 데이터와 비교. Cassie biped landing from jump 포함. 시뮬레이터 contact/impact 모델 검증 관점에서 직접 관련.

## Impact/contact simulator modeling

### Set-Valued Rigid Body Dynamics for Simultaneous, Inelastic, Frictional Impacts

- arXiv: https://arxiv.org/abs/2103.15714
- PDF: `pdfs/2103.15714_set_valued_rigid_body_dynamics_simultaneous_impacts.pdf`
- 상태: `downloaded`
- 관련성: legged locomotion에서 heel/toe strike처럼 거의 동시에 생기는 impact 순서 문제를 set-valued dynamics/LCP로 모델링.

## Parallel wire / kangaroo-like jumping / RL

### Continuous Jumping of a Parallel Wire-Driven Monopedal Robot RAMIEL Using Reinforcement Learning

- arXiv: https://arxiv.org/abs/2403.11205
- PDF: `pdfs/2403.11205_ramiel_parallel_wire_driven_monoped_rl.pdf`
- 상태: `downloaded`
- 관련성: parallel wire mechanism으로 고속/고출력 jumping을 만들고, 시뮬레이션 RL을 실제 RAMIEL에 적용. wire elongation 때문에 velocity를 직접 쓰지 않고 joint-angle history로 추론.

## Parallel wire / kangaroo-like jumping / mechanism

### RAMIEL: A Parallel-Wire Driven Monopedal Robot for High and Continuous Jumping

- arXiv: https://arxiv.org/abs/2311.04573
- PDF: `pdfs/2311.04573_ramiel_parallel_wire_driven_monoped_high_continuous_jumping.pdf`
- 상태: `downloaded`
- 관련성: RAMIEL 하드웨어/기구 구조 논문. 6개 wire로 1 linear DoF + 2 rotational DoF를 만드는 parallel wire-driven leg 구조와 실제 jumping 성능.

## Kangaroo robot / mechanism design

### Design Method of a Kangaroo Robot with High Power Legs and an Articulated Soft Tail

- arXiv: https://arxiv.org/abs/2410.07742
- PDF: `pdfs/2410.07742_kangaroo_robot_high_power_legs_articulated_soft_tail.pdf`
- 상태: `downloaded`
- 관련성: kangaroo-mimetic robot. torso-mounted motor, high-power wire-winding mechanism, articulated elastic tail, simulation-based 구조 검증.

## Parallel mechanism simulator / broader but relevant

### Kamino: GPU-based Massively Parallel Simulation of Multi-Body Systems with Challenging Topologies

- arXiv: https://arxiv.org/abs/2603.16536
- PDF: `pdfs/2603.16536_kamino_gpu_closed_kinematic_loops_simulation.pdf`
- 상태: `downloaded`
- 관련성: closed kinematic loops를 mimic joint/serial approximation 없이 GPU constrained multibody simulation으로 직접 처리. DR Legs biped 예시.

