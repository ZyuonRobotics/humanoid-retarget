# humanoid-retargeting

**humanoid-retargeting** 是一个将人类动作数据（例如来自 BVH 或 AMASS 的动作）重新定向到人形机器人上的工具。它支持多种类型的运动文件，提供对齐工具，并允许批量处理。

## 安装

推荐使用 `conda` 或 `mamba` 来管理 Python 环境：

```bash
conda create -n humanoid-retargeting python=3.10
conda activate humanoid-retargeting
pip install git+https://github.com/ZyuonRobotics/humanoid-robot-description
pip install -e .
```

如果需要使用图形化工具进行对齐，请执行下面的命令：
```bash
pip install -e .[gui]
```

### 主要依赖项

- Python >= 3.10
- `click`: 命令行接口
- `mujoco`: 物理仿真和可视化
- `dearpygui`: 基于GUI的对齐工具
- `hurodes`: 机器人描述和 MJCF 生成

---

## 数据准备

默认用于存储数据的路径为：

```
~/.humanoid_retargeting
├── data
│   ├── amass         # AMASS数据集中的动捕数据
│   ├── bvh           # bvh格式的动捕数据
│   └── ...           # 其他种类的动捕数据 (例如bip，fbx等)
├── models
│   ├── dmpls         # SMPL-X模型的DMP姿态库（可选）
│   └── smplh         # SMPL+H身体模型文件
└── parameters
    ├── unitree_g1     
    │   ├── amass     # unitree g1机器人在AMASS数据集中使用的重定向参数
    │   └── bvh       # unitree g1机器人在bvh数据集中的重定向参数
    └── ...           # 其他重定向配置参数
```

---

## 流程概述

### 播放动作（可选）

允许使用选定的动作播放器类（如 `BVHPlayer`, `AMASSPlayer`）来播放动作序列，可以用于在重定向之前可视化或调试动作。使用mujoco渲染动作文件。

需要根据 `generator-type` 使用合适的播放器播放动作文件，例如设置 `generator-type`为`bvh`或者`smpl`，分别用于播放bvh格式的数据或者smpl格式的数据。

**使用示例（播放bvh格式的动捕数据）：**
```bash
python scripts/play_motion.py \
  --source-file-path /path/to/file.bvh \
  --generator-type bvh
```

### 对齐
在进行重定向之前需要保证机器人和人体模型对齐。

humanoid-retargeting算法库通过读取位于`~/.humanoid_retargeting/parameters`文件夹下的配置文件用于对齐，用于对齐的字段包括：
- 用于平移的信息
  - `robot_foot`: 机器人的脚部信息，包含左右脚对应的body名称和脚部偏移值，用于确保机器人的**脚底正好在地面上**
  - `human_foot`: 人体模型的脚信息，数据类型与前者相同
  - `base_x_shift`: **人体模型**相对于机器人的X轴偏移量
  - `base_y_shift`: **人体模型**相对于机器人的Y轴偏移量
- 用于旋转的信息
  - `base_rotation`: **人体模型**相对于机器人的旋转角度（xyz欧拉角）
  - `body_rotate_dict`: **人体模型**各个关节的旋转角度，用于确保人体模型的姿态与机器人一致
- 用于缩放的信息
  - `robot_hip`: 机器人的髋部信息，包含左右髋对应的body名称和髋部偏移值，用于获取**腿部长度**从而计算全局缩放因子
  - `human_hip`: 人体模型的髋部信息，数据类型与前者相同
  - `extra_body_ratio`: 附加的人体模型缩放因子，可以是单个浮点数或三维列表，用于在全局缩放因子的基础上微调（例如让人体模型更宽）
  - `relative_body_ratio_dict`: 人体模型各个body的相对缩放因子

对齐程序的执行过程如下：
- 获取**基础全局缩放因子**
  - 通过机器人和人体模型各自的`foot`和`hip`位置来计算两者分别的腿部长度，将腿部长度的比值作为全局身体比例
  - 注意：在重定向阶段，将会使用该因子对动捕数据进行缩放，从而保证动作不会出现在地面上滑动的情况
- 使用基础全局缩放因子、附加全局缩放因子以及各身体部位的相对缩放因子，对人体模型进行缩放
  - 每个身体部位的最终缩放比例由以下公式决定：`global_body_ratio * extra_body_ratio * relative_body_ratio_dict[body_name]`
- 平移机器人
  - 根据机器人的`foot`信息对baselink进行平移，使其脚底正好在地面上
  - 只更改机器人的z轴高度，不做任何其他操作，通过调整人体模型的位置使两者对齐
- 平移并旋转人体模型
  - 根据人体模型的`foot`信息对baselink进行平移，使其脚底正好在地面上
  - 旋转人体模型，使其位置与机器人一致
- 旋转人体模型关节，使其姿态与机器人一致

#### 手动对齐
由于需要反复调节重定向参数才能达到完美的对齐效果，可以多次执行脚本`scripts/check_align.py`并修改参数文件实现手动对齐。

**使用示例：**
```bash
python scripts/align.py \
  --bvh-file-path /path/to/file.bvh \
  --robot-name unitree_g1 \
  --generator-type bvh \
  --params-name default
```
#### 自动对齐（待完善）
执行具有图形化界面的自动对齐工具，自动将重定向参数保存到配置文件中。

### 重定向
重定向通过mink库实现，主要流程如下：
- 基于已经对齐的机器人和人体模型，获取追踪点（tracker）的偏移量
  - 即同一个追踪点在人体模型和机器人上的相对位置和相对旋转
  - 偏移量完全由上一阶段得到的重定向参数决定，其准确性对重定向的效果产生至关重要的影响
- 对动捕数据集中的每一帧分别重定向，执行如下过程：
  - 获取人体模型当前动作下的各个追踪点位置
  - 结合静态的追踪点偏移量，计算出期望的机器人追踪点位置
  - 调用mink库执行逆运动学，获取机器人广义坐标


#### 单个动作文件重定向
将单个动作文件重定向到指定的机器人上，可以选择打开视频窗口查看动作（由mujoco viewer渲染），并循环播放。

**使用示例：**
```bash
python scripts/single_retarget.py \
  --source-file-path /path/to/file.bvh \
  --robot-name unitree_g1 \
  --generator-type bvh \
  --params-name default \
  --view \
  --speed 1.0 \
  --offset 0.0 0.0 0.0
```
#### 批量重定向

批量处理多个动作文件，并将其保存为 `.npy` 格式，支持多进程并行加速。

**使用示例：**
```bash
python scripts/batch_retarget.py \
  --source-path /path/to/motions \
  --target-path /path/to/output \
  --robot-name unitree_g1 \
  --generator-type bvh \
  --params-name default \
  --target-fps 100 \
  --num-processes 4
```

选项说明：
- `--overwrite/--no-overwrite`: 是否覆盖已有的 `.npy` 文件（默认为否）
- `--pos-filter`, `--neg-filter`: 根据文件名关键字过滤文件（可多次使用）
- `--num-processes`: 使用的 CPU 核心数，设为 1 表示禁用多进程

---

## 测试（Testing）

要查看测试覆盖率，请运行：

```bash
pytest --cov=humanoid_retargeting --cov-report=html
```


然后在浏览器中打开`htmlcov/index.html`查看结果。
