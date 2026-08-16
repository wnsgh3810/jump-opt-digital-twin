# Closed-Loop Robot Structures Implemented in Simulation

기준: 폐루프/병렬 링크 구조가 있는 로봇을 시뮬레이션, 제어, RL, 또는 simulator validation에 실제로 넣은 논문만 유지합니다. 기존 PDF는 재다운로드하지 않고 `already_exists`로 처리합니다.

## 기존 기준 논문

### Mechanical Intelligence-Aware Curriculum Reinforcement Learning for Humanoids with Parallel Actuation

- arXiv: https://arxiv.org/abs/2507.00273
- PDF: `pdfs/2507.00273_mechanical_intelligence_parallel_actuation_bruce_mjx.pdf`
- 상태: `already_exists`
- 기준 적합 이유: BRUCE humanoid의 differential pulley, five-bar, four-bar를 MJX/MuJoCo에서 native closed-chain constraints로 직접 시뮬레이션.

### Control of Humanoid Robots with Parallel Mechanisms using Kinematic Actuation Models

- arXiv: https://arxiv.org/abs/2503.22459
- PDF: `pdfs/2503.22459_kinematic_actuation_models_parallel_mechanisms.pdf`
- 상태: `already_exists`
- 기준 적합 이유: four-bar knee와 parallel 2-DoF ankle을 analytical IK + motor-joint Jacobian map으로 DDP/PPO에 통합.

### Optimal Control of Walkers with Parallel Actuation

- arXiv: https://arxiv.org/abs/2504.00642
- PDF: `pdfs/2504.00642_optimal_control_walkers_parallel_actuation.pdf`
- 상태: `already_exists`
- 기준 적합 이유: closed-loop kinematic chain을 optimal control 문제 안에 closure constraint와 analytical derivatives로 직접 포함.

### Extended URDF: Accounting for parallel mechanism in robot description

- arXiv: https://arxiv.org/abs/2504.04767
- PDF: `pdfs/2504.04767_extended_urdf_parallel_mechanism_robot_description.pdf`
- 상태: `already_exists`
- 기준 적합 이유: URDF/tree 구조에서 표현하기 어려운 parallel mechanism/closed-loop kinematics를 robot description에 포함.

### Validating Robotics Simulators on Real-World Impacts

- arXiv: https://arxiv.org/abs/2110.00541
- PDF: `pdfs/2110.00541_validating_robotics_simulators_real_world_impacts.pdf`
- 상태: `already_exists`
- 기준 적합 이유: Cassie biped landing from jump를 포함해 Drake/MuJoCo/Bullet의 real-world impact 재현성을 검증.

## 새로 추가: 폐루프/병렬구조를 시뮬레이션에 직접 구현

### Design of a 3-DOF Hopping Robot with an Optimized Gearbox: An Intermediate Platform Toward Bipedal Robots

- arXiv: https://arxiv.org/abs/2505.12231
- PDF: `pdfs/2505.12231_3dof_hopping_robot_closed_loop_ankle_raisim.pdf`
- 상태: `already_exists`
- 기준 적합 이유: 박혜원 교수팀 one-leg hopping robot. ankle closed-loop parallel mechanism을 RaiSim의 kinematic-chain support로 직접 구현하고 pin constraint/sub-step phase로 초기 불일치를 정렬.

### LiPS: Large-Scale Humanoid Robot Reinforcement Learning with Parallel-Series Structures

- arXiv: https://arxiv.org/abs/2503.08349
- PDF: `pdfs/2503.08349_lips_parallel_series_closed_loop_humanoid_rl.pdf`
- 상태: `already_exists`
- 기준 적합 이유: GPU physics engine의 open-loop topology 한계를 지적하고, simulation environment에 multi-rigid-body dynamics modeling을 넣어 humanoid parallel-series structures를 학습.

### Kamino: GPU-based Massively Parallel Simulation of Multi-Body Systems with Challenging Topologies

- arXiv: https://arxiv.org/abs/2603.16536
- PDF: `pdfs/2603.16536_kamino_dr_legs_six_nested_kinematic_loops.pdf`
- 상태: `downloaded`
- 기준 적합 이유: DR Legs biped의 six nested kinematic loops를 mimic joint/tree approximation 없이 GPU constrained multibody simulation으로 처리.

### Robust RL Control for Bipedal Locomotion with Closed Kinematic Chains

- arXiv: https://arxiv.org/abs/2507.10164
- PDF: `pdfs/2507.10164_topa_biped_closed_kinematic_chains_rl.pdf`
- 상태: `downloaded`
- 기준 적합 이유: TopA biped. closed-chain dynamics를 RL framework에 명시적으로 포함하고, simplified kinematic model보다 sim-to-real 성능이 좋아지는 것을 검증.

### A Co-Design Framework for High-Performance Jumping of a Five-Bar Monoped with Actuator Optimization

- arXiv: https://arxiv.org/abs/2604.06025
- PDF: `pdfs/2604.06025_closed_chain_five_bar_monoped_codesign_simulation.pdf`
- 상태: `downloaded`
- 기준 적합 이유: planar closed-chain five-bar monoped를 대상으로 mechanical design, motor/gearbox, control parameters를 함께 최적화하고 simulation에서 jumping 성능을 검증.

## 새로 추가: closed kinematic chains를 가진 Digit 제어/식별

### Safe Whole-Body Task Space Control for Humanoid Robots

- arXiv: https://arxiv.org/abs/2311.08409
- PDF: `pdfs/2311.08409_digit_closed_kinematic_chains_safe_wbc.pdf`
- 상태: `already_exists`
- 기준 적합 이유: Digit humanoid에 적용. QP inverse dynamics controller가 closed kinematic chains를 respect하도록 구성하고 simulation/hardware에서 검증.

### System Identification For Constrained Robots

- arXiv: https://arxiv.org/abs/2408.08830
- PDF: `pdfs/2408.08830_digit_constrained_robot_sysid_closed_kinematic_chains.pdf`
- 상태: `already_exists`
- 기준 적합 이유: closed kinematic chains/constraints가 있는 legged robot을 대상으로 system identification을 수행하고 Digit에서 simulation과 real-world 검증.

