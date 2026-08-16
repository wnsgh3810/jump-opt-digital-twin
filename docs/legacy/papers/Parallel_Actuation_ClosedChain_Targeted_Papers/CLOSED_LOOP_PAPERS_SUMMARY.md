# 폐루프/병렬구조 로봇 시뮬레이션 구현 논문 정리

기준: `C:\Users\junho\Desktop\Parallel_Actuation_ClosedChain_Targeted_Papers\pdfs` 안에 현재 존재하는 PDF만 정리했다. 다른 폴더의 논문은 포함하지 않았다.

현재 PDF 수: 11개

## 전체 분류

### 1. 폐루프 구조를 시뮬레이터에 직접 넣는 계열

핵심 철학은 “실제 로봇이 가진 폐루프/병렬기구의 비선형성과 구속조건을 학습/제어 단계에서 없애지 말자”이다. 단순 serial approximation을 쓰면 학습은 편하지만, 실제 하드웨어의 coupling, motor-space 특성, 마찰, 내부 구속력, 전달비 변화가 사라져 sim-to-real gap이 커진다는 문제의식이 공통이다.

해당 논문:
- `2507.00273_mechanical_intelligence_parallel_actuation_bruce_mjx.pdf`
- `2505.12231_3dof_hopping_robot_closed_loop_ankle_raisim.pdf`
- `2503.08349_lips_parallel_series_closed_loop_humanoid_rl.pdf`
- `2507.10164_topa_biped_closed_kinematic_chains_rl.pdf`
- `2603.16536_kamino_dr_legs_six_nested_kinematic_loops.pdf`

### 2. 폐루프 구조를 해석적 모델/최적화 제약으로 넣는 계열

핵심 철학은 “폐루프 구조 전체를 매번 물리엔진으로 풀지 않아도, motor-joint map, closure constraint, Jacobian을 정확히 넣으면 제어/최적화에서 충분히 빠르고 정확하게 쓸 수 있다”이다. 즉 native simulation보다 계산량을 줄이면서도, 상수 gear ratio나 open-chain 근사보다 정확한 모델을 얻는 접근이다.

해당 논문:
- `2503.22459_kinematic_actuation_models_parallel_mechanisms.pdf`
- `2504.00642_optimal_control_walkers_parallel_actuation.pdf`
- `2311.08409_digit_closed_kinematic_chains_safe_wbc.pdf`
- `2408.08830_digit_constrained_robot_sysid_closed_kinematic_chains.pdf`

### 3. 폐루프 구조를 표현/검증하기 위한 기반 계열

핵심 철학은 “폐루프 구조를 잘 제어하려면 먼저 로봇 description과 simulator/contact 모델이 그 구조를 제대로 표현하고 검증할 수 있어야 한다”이다. 직접 제어기보다 인프라에 가까운 논문들이다.

해당 논문:
- `2504.04767_extended_urdf_parallel_mechanism_robot_description.pdf`
- `2110.00541_validating_robotics_simulators_real_world_impacts.pdf`

## 논문별 정리

## 1. Mechanical Intelligence-Aware Curriculum Reinforcement Learning for Humanoids with Parallel Actuation

파일: `2507.00273_mechanical_intelligence_parallel_actuation_bruce_mjx.pdf`

대상 로봇/구조:
BRUCE humanoid. differential pulley, five-bar linkage, four-bar linkage가 포함된 병렬구동 humanoid 구조를 다룬다.

폐루프 구현 방식:
GPU-accelerated MuJoCo, 즉 MJX에서 closed-chain constraints를 native로 시뮬레이션한다. 논문은 기존 RL 프레임워크가 병렬기구를 serial approximation으로 단순화하는 문제를 지적하고, 세 가지 병렬기구의 일반화된 formulation과 simulation method를 제시한다.

좋은 점:
실제 하드웨어의 mechanical nonlinearity를 학습 중에 보존한다. 따라서 단순화된 serial model로 학습한 정책보다 병렬구조의 coupling, 내부 전달 특성, motor-space behavior를 더 잘 반영한다. 결과적으로 zero-shot real-world deployment와 surface generalization에 유리하다는 논리를 세운다.

