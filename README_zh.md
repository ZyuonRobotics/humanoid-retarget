# humanoid-retargeting

[English](README.md)

**humanoid-retargeting** 是一个将人类动作数据（例如来自 BVH 或 SMPL 的动作）重新定向到人形机器人上的工具。它支持多种类型的运动文件，提供对齐工具，并允许批量处理。

## 安装

推荐使用 `conda` 或 `mamba` 来管理 Python 环境：

```bash
conda create -n humanoid-retargeting python=3.9
conda activate humanoid-retargeting
pip install -e .
```

如果需要使用图形化工具进行对齐，请执行下面的命令：
```bash
pip install -e .[gui]
```

如果需要使用最新版本的 hurodes，请执行：
```bash
pip install git+https://github.com/ZyuonRobotics/humanoid-robot-description
```

### 主要依赖项

- Python >= 3.9
- `click`: 命令行接口
- `mujoco`: 物理仿真和可视化
- `dearpygui`: 基于GUI的对齐工具
- `hurodes`: 机器人描述和 MJCF 生成

---

## 数据路径

默认用于存储数据的路径为：

```
~/.humanoid_retargeting
├── data
│   ├── smpl          # SMPL格式的动捕数据
│   ├── bvh           # BVH格式的动捕数据
│   └── ...           # 其他种类的动捕数据 (例如bip，fbx等)
├── models
│   ├── dmpls         # SMPL-X模型的DMP姿态库（可选）
│   └── smplh         # SMPL+H身体模型文件
└── parameters
    ├── unitree_g1     
    │   ├── smpl      # unitree g1机器人在SMPL数据集中使用的重定向参数
    │   └── bvh       # unitree g1机器人在BVH数据集中的重定向参数
    └── ...           # 其他重定向配置参数
```

---

## 工作流程概述

脚本根据功能分为三个主要类别：

```
scripts/
├── mocap_processing/          # 动捕数据预处理
├── mocap_retargeting/          # 动作重定向到机器人
└── retargeted_data_processing/ # 重定向后的数据处理
```

### 1. 动捕数据处理

`scripts/mocap_processing/` 中的脚本处理重定向前的原始动捕数据预处理。

#### 检查 BVH 骨架类型

扫描文件夹中的 BVH 文件并分析其骨架结构。

**使用示例：**
```bash
python scripts/mocap_processing/check_bvh_bodytype_in_folder.py \
  --root-folder /path/to/bvh/folder
```

#### 修复 SMPL 文件

检查并修复 SMPL 格式文件（`.npz`），确保包含 `mocap_framerate` 等必需字段。

**使用示例：**
```bash
python scripts/mocap_processing/fix_smpl_file.py \
  --folder-path /path/to/smpl/files \
  --mocap-framerate 120
```

#### 处理 SMPL 文件

将 SMPL 格式文件从 `.pkl` 转换为 `.npz` 格式，并标准化结构。

**使用示例：**
```bash
python scripts/mocap_processing/process_smpl.py \
  --folder-path /path/to/pkl/files \
  --mocap-framerate 120
```

#### 播放动捕动作

播放原始动捕数据（BVH 或 SMPL 格式），用于可视化或调试。使用 MuJoCo 渲染器播放动作文件。

需要根据 `generator-type` 使用合适的播放器。例如，设置 `generator-type` 为 `bvh` 或 `smpl`，分别用于播放 BVH 格式或 SMPL 格式的数据。

**使用示例（播放 BVH 动捕数据）：**
```bash
python scripts/mocap_processing/play_mocap_motion.py \
  /path/to/file.bvh \
  --generator-type bvh
```

**使用示例（播放 SMPL 动捕数据）：**
```bash
python scripts/mocap_processing/play_mocap_motion.py \
  /path/to/file.npz \
  --generator-type smpl
```

### 2. 动作重定向

`scripts/mocap_retargeting/` 中的脚本处理核心重定向流程，包括对齐和动作转移。

#### 对齐

在进行重定向之前需要保证机器人和人体模型对齐。

**humanoid-retargeting** 算法通过读取位于 `~/.humanoid_retargeting/parameters` 文件夹下的配置文件用于对齐，用于对齐的字段包括：

- **平移相关信息**
  - `robot_foot`: 机器人的脚部信息，包含左右脚对应的body名称和脚部偏移值，用于确保机器人的**脚底正好在地面上**
  - `human_foot`: 人体模型的脚信息，数据类型与前者相同
  - `base_x_shift`: **人体模型**相对于机器人的X轴偏移量
  - `base_y_shift`: **人体模型**相对于机器人的Y轴偏移量
- **旋转相关信息**
  - `base_rotation`: **人体模型**相对于机器人的旋转角度（XYZ欧拉角）
  - `body_rotate_dict`: **人体模型**各个关节的旋转角度，用于确保人体模型的姿态与机器人一致
