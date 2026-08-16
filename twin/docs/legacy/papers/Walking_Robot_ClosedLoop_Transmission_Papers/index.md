# 보행 로봇 폐루프 모델링, 시뮬레이션 구현, 전달비 관련 논문 정리
생성 위치: `C:\Users\junho\Desktop\Walking_Robot_ClosedLoop_Transmission_Papers`
PDF 폴더: `pdfs/`

## 핵심 결론
- 폐루프 기구를 시뮬레이션에 넣는 방식은 크게 두 가지다: 전체 closed-chain rigid-body constraint를 물리엔진/DAE로 직접 푸는 방식과, 메인 serial chain에 기구학적 actuation map을 붙여 motor-joint 전달비만 별도 계산하는 방식이다.
- four-bar knee/Cassie류 구조에서는 전달비를 상수 gear ratio로 두면 틀릴 수 있다. 보통 `J = dq_joint / dq_motor`를 구하고, 속도는 `dq_joint = J dq_motor`, 토크는 virtual work로 `tau_joint = tau_motor / J` 형태로 변환한다.
- 보행 폐루프는 HZD/virtual constraints, HLIP/DCM/ZMP, MPC, CLF-QP, RL+HZD처럼 hybrid dynamics와 feedback tracking을 결합한다. simulation 구현은 phase event, impact/reset, contact force, actuator saturation을 어떻게 처리하는지가 핵심이다.
- 구동기 관점에서는 전달비가 torque 한계만 바꾸는 것이 아니라 reflected inertia, speed limit, bandwidth, torque transmissibility, thermal limit까지 바꾼다.

## 우선순위로 읽을 논문
1. `2503.22459_kinematic_actuation_parallel_mechanisms.pdf`: 지금 CVT/four-bar knee 전달비 모델링과 가장 직접적으로 연결됨.
2. `1809.07279_cassie_feedback_control.pdf`: Cassie 보행 controller를 실제로 어떻게 닫힌 루프로 구현했는지 확인.
3. `1706.01127_virtual_constraints_hzd.pdf`: HZD/virtual constraints 기본 이론.
4. `2604.06025_five_bar_monoped_codesign.pdf`: closed-chain five-bar와 gear ratio를 co-design에 넣는 최신 예시.
5. `1902.05346_sea_maximum_torque_transmissibility.pdf`: motor torque-speed 한계와 전달계 성능 해석.

## 논문 목록