왜 그렇게 했는가:
병렬기구는 단순한 외란이나 보정항이 아니라 로봇의 “mechanical intelligence”라는 관점이다. 즉 기구 설계 자체가 제어에 도움을 주는 정보인데, 학습 과정에서 이를 제거하면 정책이 실제 로봇을 잘못 배운다.

차별점/철학:
이 논문은 “제어 시간에만 폐루프 보정”하는 것이 아니라 “학습 환경 자체에 폐루프를 넣자”는 입장이다. 가장 직접적인 native closed-chain simulation 계열이다.

## 2. Design of a 3-DOF Hopping Robot with an Optimized Gearbox

파일: `2505.12231_3dof_hopping_robot_closed_loop_ankle_raisim.pdf`

대상 로봇/구조:
박혜원 교수팀의 one-leg 3-DOF hopping robot. knee는 four-bar linkage로 1:1 torque transmission을 사용하고, ankle pitch/roll은 closed-loop parallel mechanism이다.

폐루프 구현 방식:
RaiSim의 kinematic-chain support를 사용한다. 논문은 ankle closed-loop 구조를 직접 시뮬레이션하며, closed-loop system을 kinematic tree에 pin constraint를 추가해 두 링크 위의 두 점 사이 위치 일관성을 강제하는 방식으로 모델링한다고 설명한다.

초기화 문제 처리:
RL episode가 random generalized coordinates에서 시작하면 폐루프가 처음부터 일관되지 않을 수 있다. 이를 해결하기 위해 sub-step phase를 둔다. 이 단계에서 ankle pitch/roll joint에 PD control을 적용해 초기 값을 유지하면서 pin constraint가 나머지 링크들을 점진적으로 정렬하게 한다. 충분히 일관된 configuration이 된 뒤 episode를 시작한다.

좋은 점:
실제 ankle parallel mechanism의 pitch/roll coupling을 제어 학습에 반영한다. 폐루프를 무시하고 단순 2-DoF ankle로 취급하면 actuator 배치와 기구 coupling이 사라지지만, 이 방법은 RaiSim 안에서 실제 구조를 유지한다.

왜 그렇게 했는가:
flat-foot hopping은 접촉과 자세 안정성이 중요하고, ankle의 폐루프 병렬구조가 pitch/roll 동작을 만든다. 따라서 제어기는 이 구조를 고려해야 하며, 단순 open-chain ankle 모델로는 실제 하드웨어와 맞지 않는다.

차별점/철학:
“시뮬레이터가 지원하는 kinematic-chain/pin constraint 기능을 이용해 실제 폐루프 관절을 직접 넣고, 초기 불일치까지 별도 phase로 정리한다”는 실용적인 구현 논문이다. 현재 작업의 예시로 매우 직접적이다.

## 3. LiPS: Large-Scale Humanoid Robot Reinforcement Learning with Parallel-Series Structures

파일: `2503.08349_lips_parallel_series_closed_loop_humanoid_rl.pdf`

대상 로봇/구조:
parallel-series structure를 가진 humanoid. 논문은 humanoid가 복잡한 series/parallel mechanism을 가진다는 점을 문제의 출발점으로 둔다.

폐루프 구현 방식:
기존 GPU physics engine은 대체로 open-loop topology만 지원하거나 multi-rigid-body closed-loop topology 시뮬레이션 능력이 제한적이라고 본다. LiPS는 simulation environment에 multi-rigid-body dynamics modeling을 넣어, 학습 중 open-loop model로 단순화한 뒤 real phase에서 병렬구조로 변환하는 방식을 줄이려 한다.

좋은 점:
large-scale RL 훈련에서 parallel-series 구조를 더 이른 단계에 반영해 sim-to-real gap을 줄인다. 기존 접근은 학습 단계에서는 open-loop로 두고 실제 배포 단계에서 구조 변환을 하므로, 정책이 배운 동역학과 실제 구조가 달라진다.

왜 그렇게 했는가:
대규모 병렬 학습에는 GPU physics가 필요하지만, GPU engine은 폐루프 topology를 잘 처리하지 못한다. 그래서 병렬구조를 버리면 학습은 빠르지만 실제성과 성능이 떨어진다. LiPS는 이 trade-off를 줄이려는 시도다.

