# 人形机器人运动重定向

一个用于将人体动作捕捉数据重定向到人形机器人的 Python 库，使用逆运动学（IK）优化实现。

## 概述

该库提供了将人体运动数据（来自 SMPL 模型或 BVH 文件）转换为机器人可执行运动轨迹的工具。重定向过程包含两个主要步骤：**对齐（Alignment）** 和 **重定向（Retargeting）**。

## 模块结构

### 核心模块

#### `aligner.py` - 运动对齐
`Aligner` 类负责人体和机器人模型之间的初始对齐，通过计算缩放因子和跟踪器偏移量实现。

**主要功能：**
- **身体比例计算**：通过比较人体和机器人的腿长来计算全局缩放因子
  - 测量两个模型从髋部到脚部的距离
  - 计算比例：`global_body_ratio = 机器人腿长 / 人体腿长`
  
- **基座对齐**：对齐基座的位置和方向
  - 设置基座旋转（默认：BVH 为 [90, 0, 90]，SMPL 为 [0, 0, 0]）
  - 将双脚对齐到地面（Z 轴对齐）
  - 应用用户自定义的 XY 平移
  
- **跟踪器偏移计算**：计算对应的人体和机器人身体部位之间的位置和方向偏移
  - 对于每个跟踪器对（人体部位 → 机器人部位），计算 7 维偏移（3D 位置 + 4D 四元数）
  - 这些偏移用于在机器人模型上放置虚拟跟踪器

**对齐流程：**
1. 加载人体运动数据和机器人模型
2. 基于腿长计算全局身体比例
3. 缩放人体模型以匹配机器人比例
4. 应用基座旋转和平移
5. 计算每个身体部位对的跟踪器偏移

#### `retargeter.py` - 运动重定向
`Retargeter` 类使用逆运动学优化执行实际的运动重定向。

**关键组件：**
- **IK 求解器**：使用 `mink` 库，支持可配置的求解器（默认："daqp"）
- **任务（Tasks）**：定义优化目标
  - `PostureTask`：保持平滑的姿态过渡（代价：1.0）
  - `FrameTask`：跟踪每个身体部位的目标位置和方向
- **限制（Limits）**：强制执行物理约束
  - `ConfigurationLimit`：关节位置限制
  - `VelocityLimit`：关节速度限制（可选）
  - `CollisionAvoidanceLimit`：地面碰撞避免（可选）

**重定向算法：**

对于运动序列中的每一帧：

1. **设置目标姿态**：从人体运动中提取目标位置和方向
   ```
   对于每个跟踪器（手、脚、头等）：
     目标位置 = 人体部位位置
     目标方向 = 人体部位方向
   ```

2. **求解 IK 优化**：最小化目标函数
   ```
   最小化：Σ(位置代价 * ||机器人跟踪器位置 - 目标位置||² + 
           方向代价 * ||机器人跟踪器旋转 - 目标旋转||² +
           姿态代价 * ||q - q_prev||²)
   
   约束条件：
     - 关节位置限制：q_min ≤ q ≤ q_max
     - 关节速度限制：|dq/dt| ≤ v_max
     - 碰撞避免：distance(机器人, 地面) > 阈值
   ```

3. **积分速度**：更新机器人配置
   ```
   q(t+1) = q(t) + v * dt
   ```

4. **存储结果**：保存关节位置和速度

**特殊处理：**
- 第一帧：运行 `init_frame_loop_num` 次迭代（默认：100）以找到良好的初始姿态
- 后续帧：单次迭代，使用前一帧作为初始化

**输出格式：**
- NPZ 格式：包含根部平移、旋转（四元数）、关节位置、速度和帧率
- CSV 格式：连接的 qpos 和 qvel 数组

### 支持模块

#### `mjcf_generator/` - MJCF 模型生成
将人体运动数据和机器人模型转换为 MuJoCo XML 格式。

- `smpl2mjcf_generator.py`：将 SMPL 模型转换为 MJCF
- `bvh2mjcf_generator.py`：将 BVH 文件转换为 MJCF
- `tracker_generator.py`：在机器人模型上生成虚拟跟踪器站点
- `body_tree.py`：构建层次化的身体树结构
- `retargeting_generator_base.py`：MJCF 生成器的基类

#### `motion_player/` - 运动回放
处理运动数据的加载和回放。

- `smpl_player.py`：播放 SMPL 运动数据
- `bvh_player.py`：播放 BVH 运动数据
- `robot_motion_player.py`：播放重定向后的机器人运动
- `robot_peroid_player.py`：播放周期性机器人运动
- `humanoid_player_base.py`：人形运动播放器的基类
- `player_base.py`：所有播放器的抽象基类

#### `utils/` - 工具函数
辅助函数和配置类。

- `retarget_config.py`：重定向参数的配置类
  - `TrackerConfig`：定义跟踪器对和优化代价
  - `RetargetConfig`：完整的重定向配置
- `human_config.py`：人体模型配置（髋部/脚部名称和偏移）
- `rot.py`：旋转工具（欧拉角、四元数）
- `lowpass.py`：用于运动平滑的低通滤波
- `plot.py`：可视化工具