### A. 폐루프/평행기구/전달비 모델링
#### Control of Humanoid Robots with Parallel Mechanisms using Kinematic Actuation Models (2025)
- 저자: Victor Lutz, Ludovic de Matteis, Virgile Batto, Nicolas Mansard
- 왜 봐야 하는가: Cassie류 four-bar knee linkage와 parallel ankle에서 모터가 조인트에서 떨어져 생기는 비선형 reduction ratio를 trajectory optimization/DDP/RL 안에 직접 넣는 방법을 제시한다.
- 모델링/구현 포인트: 폐루프 기구 전체를 rigid-body tree에 모두 넣기보다, 메인 serial chain inertia와 kinematic actuation map q_motor <-> q_joint를 분리한다. 전달비는 dq_joint/dq_motor Jacobian으로 계산하고 torque는 virtual work로 변환한다.
- 로컬 PDF: `pdfs/2503.22459_kinematic_actuation_parallel_mechanisms.pdf`
- 원문/초록: https://arxiv.org/abs/2503.22459
- 다운로드 상태: `already_exists`
#### A Co-Design Framework for High-Performance Jumping of a Five-Bar Monoped with Actuator Optimization (2026)
- 저자: Aastha Mishra, Aman Singh, Shishir Kolathaya
- 왜 봐야 하는가: planar closed-chain five-bar monoped에서 링크 치수, 모터, gearbox, control parameter를 같이 최적화한다.
- 모델링/구현 포인트: five-bar 폐루프 기구를 설계 변수와 actuator map으로 묶고, gear ratio가 torque, speed, mass, efficiency에 미치는 효과를 최적화 루프에 포함한다.
- 로컬 PDF: `pdfs/2604.06025_five_bar_monoped_codesign.pdf`
- 원문/초록: https://arxiv.org/abs/2604.06025
- 다운로드 상태: `already_exists`
#### Design and Central Pattern Generator Control of a New Transformable Wheel-Legged Robot (2024)
- 저자: Tyler Bishop, Keran Ye, Konstantinos Karydis
- 왜 봐야 하는가: generalized four-bar mechanism 기반 wheel-leg 설계에서 기구학 해석을 CPG controller와 simulation에 연결한다.
- 모델링/구현 포인트: coaxial hub arrangement로 구동되는 four-bar wheel-leg의 기구학을 유도하고, oscillator state를 실제 leg/wheel trajectory로 mapping한다.
- 로컬 PDF: `pdfs/2407.03765_transformable_wheel_legged_robot.pdf`
- 원문/초록: https://arxiv.org/abs/2407.03765
- 다운로드 상태: `already_exists`
#### Leveraging Natural Load Dynamics with Variable Gear-ratio Actuators (2024)
- 저자: Alexandre Girard, H. Harry Asada
- 왜 봐야 하는가: 가변 gear-ratio를 동적으로 선택해 load dynamics를 이용하거나 감쇠시키는 모델 기반 제어를 다룬다.
- 모델링/구현 포인트: gear ratio를 actuator/load dynamics 사이의 동적 map으로 두고, 불확실성과 필요한 torque/power를 기준으로 ratio를 선택한다.
- 로컬 PDF: `pdfs/2405.14441_variable_gear_ratio_actuators.pdf`
- 원문/초록: https://arxiv.org/abs/2405.14441
- 다운로드 상태: `already_exists`
#### Deep Generative Model-based Synthesis of Four-bar Linkage Mechanisms with Target Conditions (2024)
- 저자: Sumin Lee, Jihoon Kim, Namwoo Kang
- 왜 봐야 하는가: four-bar linkage를 kinematic workspace와 quasi-static torque transmission 조건으로 설계한다.
- 모델링/구현 포인트: 링크 길이와 coupler behavior를 조건부 생성모델로 연결하고, torque transmission 성능을 설계 조건으로 둔다.
- 로컬 PDF: `pdfs/2402.14882_four_bar_synthesis_torque_transmission.pdf`
- 원문/초록: https://arxiv.org/abs/2402.14882
- 다운로드 상태: `already_exists`