차별점/철학:
“GPU-scale RL을 포기하지 않으면서 humanoid의 parallel-series structure를 학습 환경에 반영하자”는 입장이다. BRUCE/MJX 논문과 비슷한 문제의식이지만, 특정 parallel mechanism formulation보다 대규모 humanoid RL pipeline 쪽에 초점이 있다.

## 4. Robust RL Control for Bipedal Locomotion with Closed Kinematic Chains

파일: `2507.10164_topa_biped_closed_kinematic_chains_rl.pdf`

대상 로봇/구조:
custom-built biped robot TopA. closed kinematic chains를 가진 bipedal locomotion 문제를 다룬다.

폐루프 구현 방식:
RL framework가 closed-chain dynamics를 명시적으로 포함한다. 논문은 대부분의 RL 접근이 parallel mechanism을 serial model로 단순화하며, 이것이 joint coupling, friction dynamics, motor-space control characteristics를 놓쳐 sim-to-real transfer를 악화시킨다고 주장한다.

좋은 점:
폐루프 구조의 coupling과 motor-space 특성을 학습에 반영해 실제 지형 locomotion 성능을 높인다. 실험적으로 simplified kinematic model 기반 방식보다 안정적인 locomotion을 보인다는 논리다.

왜 그렇게 했는가:
폐루프 구조를 가진 biped는 단순 serial biped와 동역학이 다르다. 특히 마찰과 actuator/motor-space behavior가 강하게 영향을 주므로, 구조를 단순화하면 실제 로봇에서 정책이 틀어진다.

차별점/철학:
“폐루프 구조를 제어기 밖의 기계적 세부사항으로 보지 말고, RL dynamics model의 일부로 넣어야 한다”는 입장이다. BRUCE 논문과 같은 철학이지만, TopA라는 별도 biped 플랫폼에서 robust RL 쪽을 강조한다.

## 5. Kamino: GPU-based Massively Parallel Simulation of Multi-Body Systems with Challenging Topologies

파일: `2603.16536_kamino_dr_legs_six_nested_kinematic_loops.pdf`

대상 로봇/구조:
DR Legs biped. six nested kinematic loops를 가진 구조를 예시로 사용한다.

폐루프 구현 방식:
Kamino는 kinematic loops 같은 strongly coupled kinematic/dynamic constraints를 GPU-based physics solver에서 native로 지원한다. 기존 방식처럼 kinematic tree로 근사하거나 explicit loop-closure constraint 또는 mimic joint로 우회하지 않는다. constrained rigid multibody forward dynamics를 nonlinear complementarity problem으로 풀어 constraint forces를 계산한다.

좋은 점:
tree-structured topology 가정을 깨고도 대규모 parallel simulation을 수행할 수 있다. RL policy training에서 DR Legs를 4096 parallel environments로 시뮬레이션하는 예시를 제시한다.

왜 그렇게 했는가:
GPU 시뮬레이터는 빠르지만 대부분 reduced-coordinate/tree topology에 최적화되어 있다. 하지만 실제 기계 시스템은 closed kinematic chains를 이용해 mechanical advantage를 얻는다. 이를 mimic joint나 tree approximation으로 바꾸면 실제 기계의 본질을 잃는다.

차별점/철학:
가장 근본적인 시뮬레이터 레벨 접근이다. 특정 로봇 controller보다 “폐루프 구조를 잘 다루는 물리엔진이 필요하다”는 논문이다.

## 6. Control of Humanoid Robots with Parallel Mechanisms using Kinematic Actuation Models

파일: `2503.22459_kinematic_actuation_models_parallel_mechanisms.pdf`

대상 로봇/구조:
Cassie류 설계에서 영감을 받은 four-bar knee linkage와 parallel 2-DoF ankle mechanism.

폐루프 구현 방식:
전체 closed-loop mechanism을 동역학 모델에 모두 넣지 않는다. 대신 main serial chain inertia는 유지하고, analytical inverse kinematics 기반 kinematic actuation model을 둔다. motor coordinate와 joint coordinate 사이의 mapping을 만들고, 그 미분인 Jacobian으로 속도/토크/제약을 변환한다.

