# Targeted Papers: Parallel Actuation / Closed-Chain Simulation / Four-Bar-like Modeling

이 페이지는 보행/휴머노이드 로봇에서 four-bar, five-bar, differential pulley 같은 parallel actuation 또는 closed-chain mechanism을 **시뮬레이션과 제어에 어떻게 구현했는지**만 대상으로 다시 정리한 것입니다.

## 핵심 분류

- **Native closed-chain simulation**: MuJoCo/MJX/Kamino처럼 loop constraint를 물리엔진 안에서 직접 풉니다.
- **Kinematic actuation model**: 전체 폐루프를 모두 시뮬레이션하지 않고, serial main chain에 motor-joint kinematic map과 Jacobian 전달비를 붙입니다.
- **OCP closure constraints**: kinematic closure equation과 analytical derivative를 optimal control constraint로 넣습니다.
- **Robot description extension**: URDF 같은 tree-only 포맷을 parallel mechanism 표현 가능하게 확장합니다.

## 결론적으로 지금 CVT/4-bar 모델과 가장 가까운 구현 방식

1. 정확한 폐루프 동역학까지 보존하려면 `Mechanical Intelligence-Aware...` 또는 `Kamino`처럼 closed-chain constraints를 simulator가 직접 풀어야 합니다.
2. 빠른 최적화/제어가 목적이면 `Kinematic Actuation Models`처럼 motor-joint map을 만들고 `J=dq_joint/dq_motor`로 속도/토크/제약을 변환하는 방식이 가장 현실적입니다.
3. trajectory optimization 안에 폐루프를 직접 넣으려면 `Optimal Control of Walkers...`처럼 closure constraint와 derivative를 OCP에 넣는 방식이 맞습니다.

## 논문 목록

### [core] Mechanical Intelligence-Aware Curriculum Reinforcement Learning for Humanoids with Parallel Actuation (2025)

- 저자: Yusuke Tanaka, Alvin Zhu, Quanyou Wang, Dennis Hong
- 관련성: 사용자가 든 예시. differential pulley, five-bar linkage, four-bar linkage를 모두 다루고, BRUCE humanoid에서 closed-chain constraints를 MJX/MuJoCo 안에 native로 시뮬레이션해 RL을 학습한다.
- 구현 방식: serial approximation이나 단순 Jacobian 보정이 아니라, GPU-accelerated MuJoCo/MJX에서 closed-chain constraints 자체를 유지한다. 병렬기구의 비선형 mechanical property를 policy training 중 그대로 보존한다.
- 봐야 할 부분: four-bar/five-bar/differential pulley를 simulation model에 넣는 방식, MJX constraint 구현, RL curriculum에서 parallel mechanism aware policy를 구성하는 부분.
- PDF: `pdfs/2507.00273_mechanical_intelligence_parallel_actuation_bruce_mjx.pdf`
- arXiv: https://arxiv.org/abs/2507.00273
- 다운로드 상태: `already_exists`

### [core] Control of Humanoid Robots with Parallel Mechanisms using Kinematic Actuation Models (2025)

- 저자: Victor Lutz, Ludovic de Matteis, Virgile Batto, Nicolas Mansard
- 관련성: four-bar knee linkage와 parallel 2-DoF ankle을 직접 다룬다. Cassie류처럼 모터가 joint와 떨어져 있고 reduction ratio가 비선형인 구조에 가장 직접적이다.
- 구현 방식: 전체 closed-chain dynamics를 모두 풀기보다 serial chain inertia에 analytical inverse kinematics 기반 kinematic actuation map을 붙인다. 전달비는 motor-joint velocity map의 Jacobian으로 처리하고, torque/speed/range limit도 그 map으로 변환한다.
- 봐야 할 부분: q_motor와 q_joint mapping, J=dq_joint/dq_motor, tau 변환, DDP/PPO 안에 actuator model을 넣는 방식. 사용자의 CVT/4-bar 모델과 가장 가까운 레퍼런스.
- PDF: `pdfs/2503.22459_kinematic_actuation_models_parallel_mechanisms.pdf`
- arXiv: https://arxiv.org/abs/2503.22459
- 다운로드 상태: `already_exists`

### [core] Optimal Control of Walkers with Parallel Actuation (2025)