### B. 보행 폐루프 제어/시뮬레이션 구현
#### Virtual Constraints and Hybrid Zero Dynamics for Realizing Underactuated Bipedal Locomotion (2017)
- 저자: Jessy W. Grizzle, Christine Chevallereau
- 왜 봐야 하는가: biped walking에서 가장 표준적인 폐루프 모델링 프레임워크 중 하나. virtual constraint와 HZD를 명확히 설명한다.
- 모델링/구현 포인트: Lagrangian continuous dynamics, impact reset map, switching surface로 hybrid model을 만들고, feedback controller로 virtual constraints를 강제해 low-dimensional zero dynamics를 만든다.
- 로컬 PDF: `pdfs/1706.01127_virtual_constraints_hzd.pdf`
- 원문/초록: https://arxiv.org/abs/1706.01127
- 다운로드 상태: `already_exists`
#### Feedback Control of a Cassie Bipedal Robot: Walking, Standing, and Riding a Segway (2018)
- 저자: Yukai Gong et al.
- 왜 봐야 하는가: Cassie에서 virtual constraints와 gait library 기반 closed-loop walking controller를 실제 구현한 대표 논문.
- 모델링/구현 포인트: full-order Cassie model, gait library, output tracking controller, state-based feedback을 조합해 standing/walking controller를 구성한다.
- 로컬 PDF: `pdfs/1809.07279_cassie_feedback_control.pdf`
- 원문/초록: https://arxiv.org/abs/1809.07279
- 다운로드 상태: `already_exists`
#### Dynamic Walking on Highly Underactuated Point Foot Humanoids: Closing the Loop between HZD and HLIP (2024)
- 저자: Adrian B. Ghansah, Jeeseop Kim, Kejun Li, Aaron D. Ames
- 왜 봐야 하는가: HZD trajectory와 HLIP step-length regulation을 닫힌 루프로 연결해 humanoid point-foot walking을 만든다.
- 모델링/구현 포인트: offline HZD gait generation, online HLIP regulator, task-space controller/inverse kinematics mapping으로 full-order system을 구동한다.
- 로컬 PDF: `pdfs/2406.13115_hzd_hlip_point_foot_humanoid.pdf`
- 원문/초록: https://arxiv.org/abs/2406.13115
- 다운로드 상태: `already_exists`
#### A Robust Closed-Loop Biped Locomotion Planner Based on Time Varying Model Predictive Control (2019)
- 저자: Mohammadreza Kasaei, Nuno Lau, Artur Pereira
- 왜 봐야 하는가: TVMPC로 DCM/ZMP reference를 online 수정하는 폐루프 보행 planner.
- 모델링/구현 포인트: COM vertical motion, DCM, ZMP constraint를 TVMPC 상태/입출력 제약으로 넣고 MATLAB simulation으로 검증한다.
- 로컬 PDF: `pdfs/1909.06873_tvmc_biped_locomotion_planner.pdf`
- 원문/초록: https://arxiv.org/abs/1909.06873
- 다운로드 상태: `already_exists`
#### A Robust Biped Locomotion Based on Linear-Quadratic-Gaussian Controller and Divergent Component of Motion (2019)
- 저자: Mohammadreza Kasaei, Nuno Lau, Artur Pereira
- 왜 봐야 하는가: LIPM/DCM 기반 closed-loop controller와 swing foot landing adjustment를 다룬다.
- 모델링/구현 포인트: LIPM으로 dynamics를 근사하고 LQG feedback으로 disturbance에 대한 DCM/ZMP response를 제어한다.
- 로컬 PDF: `pdfs/1906.09239_lqg_dcm_biped_locomotion.pdf`
- 원문/초록: https://arxiv.org/abs/1906.09239
- 다운로드 상태: `already_exists`
#### Restricted Discrete Invariance and Self-Synchronization For Stable Walking of Bipedal Robots (2014)
- 저자: Hamed Razavi, Anthony M. Bloch, Christine Chevallereau, J. W. Grizzle
- 왜 봐야 하는가: switching surface, reset map, invariance를 이용해 stable periodic gait를 분석한다.
- 모델링/구현 포인트: continuous Lagrangian dynamics와 discrete impact dynamics로 hybrid walking model을 세우고, closed-loop invariant submanifold를 찾는다.
- 로컬 PDF: `pdfs/1411.0181_discrete_invariance_self_synchronization.pdf`
- 원문/초록: https://arxiv.org/abs/1411.0181
- 다운로드 상태: `already_exists`
#### Reinforcement Learning Meets Hybrid Zero Dynamics: A Case Study for RABBIT (2018)
- 저자: Guillermo A. Castillo, Bowen Weng, Ayonga Hereid, Wei Zhang
- 왜 봐야 하는가: HZD 구조를 policy 안에 넣고 MuJoCo/OpenAI Gym에서 RABBIT 보행을 학습한다.
- 모델링/구현 포인트: RL policy가 virtual constraint trajectory parameter를 출력하고, adaptive PD가 low-level tracking을 담당한다.
- 로컬 PDF: `pdfs/1810.01977_rl_meets_hzd_rabbit.pdf`
- 원문/초록: https://arxiv.org/abs/1810.01977
- 다운로드 상태: `already_exists`
#### Bayesian Optimization Meets Hybrid Zero Dynamics: Safe Parameter Learning for Bipedal Locomotion Control (2022)
- 저자: Lizhi Yang, Zhongyu Li, Jun Zeng, Koushil Sreenath
- 왜 봐야 하는가: Cassie에서 HZD controller parameter를 simulation과 hardware에서 안전하게 학습한다.
- 모델링/구현 포인트: HZD control parameters를 Bayesian optimization으로 조정하고, simulation-to-real discrepancy를 hardware learning으로 보정한다.
- 로컬 PDF: `pdfs/2203.02570_bo_meets_hzd_cassie.pdf`
- 원문/초록: https://arxiv.org/abs/2203.02570
- 다운로드 상태: `already_exists`
#### Hybrid Zero Dynamics Control for Bipedal Walking with a Non-Instantaneous Double Support Phase (2023)
- 저자: Yinnan Luo et al.
- 왜 봐야 하는가: HZD가 흔히 생략하는 finite-duration double support phase를 모델에 포함한다.
- 모델링/구현 포인트: SSP와 DSP를 별도 continuous phase로 두고, rear-leg lift-off와 swing-leg touchdown을 event로 처리한다.
- 로컬 PDF: `pdfs/2303.05165_hzd_non_instantaneous_double_support.pdf`
- 원문/초록: https://arxiv.org/abs/2303.05165
- 다운로드 상태: `already_exists`
#### Bipedal Hopping: Reduced-order Model Embedding via Optimization-based Control (2018)
- 저자: Xiaobin Xiong, Aaron Ames
- 왜 봐야 하는가: Cassie의 leg compliance를 reduced-order spring-mass model로 식별하고 CLF-QP에 embedding한다.
- 모델링/구현 포인트: leg length trajectory를 optimization으로 만들고, full-order biped에 output으로 넣어 jumping/hopping을 구현한다.
- 로컬 PDF: `pdfs/1807.08037_cassie_bipedal_hopping_rom_embedding.pdf`
- 원문/초록: https://arxiv.org/abs/1807.08037
- 다운로드 상태: `already_exists`