- **缩放相关信息**
  - `robot_hip`: 机器人的髋部信息，包含左右髋对应的body名称和髋部偏移值，用于获取**腿部长度**从而计算全局缩放因子
  - `human_hip`: 人体模型的髋部信息，数据类型与前者相同
  - `extra_body_ratio`: 附加的人体模型缩放因子，可以是单个浮点数或三维列表，用于在全局缩放因子的基础上微调（例如让人体模型更宽）
  - `relative_body_ratio_dict`: 人体模型各个body的相对缩放因子

##### 对齐流程

- **计算基础全局缩放因子**
  - 通过机器人和人体模型各自的`foot`和`hip`位置来计算两者分别的腿部长度，将腿部长度的比值作为全局缩放因子
  - 注意：在重定向阶段，将会使用该因子对动捕数据进行缩放，从而保证动作不会出现在地面上滑动的情况
- 应用基础全局缩放、附加缩放和各身体部位的相对缩放因子，对人体模型进行缩放
  - 每个身体部位的最终缩放比例由以下公式决定：`global_body_ratio * extra_body_ratio * relative_body_ratio_dict[body_name]`
- 平移机器人
  - 根据机器人的`foot`信息对baselink进行垂直平移，使其脚底正好在地面上
  - 只更改Z轴高度；其他调整通过人体模型进行
- 平移并旋转人体模型
  - 根据人体模型的`foot`信息对baselink进行平移，使其脚底正好在地面上
  - 旋转人体模型，使其位置与机器人一致
- 旋转人体模型关节，使其姿态与机器人一致

##### 手动对齐

由于需要反复调节重定向参数才能达到完美的对齐效果，可以多次执行对齐检查脚本并修改参数文件实现手动对齐。

**使用示例：**
```bash
python scripts/mocap_retargeting/check_align.py \
  /path/to/file.bvh \
  unitree_g1 \
  --generator-type bvh \
  --params-name default
```

##### 生成重定向参数

为特定机器人和动捕数据类型生成重定向参数。

**使用示例：**
```bash
python scripts/mocap_retargeting/generate_retarget_params.py \
  /path/to/file.bvh \
  unitree_g1 \
  --generator-type bvh \
```

##### 自动对齐（待完善）

执行具有图形化界面的自动对齐工具，自动将重定向参数保存到配置文件中。

#### 重定向

重定向通过 **mink** 库实现，主要流程如下：

- 基于已经对齐的机器人和人体模型，获取追踪点（tracker）的偏移量
  - 偏移量包括追踪点在人体模型和机器人上的相对位置和相对旋转
  - 偏移量完全由上一阶段得到的重定向参数决定，其准确性对重定向的效果产生至关重要的影响
- 对动捕数据集中的每一帧分别重定向，执行如下过程：
  - 获取人体模型当前动作下的各个追踪点位置
  - 结合静态的追踪点偏移量，计算出期望的机器人追踪点位置
  - 调用mink库执行逆运动学，获取机器人广义坐标

##### 单个动作重定向

将单个动作文件重定向到指定的机器人上，可以选择打开视频窗口查看动作（由mujoco viewer渲染），并循环播放。

**使用示例：**
```bash
python scripts/mocap_retargeting/single_retarget.py \
  /path/to/file.bvh \
  unitree_g1 \
  --generator-type bvh \
  --params-name default \
  --view \
  --speed 1.0 \
  --offset 0.0 1.0 0.0
```

##### 批量重定向

批量处理多个动作文件，并将其保存为 `.npz` 格式，支持多进程并行加速。

**使用示例：**
```bash
python scripts/mocap_retargeting/batch_retarget.py \
  /path/to/motions \
  unitree_g1 \
  --generator-type bvh \
  --params-name default \
  --target-path /path/to/output \
  --target-fps 100 \
  --num-processes 4
```

选项说明：
- `--overwrite/--no-overwrite`: 是否覆盖已有的 `.npz` 文件（默认为否）
- `--pos-filter`, `--neg-filter`: 根据文件名关键字过滤文件（可多次使用）
- `--num-processes`: 使用的 CPU 核心数，设为 1 表示禁用多进程

### 3. 重定向后的数据处理

`scripts/retargeted_data_processing/` 中的脚本处理重定向后动作数据的可视化和播放。

#### 播放机器人动作

播放重定向后的机器人动作数据（`.npz` 格式），用于可视化或调试。使用 MuJoCo 渲染器播放动作文件。

**使用示例：**
```bash
python scripts/retargeted_data_processing/play_robot_motion.py \
  /path/to/retargeted.npz \
  unitree_g1
```

#### 播放机器人周期动作

基于 JSON 配置生成并播放周期性机器人动作。该脚本根据步态周期和关节配置生成机器人关节的正弦运动模式。

**使用示例：**
```bash
python scripts/retargeted_data_processing/play_robot_period.py \
  --config-file-path /path/to/config.json \
  --robot-name unitree_g1 \
  --frame-rate 100 \
  --max-steps 300000
```

---

## 测试

要查看测试覆盖率，请运行：

```bash
pytest --cov=humanoid_retargeting --cov-report=html
```

然后在浏览器中打开 `htmlcov/index.html` 查看结果。