전달비 구현:
비선형 transmission ratio를 상수 gear ratio로 근사하지 않는다. `dq_joint / dq_motor` 형태의 configuration-dependent Jacobian을 사용한다. 속도는 Jacobian으로 변환하고, torque는 virtual work 관계로 반대 방향 변환을 한다.

좋은 점:
native closed-chain simulation보다 훨씬 빠르다. DDP와 PPO 안에 넣을 수 있을 만큼 계산 효율이 좋고, 동시에 motor capability와 joint range를 단순화하지 않는다.

왜 그렇게 했는가:
full closed-chain dynamics는 계산량이 크고, GPU simulator의 soft/approximate contact constraint는 sim-to-real gap을 만들 수 있다. 반대로 상수 reduction ratio는 폐루프 기구의 장점을 잃는다. 이 논문은 둘 사이의 중간 해법이다.

차별점/철학:
“폐루프 전체를 매번 풀 필요는 없지만, transmission nonlinearity는 정확히 보존해야 한다”는 해석적 모델링 철학이다. 현재 4-bar/CVT 전달비 계산과 가장 직접적으로 연결된다.

## 7. Optimal Control of Walkers with Parallel Actuation

파일: `2504.00642_optimal_control_walkers_parallel_actuation.pdf`

대상 로봇/구조:
closed-loop kinematic chains를 가진 legged walker. four-bar knee 등 parallel actuation 구조를 일반적인 motion generation 문제로 다룬다.

폐루프 구현 방식:
optimal control problem 안에 kinematic closure conditions와 analytical derivatives를 직접 넣는다. 즉 serial-chain approximation으로 닫힌 링크를 없애지 않고, closure constraint를 OCP 제약으로 둔다.

좋은 점:
solver가 closed-chain의 nonlinear transmission effect를 직접 활용할 수 있다. 단순 serial approximation은 특정 구조에만 맞거나 suboptimal motion을 만들 수 있는데, 이 방식은 다양한 closed-chain architecture에 더 일반적으로 적용할 수 있다.

왜 그렇게 했는가:
기존 motion generation은 폐루프 구조를 low-level controller에서만 처리하거나, serial chain으로 근사하는 경우가 많다. 그러면 최적화 단계에서 기구의 실제 mobility/efficiency를 활용하지 못한다.

차별점/철학:
“폐루프 구조는 제어 후처리에서 보정할 대상이 아니라, motion generation 단계의 제약과 자유도로 들어가야 한다”는 철학이다.

## 8. Safe Whole-Body Task Space Control for Humanoid Robots

파일: `2311.08409_digit_closed_kinematic_chains_safe_wbc.pdf`

대상 로봇/구조:
Agility Robotics Digit. closed kinematic chains와 contact interactions를 가진 humanoid로 다룬다.

폐루프 구현 방식:
inverse dynamics QP controller가 closed kinematic chains를 respect하도록 구성된다. 논문은 four-bar linkage 같은 closed kinematic chain constraints를 예로 들고, constraint wrench와 Jacobian을 통해 controller 안에서 처리한다.

좋은 점:
task-space tracking, ZMP, friction cone, torque constraints, safety-critical constraints를 한 QP 안에서 함께 다룬다. 폐루프 기구를 무시하지 않기 때문에 humanoid의 실제 구조와 contact task를 동시에 만족시키는 제어가 가능하다.

왜 그렇게 했는가:
humanoid whole-body control은 contact와 closed-chain constraints를 동시에 다뤄야 한다. 특히 안전 제약을 넣으려면, 로봇 구조의 실제 constraint를 어긴 상태에서 task tracking만 잘하는 제어기는 위험하다.

차별점/철학:
“폐루프 구조를 가진 humanoid에서는 안전 제약과 task 제약을 모두 만족하는 control QP가 필요하다”는 제어 중심 논문이다. RL보다 model-based WBC 철학에 가깝다.

## 9. System Identification For Constrained Robots

파일: `2408.08830_digit_constrained_robot_sysid_closed_kinematic_chains.pdf`