- 저자: Ludovic de Matteis, Virgile Batto, Justin Carpentier, Nicolas Mansard
- 관련성: legged robot closed-loop kinematic chain을 optimal control 문제 안에 직접 포함한다. serial-chain approximation을 피하는 쪽이다.
- 구현 방식: kinematic closure condition과 그 analytical derivatives를 OCP 제약으로 넣는다. solver가 closed-chain의 nonlinear transmission effect를 직접 활용하게 만든다.
- 봐야 할 부분: closure constraint 식, derivative/Jacobian을 OCP에 넣는 방식, peak actuator effort가 줄어드는 비교 결과.
- PDF: `pdfs/2504.00642_optimal_control_walkers_parallel_actuation.pdf`
- arXiv: https://arxiv.org/abs/2504.00642
- 다운로드 상태: `already_exists`

### [core] Extended URDF: Accounting for parallel mechanism in robot description (2025)

- 저자: Virgile Batto, Ludovic de Matteis, Nicolas Mansard
- 관련성: 폐루프/parallel mechanism을 URDF 같은 robot description에 어떻게 표현할지 다룬다. 시뮬레이터 구현 전 단계에서 매우 중요하다.
- 구현 방식: 기존 URDF가 tree structure 중심이라 closed loop를 표현하지 못하는 문제를, 최소 추가 정보로 parallel mechanism을 기술하는 extended description으로 해결한다.
- 봐야 할 부분: robot description에서 loop closure를 표현하는 필드/구조, simulation/control toolchain으로 넘기는 방법.
- PDF: `pdfs/2504.04767_extended_urdf_parallel_mechanism_robot_description.pdf`
- arXiv: https://arxiv.org/abs/2504.04767
- 다운로드 상태: `already_exists`

### [core] Kamino: GPU-based Massively Parallel Simulation of Multi-Body Systems with Challenging Topologies (2026)

- 저자: Vassilios Tsounis et al.
- 관련성: kinematic loops를 mimic joint나 serial approximation으로 우회하지 않고 GPU 물리 solver에서 native로 푸는 논문. DR Legs라는 six nested kinematic loops biped 예시가 있다.
- 구현 방식: closed kinematic chains/contact를 constrained rigid multibody forward dynamics로 풀고, nonlinear complementarity/constraint force 계산을 GPU 병렬화한다.
- 봐야 할 부분: closed-loop constraint force를 forward dynamics에서 푸는 방식, RL용 parallel simulation 구조, mimic joint/explicit loop-closure 우회법과의 차이.
- PDF: `pdfs/2603.16536_kamino_gpu_closed_kinematic_loops_simulation.pdf`
- arXiv: https://arxiv.org/abs/2603.16536
- 다운로드 상태: `already_exists`

### [core-adjacent] A Generalized Theory of Load Distribution in Redundantly-actuated Robotic Systems (2026)

- 저자: Joshua Flight, Clement Gosselin
- 관련성: legged robot을 포함한 multiple independent closed-loop kinematic chains에서 load/wrench가 어떻게 분배되는지 이론적으로 다룬다.
- 구현 방식: resultant wrench를 여러 closed-loop chain이 어떻게 분담할 수 있는지 feasible set과 explicit solution으로 표현한다.
- 봐야 할 부분: 폐루프 다중 구동계에서 force/torque distribution을 해석하는 방법. 직접 four-bar simulation은 아니지만 병렬/중복구동 해석에 유용.
- PDF: `pdfs/2603.11431_load_distribution_redundantly_actuated_closed_loop_systems.pdf`
- arXiv: https://arxiv.org/abs/2603.11431
- 다운로드 상태: `already_exists`

### [core-adjacent] A Co-Design Framework for High-Performance Jumping of a Five-Bar Monoped with Actuator Optimization (2026)

- 저자: Aastha Mishra, Aman Singh, Shishir Kolathaya
- 관련성: five-bar closed-chain monoped에서 mechanical design, motor, gearbox, control parameter를 같이 최적화한다.
- 구현 방식: closed-chain five-bar leg와 actuator/gearbox model을 co-design optimization에 넣는다. gear ratio가 mass/efficiency/torque/speed에 미치는 영향을 포함한다.
- 봐야 할 부분: five-bar closed-chain leg를 optimizer에서 어떤 변수와 constraint로 다루는지, actuator optimization map을 어떻게 연결하는지.
- PDF: `pdfs/2604.06025_five_bar_monoped_closed_chain_actuator_codesign.pdf`
- arXiv: https://arxiv.org/abs/2604.06025
- 다운로드 상태: `already_exists`