## 配置

### RetargetConfig
重定向的主要配置类：

```yaml
base_x_shift: 0.0          # 人体模型的 X 轴平移
base_y_shift: 0.0          # 人体模型的 Y 轴平移
base_rotation: [0, 0, 0]   # 基座旋转的欧拉角
body_rotate_dict: {}       # 每个身体部位的旋转调整
extra_body_ratio: [1, 1, 1] # 额外的缩放因子（X, Y, Z）
relative_body_ratio_dict: {} # 每个身体部位的缩放调整
damping_cost: 5.0          # IK 求解器阻尼

tracker_dict:              # 跟踪器定义
  hands:
    human: [left_hand, right_hand]
    robot: [left_hand, right_hand]
    position_cost: 100.0
    orientation_cost: 10.0
  feet:
    human: [left_foot, right_foot]
    robot: [left_foot, right_foot]
    position_cost: 100.0
    orientation_cost: 10.0
```

### HumanConfig
人体模型配置（作为 `.yaml` 文件存储在运动文件旁边）：

```yaml
hip_names: [left_hip, right_hip]
foot_names: [left_foot, right_foot]
hip_offset: 0.0    # 从髋关节到测量点的垂直偏移
foot_offset: 0.0   # 从脚关节到地面接触点的垂直偏移
```

## 使用示例

```python
from humanoid_retargeting import Retargeter

# 初始化重定向器
retargeter = Retargeter(
    source_file_path="path/to/motion.npz",
    robot_name="DumBot13-21dof",
    generator_type="smpl",
    config_name="default",
    view=True,
    solver="daqp",
    init_frame_loop_num=100
)

# 运行重定向
retargeter.run_ik(progress_bar=True)

# 保存结果
retargeter.save_as_npz("output.npz", target_framerate=100)

# 播放运动
retargeter.play(speed=1.0, loop=True)
```

## 依赖项

- `mujoco`：物理仿真和可视化
- `mink`：逆运动学求解器
- `numpy`：数值计算
- `scipy`：插值和旋转工具
- `hurodes`：人形机器人描述系统
- `tqdm`：进度条

## 技术细节

### 坐标系
- 人体模型：SMPL 通常为 Y-up，BVH 为 Z-up
- 机器人模型：Z-up（MuJoCo 约定）
- 四元数顺序：[w, x, y, z]

### 优化
- 求解器：默认使用 DAQP（双主动集 QP 求解器）
- 时间步长：1 / 帧率
- 阻尼：可配置（默认：0.1）

### 性能
- 第一帧：约 100 次迭代用于初始化
- 后续帧：每帧 1 次迭代
- 典型处理速度：对于 30-60 FPS 的运动数据，可达到实时或更快

## 算法详解

### 对齐（Alignment）过程

对齐是重定向的第一步，目的是建立人体和机器人之间的对应关系：

1. **腿长测量**
   - 人体腿长 = ||髋部中心 - 脚部中心|| + 髋部偏移 - 脚部偏移
   - 机器人腿长 = ||髋部中心 - 脚部中心|| + 髋部偏移 - 脚部偏移

2. **全局缩放**
   - 计算比例因子使人体和机器人的腿长匹配
   - 应用到人体模型的所有尺寸

3. **基座对齐**
   - 旋转：将人体模型旋转到与机器人相同的朝向
   - 平移：将双脚对齐到地面（Z=0）
   - 偏移：应用用户定义的 XY 平移以避免重叠

4. **跟踪器偏移**
   - 对于每个跟踪器对，计算人体部位相对于机器人部位的偏移
   - 这些偏移用于在 IK 优化中设置目标位置

### 重定向（Retargeting）过程

重定向使用基于优化的逆运动学方法：

1. **目标设定**
   - 从人体运动中读取每个跟踪器的位置和方向
   - 这些成为机器人需要达到的目标

2. **优化问题**
   ```
   决策变量：关节速度 v
   
   目标函数：
     J = Σ w_pos * ||p_robot - p_target||²        # 位置误差
       + Σ w_ori * ||R_robot - R_target||²        # 方向误差
       + w_posture * ||q - q_prev||²              # 姿态平滑
   
   约束：
     - q_min ≤ q + v*dt ≤ q_max                   # 关节限制
     - |v| ≤ v_max                                # 速度限制
     - distance(robot, ground) > d_safe           # 碰撞避免
   ```

3. **求解方法**
   - 使用二次规划（QP）求解器
   - DAQP 求解器：快速、鲁棒的主动集方法
   - 每帧求解时间：通常 < 10ms

4. **时间积分**
   - 使用欧拉积分更新关节位置
   - q(t+1) = q(t) + v * dt
   - 保持速度连续性

### 关键参数说明

- **position_cost**：位置跟踪的权重，值越大越精确跟踪位置
- **orientation_cost**：方向跟踪的权重，值越大越精确跟踪方向
- **posture_cost**：姿态平滑的权重，值越大运动越平滑但可能牺牲精度
- **damping**：数值阻尼，提高求解稳定性
- **init_frame_loop_num**：第一帧的迭代次数，更多迭代可以找到更好的初始姿态