대상 로봇/구조:
Digit humanoid. closed kinematic chains 또는 other constraints를 가진 constrained robot으로 모델링한다.

폐루프 구현 방식:
constraint function `c(q)=0`, constraint Jacobian `J(q)`, constraint force `J^T lambda`를 포함한 dynamics를 사용한다. 식별 대상은 motor inertia와 joint friction 등이며, constrained system의 equation of motion에 맞춰 iterative least squares를 수행한다.

좋은 점:
일반 unconstrained manipulator용 system identification을 그대로 쓰면 폐루프 로봇에는 맞지 않는다. constraint force와 constraint acceleration 조건을 포함하면 실제 Digit의 동역학 parameter를 더 잘 식별할 수 있다.

왜 그렇게 했는가:
제어 성능은 model parameter에 민감하다. 폐루프/구속 로봇에서 constraint를 무시하고 parameter를 식별하면 torque prediction과 tracking control이 틀어진다.

차별점/철학:
“폐루프 구조는 controller뿐 아니라 system identification 단계에서도 dynamics equation에 들어가야 한다”는 논문이다. 제어 전에 모델을 맞추는 관점에서 중요하다.

## 10. Extended URDF: Accounting for parallel mechanism in robot description

파일: `2504.04767_extended_urdf_parallel_mechanism_robot_description.pdf`

대상 로봇/구조:
parallel mechanism과 closed-loop kinematic structure를 가진 다양한 로봇.

폐루프 구현 방식:
URDF는 기본적으로 tree 구조를 가정하므로 closed-loop를 직접 표현하기 어렵다. 이 논문은 underlying serial kinematic chain은 유지하되, closure constraints를 명시적으로 추가하는 방식으로 URDF를 확장한다.

좋은 점:
robot description 단계에서 폐루프 구조를 잃지 않는다. Pinocchio 같은 기존 design/simulation/control framework와 호환성을 유지하면서 최소한의 추가 정보로 closure를 표현한다.

왜 그렇게 했는가:
시뮬레이션이나 제어 알고리즘이 폐루프를 지원해도, robot model file이 그 구조를 표현하지 못하면 toolchain 전체가 끊어진다. 따라서 description format이 먼저 폐루프를 표현할 수 있어야 한다.

차별점/철학:
“폐루프 구현 문제는 알고리즘만의 문제가 아니라 robot description 문제이기도 하다”는 인프라 논문이다.

## 11. Validating Robotics Simulators on Real-World Impacts

파일: `2110.00541_validating_robotics_simulators_real_world_impacts.pdf`

대상 로봇/구조:
Drake, MuJoCo, Bullet 시뮬레이터와 실제 impact 실험. 고차원 예제로 Cassie biped landing from jump를 사용한다.

폐루프 구현과의 관계:
이 논문은 폐루프 관절 구현 논문은 아니지만, 현재 기준에 맞는 이유는 “폐루프/병렬구조 로봇을 시뮬레이션에 넣었을 때 contact/impact 모델이 얼마나 실제와 맞는가”를 판단하는 기반을 제공하기 때문이다. Cassie jumping landing이라는 legged robot impact case를 다룬다.

좋은 점:
simulator가 contact parameter와 impact modeling choice에 따라 실제와 얼마나 차이나는지 정량적으로 비교한다. 폐루프 기구를 아무리 잘 모델링해도 contact/impact가 틀리면 jump/landing 예측은 틀어진다는 점을 보여준다.

왜 그렇게 했는가:
로봇 정책 학습과 제어는 simulation fidelity에 크게 의존한다. 특히 jumping/landing처럼 고속 impact가 있는 동작에서는 contact가 계산 bottleneck이자 주요 오차 원인이다.

차별점/철학:
“시뮬레이터를 믿기 전에 실제 impact 데이터로 검증하자”는 검증 중심 논문이다. 폐루프 구조 구현 논문들과 직접 같은 범주는 아니지만, jumping/impact simulation 신뢰성 판단에 필요하다.

## 비교 요약