### C. 시뮬레이션/접촉/모델 구현
#### mc-mujoco: Simulating Articulated Robots with FSM Controllers in MuJoCo (2022)
- 저자: Rohan P. Singh, Pierre Gergondet, Fumio Kanehiro
- 왜 봐야 하는가: 복잡한 FSM controller를 MuJoCo simulation에 연결하는 구현 논문이다.
- 모델링/구현 포인트: MuJoCo physics engine과 mc-rtc controller framework를 interface하고, HRP-5P biped locomotion FSM controller 예제를 제공한다.
- 로컬 PDF: `pdfs/2209.00274_mc_mujoco_fsm_controllers.pdf`
- 원문/초록: https://arxiv.org/abs/2209.00274
- 다운로드 상태: `already_exists`
#### From Compliant to Rigid Contact Simulation: a Unified and Efficient Approach (2024)
- 저자: Justin Carpentier, Louis Montaut, Quentin Le Lidec
- 왜 봐야 하는가: legged robot simulation에서 중요한 compliant/rigid contact solver 구현을 다룬다.
- 모델링/구현 포인트: NCP contact를 ADMM/proximal method로 풀고, MuJoCo류 inverse dynamics/contact computation을 확장한다.
- 로컬 PDF: `pdfs/2405.17020_compliant_rigid_contact_simulation.pdf`
- 원문/초록: https://arxiv.org/abs/2405.17020
- 다운로드 상태: `already_exists`
#### Soft Adaptive Feet for Legged Robots: An Open-Source Model for Locomotion Simulation (2024)
- 저자: Matteo Crotti et al.
- 왜 봐야 하는가: MuJoCo에서 legged robot foot contact/deformation digital twin을 구현한다.
- 모델링/구현 포인트: soft adaptive foot의 kinematic/dynamic/contact 속성을 MuJoCo model로 만들고 bench test와 비교 검증한다.
- 로컬 PDF: `pdfs/2412.03191_soft_adaptive_feet_mujoco.pdf`
- 원문/초록: https://arxiv.org/abs/2412.03191
- 다운로드 상태: `already_exists`
#### Optimal Reduced-order Modeling of Bipedal Locomotion (2019)
- 저자: Yu-Ming Chen, Michael Posa
- 왜 봐야 하는가: full-order Cassie와 low-dimensional walking model 사이의 자동 모델 축약 방법을 다룬다.
- 모델링/구현 포인트: LIP/SLIP류 reduced-order model 구조를 최적화해 full-order biped/Cassie behavior를 보존한다.
- 로컬 PDF: `pdfs/1909.10111_optimal_rom_bipedal_locomotion.pdf`
- 원문/초록: https://arxiv.org/abs/1909.10111
- 다운로드 상태: `already_exists`