### [implementation-adjacent] A Framework for Optimal Ankle Design of Humanoid Robots (2025)

- 저자: Guglielmo Cervettini, Roberto Mauceri, Alex Coppola, Fabio Bergonti, Luca Fiorio, Marco Maggiali, Daniele Pucci
- 관련성: humanoid ankle에서 parallel mechanism architecture를 설계/평가한다. 직접 보행 제어 논문은 아니지만, parallel ankle의 기구학 해석과 최적화가 주제와 맞는다.
- 구현 방식: SPU와 RSU parallel ankle architecture의 kinematics를 풀고, workspace feasibility와 actuator/task requirement를 반영해 multi-objective design optimization을 수행한다.
- 봐야 할 부분: parallel ankle geometry parameterization, workspace feasibility 조건, serial ankle 대비 parallel architecture 평가 지표.
- PDF: `pdfs/2509.16469_optimal_parallel_ankle_design_humanoid_robots.pdf`
- arXiv: https://arxiv.org/abs/2509.16469
- 다운로드 상태: `already_exists`

### [implementation-adjacent] Humanoid Robot Running Through Random Stepping Stones and Jumping Over Obstacles: Step Adaptation Using Spring-Mass Trajectories (2025)

- 저자: Sait Sovukluk, Johannes Englsberger, Christian Ott
- 관련성: parallel mechanism 자체가 주제는 아니지만, humanoid WBC에서 closed-kinematic chain systems를 고려하고 MuJoCo에서 agile behavior를 검증한다.
- 구현 방식: spring-mass trajectory를 humanoid whole-body model로 mapping할 때 closed-kinematic chain systems, self collision, reactive limb swinging을 WBC에 포함한다.
- 봐야 할 부분: closed-kinematic chain system을 WBC mapping과 MuJoCo simulation에서 어떻게 처리했는지.
- PDF: `pdfs/2512.13304_humanoid_running_closed_kinematic_chain_wbc_mujoco.pdf`
- arXiv: https://arxiv.org/abs/2512.13304
- 다운로드 상태: `already_exists`

### [mechanism-modeling-adjacent] From Structural Design to Dynamics Modeling: Control-Oriented Development of a 3-RRR Parallel Ankle Rehabilitation Robot (2025)

- 저자: Siyuan Zhang, Yufei Zhang, Junlin Lyu, Sunil K. Agrawal
- 관련성: 보행 로봇은 아니지만, 3-RRR spherical parallel ankle mechanism의 구조 설계부터 kinematic/dynamic modeling, torque estimation, simulation analysis까지 연결한다.
- 구현 방식: structural design, kinematic modeling for motion planning, Lagrangian-based dynamic modeling, torque estimation, representative trajectory simulation을 하나의 pipeline으로 구성한다.
- 봐야 할 부분: parallel ankle의 Lagrangian dynamics 모델링, torque estimation, motion tracking simulation 구성.
- PDF: `PDF 없음 또는 다운로드 실패`
- arXiv: https://arxiv.org/abs/2505.13762
- 다운로드 상태: `failed:HTTP Error 404: Not Found`

### [adjacent] Design and Central Pattern Generator Control of a New Transformable Wheel-Legged Robot (2024)

- 저자: Tyler Bishop, Keran Ye, Konstantinos Karydis
- 관련성: generalized four-bar mechanism을 wheel-leg trajectory와 controller에 연결한다. humanoid는 아니지만 four-bar leg 구현 사례다.
- 구현 방식: four-bar mechanism kinematic analysis로 CPG oscillator state를 실제 leg/wheel trajectory에 mapping한다.
- 봐야 할 부분: four-bar kinematic map을 controller input/output에 연결하는 방식.
- PDF: `pdfs/2407.03765_four_bar_transformable_wheel_legged_robot.pdf`
- arXiv: https://arxiv.org/abs/2407.03765
- 다운로드 상태: `already_exists`

## 이번 검색에서 제외한 것

- 일반 HZD/MPC/LIPM 보행 제어 논문: 폐루프 제어라는 단어는 맞지만, four-bar/parallel actuation 구현과 직접 관련이 약해서 제외.
- 일반 SEA/QDD/gear ratio 논문: actuator 관점에는 중요하지만, closed-chain simulation 구현 논문은 아니라 제외.
- 일반 four-bar synthesis 논문: mechanism 설계에는 도움되지만, humanoid/legged robot simulation-control 구현과 직접 연결되지 않으면 제외.