| 분류 | 논문 | 구현 핵심 | 장점 | 한계/주의점 |
|---|---|---|---|---|
| Native closed-chain simulation | BRUCE/MJX | MJX에서 closed-chain constraints 직접 시뮬레이션 | 실제 병렬기구 특성 보존 | simulator support와 계산비용 의존 |
| Native closed-loop with pin constraint | 3-DOF hopping/RaiSim | RaiSim pin constraint로 closed-loop ankle 구현 | 실제 ankle coupling 반영 | 초기 configuration consistency 처리 필요 |
| GPU closed-loop simulator | Kamino | constrained multibody dynamics/NCP | 복잡한 kinematic loops 대규모 병렬 시뮬레이션 | 새로운 solver/framework 의존 |
| Humanoid parallel-series RL | LiPS | simulation environment에 multi-rigid-body modeling 반영 | GPU RL과 병렬구조 반영의 절충 | 구체 구현은 플랫폼/engine 의존 |
| Closed-chain RL | TopA | closed-chain dynamics를 RL framework에 포함 | sim-to-real gap 감소 | 특정 플랫폼 식별/마찰 모델 중요 |
| Kinematic actuation model | KAM paper | analytical IK + Jacobian transmission | 빠르고 최적화/학습에 넣기 쉬움 | full constraint force는 직접 풀지 않음 |
| OCP closure constraint | Optimal Control of Walkers | closure condition + analytical derivative | motion generation 단계에서 폐루프 활용 | OCP formulation 복잡도 증가 |
| WBC/QP | Digit safe WBC | QP inverse dynamics가 closed chains respect | 안전 제약과 task tracking 통합 | model-based controller 튜닝 필요 |
| SysID | Digit constrained sysID | constraint Jacobian 포함 dynamics 식별 | 실제 로봇 parameter 정확도 개선 | 데이터 품질과 constraint model 의존 |
| Description format | Extended URDF | serial chain + explicit closure constraints | toolchain 호환성 개선 | 직접 simulation algorithm은 아님 |
| Simulator validation | Real-world impacts | contact/impact fidelity 비교 | jump/landing simulation 신뢰성 평가 | 폐루프 joint 구현 자체는 아님 |

## 현재 연구에 가져올 수 있는 논리

1. 폐루프/4-bar/CVT 구조는 단순 상수 전달비로 줄이면 핵심 특성이 사라진다.

2. 가장 정확한 구현은 BRUCE/MJX, RaiSim hopping robot, Kamino처럼 simulator 안에 closed-chain constraint를 직접 넣는 것이다.

3. 하지만 최적화나 빠른 제어가 목적이면 Kinematic Actuation Models처럼 analytical IK와 Jacobian 기반 전달비를 쓰는 것이 현실적인 절충이다.

4. OCP에서는 폐루프를 low-level controller에서 보정하지 말고 closure constraint와 derivative를 최적화 문제에 직접 넣어야 한다.

5. RL에서는 폐루프 구조를 학습 중에 제거하면 sim-to-real gap이 커진다. 따라서 native closed-chain simulation 또는 최소한 motor-space/Jacobian/torque conversion을 정책 학습에 반영해야 한다.

6. jumping/landing 연구에서는 폐루프 구현만으로 충분하지 않고, contact/impact simulator fidelity까지 검증해야 한다.

## 가장 직접 참고할 우선순위

1. `2505.12231_3dof_hopping_robot_closed_loop_ankle_raisim.pdf`
   현재 작업처럼 jumping, flat foot, 폐루프 ankle, RL, RaiSim 구현이 모두 들어 있다.

2. `2503.22459_kinematic_actuation_models_parallel_mechanisms.pdf`
   4-bar knee/parallel ankle의 전달비를 analytical IK/Jacobian으로 구현하는 방법이 가장 직접적이다.

3. `2507.00273_mechanical_intelligence_parallel_actuation_bruce_mjx.pdf`
   폐루프를 학습 환경에 native로 넣는 철학과 구현 방향이 명확하다.

4. `2504.00642_optimal_control_walkers_parallel_actuation.pdf`
   최적화 문제에 closure constraint를 넣는 방식 참고.

5. `2603.16536_kamino_dr_legs_six_nested_kinematic_loops.pdf`
   복잡한 폐루프 구조를 물리엔진 수준에서 다루는 큰 방향 참고.