### D. 구동기/전달계/SEA/QDD
#### Stanford Doggo: An Open-Source, Quasi-Direct-Drive Quadruped (2019)
- 저자: Nathan Kau, Aaron Schultz, Natalie Ferrante, Patrick Slade
- 왜 봐야 하는가: legged robot에서 low-ratio QDD actuator를 어떻게 설계하고 제어하는지 좋은 기준점.
- 모델링/구현 포인트: low gear ratio, high torque density actuator를 사용해 torque transparency와 dynamic locomotion을 확보한다.
- 로컬 PDF: `pdfs/1905.04254_stanford_doggo_qdd.pdf`
- 원문/초록: https://arxiv.org/abs/1905.04254
- 다운로드 상태: `already_exists`
#### Alternative Metrics to Select Motors for Quasi-Direct Drive Actuators (2022)
- 저자: Karthik Urs, Challen Enninful Adu, Elliott J. Rouse, Talia Y. Moore
- 왜 봐야 하는가: legged locomotion actuator selection에서 transmission ratio에 덜 종속적인 motor metric을 제안한다.
- 모델링/구현 포인트: motor inertia, torque constant, thermal/torque properties를 gear ratio와 분리해 평가한다.
- 로컬 PDF: `pdfs/2202.12365_qdd_motor_selection_metrics.pdf`
- 원문/초록: https://arxiv.org/abs/2202.12365
- 다운로드 상태: `already_exists`
#### Cycloidal Quasi-Direct Drive Actuator Designs with Learning-based Torque Estimation for Legged Robotics (2024)
- 저자: Alvin Zhu, Yusuke Tanaka, Fadi Rafeedi, Dennis Hong
- 왜 봐야 하는가: cycloidal QDD의 복잡한 drive dynamics와 torque estimation을 legged robotics 관점에서 다룬다.
- 모델링/구현 포인트: cycloidal gear actuator의 비선형/손실을 actuator network로 학습해 sim-to-real gap을 줄인다.
- 로컬 PDF: `pdfs/2410.16591_cycloidal_qdd_legged_robotics.pdf`
- 원문/초록: https://arxiv.org/abs/2410.16591
- 다운로드 상태: `already_exists`
#### Modeling and Application of Series Elastic Actuators for Force Control Multi Legged Robots (2009)
- 저자: Arumugom S., Muthuraman S., Ponselvan V.
- 왜 봐야 하는가: SEA를 multi-legged robot force control에 적용할 때의 기본 모델링 자료.
- 모델링/구현 포인트: gear train과 load 사이에 elastic element를 넣고, deflection sensor로 force/torque를 추정해 force loop를 닫는다.
- 로컬 PDF: `pdfs/0912.3956_sea_force_control_multi_legged_robots.pdf`
- 원문/초록: https://arxiv.org/abs/0912.3956
- 다운로드 상태: `already_exists`
#### Exploiting the Natural Dynamics of Series Elastic Robots by Actuator-Centered Sequential Linear Programming (2018)
- 저자: Rachel Schlossman, Gray C. Thomas, Orion Campbell, Luis Sentis
- 왜 봐야 하는가: SEA dynamics를 trajectory optimization 안에 효율적으로 넣는 방법.
- 모델링/구현 포인트: actuator dynamics를 robot dynamics에서 분리해 SLP 문제로 구성하고, compliance를 이용한 고성능 motion을 만든다.
- 로컬 PDF: `pdfs/1802.10190_sea_actuator_centered_slp.pdf`
- 원문/초록: https://arxiv.org/abs/1802.10190
- 다운로드 상태: `already_exists`
#### Performance Analysis of Series Elastic Actuator based on Maximum Torque Transmissibility (2019)
- 저자: Chan Lee, Sehoon Oh
- 왜 봐야 하는가: SEA를 transmission system으로 보고 motor torque/speed 한계가 출력 torque bandwidth를 어떻게 제한하는지 분석한다.
- 모델링/구현 포인트: Maximum Torque Transmissibility와 torque frequency bandwidth를 정의해 SEA 설계 변수와 controller 한계를 평가한다.
- 로컬 PDF: `pdfs/1902.05346_sea_maximum_torque_transmissibility.pdf`
- 원문/초록: https://arxiv.org/abs/1902.05346
- 다운로드 상태: `already_exists`

## 추가로 링크만 보관할 자료
- MuJoCo: A physics engine for model-based control, Todorov/Erez/Tassa, 2012. 원 논문/엔진은 legged robot contact simulation의 표준 배경 자료.
- Design Principles for Energy-Efficient Legged Locomotion and Implementation on the MIT Cheetah Robot, Seok et al., 2015. 공개 PDF를 자동으로 찾지는 못했지만 QDD/low-loss transmission 관점에서 중요.
- Proprioceptive Actuator Design in the MIT Cheetah, Wensing et al. 계열 자료. actuator/transmission design 배경으로 추가 확인 권장.

## 검색 키워드 기록
- `Control of Humanoid Robots with Parallel Mechanisms using Kinematic Actuation Models`
- `Cassie four-bar knee nonlinear transmission ratio`
- `closed-chain five-bar monoped actuator optimization gear ratio`
- `Hybrid Zero Dynamics biped walking simulation implementation`
- `legged robot contact simulation MuJoCo closed loop controller`
- `series elastic actuator maximum torque transmissibility legged robot`
