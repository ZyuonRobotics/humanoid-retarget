# humanoid-retargeting

[中文](README_zh.md)

**humanoid-retargeting** is a tool for retargeting human motion data (e.g., from BVH or SMPL) onto humanoid robots. It supports various motion file formats, provides alignment tools, and allows batch processing.

## Installation

It is recommended to use `conda` or `mamba` to manage the Python environment:

```bash
conda create -n humanoid-retargeting python=3.9
conda activate humanoid-retargeting
pip install -e .
```

If you need to use the GUI-based alignment tool, run:
```bash
pip install -e .[gui]
```

If you want to use the newest hurodes, run:
```bash
pip install git+https://github.com/ZyuonRobotics/humanoid-robot-description
```

### Main Dependencies

- Python >= 3.9
- `click`: Command-line interface
- `mujoco`: Physics simulation and visualization
- `dearpygui`: GUI-based alignment tool
- `hurodes`: Robot description and MJCF generation

---

## Data Path

The default path for storing data is:

```
~/.humanoid_retargeting
├── data
│   ├── smpl          # SMPL format motion capture data
│   ├── bvh           # BVH format motion capture data
│   └── ...           # Other types of motion capture data (e.g., bip, fbx)
├── models
│   ├── dmpls         # DMP pose library for SMPL-X model (optional)
│   └── smplh         # SMPL+H body model files
└── configs
    ├── unitree_g1     
    │   ├── smpl      # Retargeting configs for Unitree G1 robot using SMPL dataset
    │   └── bvh       # Retargeting configs for Unitree G1 robot using BVH dataset
    └── ...           # Other retargeting configuration configs
```

---

## Workflow Overview

The scripts are organized into three main categories based on their functionality:

```
scripts/
├── mocap_processing/          # Motion capture data preprocessing
├── mocap_retargeting/          # Motion retargeting to robots
└── retargeted_data_processing/ # Post-retargeting data processing
```

### 1. Motion Capture Data Processing

Scripts in `scripts/mocap_processing/` handle preprocessing of raw motion capture data before retargeting.

#### Check BVH Body Type

Scan BVH files in a folder and analyze their skeleton structures.

**Usage Example:**
```bash
python scripts/mocap_processing/check_bvh_bodytype_in_folder.py \
  --root-folder /path/to/bvh/folder
```

#### Fix SMPL Files

Check and fix SMPL format files (`.npz`), ensuring required fields like `mocap_framerate` are present.

**Usage Example:**
```bash
python scripts/mocap_processing/fix_smpl_file.py \
  --folder-path /path/to/smpl/files \
  --mocap-framerate 120
```

#### Process SMPL Files

Convert SMPL format files from `.pkl` to `.npz` format with standardized structure.

**Usage Example:**
```bash
python scripts/mocap_processing/process_smpl.py \
  --folder-path /path/to/pkl/files \
  --mocap-framerate 120
```

#### Play Mocap Motion

Play raw motion capture data (BVH or SMPL format) for visualization or debugging. Uses MuJoCo renderer to play action files.

You should use the appropriate player according to the `generator-type`. For example, set `generator-type` to `bvh` or `smpl` to play BVH format or SMPL format data respectively.

**Usage Example (Play BVH motion capture data):**
```bash
python scripts/mocap_processing/play_mocap_motion.py \
  /path/to/file.bvh \
  --generator-type bvh
```

**Usage Example (Play SMPL motion capture data):**
```bash
python scripts/mocap_processing/play_mocap_motion.py \
  /path/to/file.npz \
  --generator-type smpl
```

#### Batch Play / Generate Configs

Batch process motion files in a folder to generate config files. Supports BVH and SMPL formats. Can use a template config file and only recalculate `height_adjustment`, or generate configs from scratch with custom foot/hip offsets.

**Usage Example (Generate configs for all BVH files):**
```bash
python scripts/mocap_processing/batch_play.py \
  /path/to/bvh/folder \
  --generator-type bvh
```

**Usage Example (Use template config and only recalculate height_adjustment):**
```bash
python scripts/mocap_processing/batch_play.py \
  /path/to/bvh/folder \
  --generator-type bvh \
  --config-file /path/to/template_config.yaml \
  --draw-plot
```

**Options:**
- `--config-file`: Path to template config YAML file. Uses this config and only recalculates `height_adjustment`
- `--foot-offset`: Custom foot offset value (overrides config file if specified)
- `--hip-offset`: Custom hip offset value (overrides config file if specified)
- `--draw-plot`: Whether to draw analysis plots for height adjustment

### 2. Motion Retargeting

Scripts in `scripts/mocap_retargeting/` handle the core retargeting process, including alignment and motion transfer.

#### Alignment

Before retargeting, it's necessary to ensure that the robot and human model are aligned.

The **humanoid-retargeting** algorithm reads configuration files located in `~/.humanoid_retargeting/configs` for alignment. The fields used include:

- **Translation-related information**
  - `robot_foot`: Robot foot information, including left and right foot body names and offsets, ensuring the **robot's soles are exactly on the ground**
  - `human_foot`: Human model foot information, same data type as above
  - `base_x_shift`: **Human model's** X-axis offset relative to the robot
  - `base_y_shift`: **Human model's** Y-axis offset relative to the robot
- **Rotation-related information**
  - `base_rotation`: **Human model's** rotation relative to the robot (XYZ Euler angles)
  - `body_rotate_dict`: Rotations of each joint in the human model to align its posture with the robot
- **Scaling-related information**
  - `robot_hip`: Robot hip information, including body names and offsets for both hips, used to calculate **leg length** and thus global scale factor
  - `human_hip`: Human model hip information, same data type as above
  - `extra_body_ratio`: Additional global scaling factor for the human model, can be a single float or a 3D list for fine-tuning (e.g., making the human model wider)
  - `relative_body_ratio_dict`: Relative scale factors for each body part

##### Alignment Process

- **Compute Base Global Scale Factor**
  - Calculate leg lengths based on `foot` and `hip` positions for both robot and human model, then take their ratio as the global scale factor
  - Note: This factor will be used during retargeting to scale the motion capture data, preventing foot sliding
- Apply base global scale, extra scale, and relative body ratios to scale the human model
  - Each body part's final scale is determined by: `global_body_ratio * extra_body_ratio * relative_body_ratio_dict[body_name]`
- Translate the robot
  - Adjust the baselink vertically based on `robot_foot` so that the robot's feet are exactly on the ground
  - Only Z-axis changes; other adjustments are made via the human model
- Translate and rotate the human model
  - Move the human model's baselink so its feet are on the ground
  - Rotate the human model to match the robot's orientation
- Rotate human joints to match the robot's posture

##### Manual Alignment

Since repeated config tuning may be required for perfect alignment, you can repeatedly execute the alignment check script and modify the config file accordingly.

**Usage Example:**
```bash
python scripts/mocap_retargeting/check_align.py \
  /path/to/file.bvh \
  unitree_g1 \
  --generator-type bvh \
  --config-name default
```

##### Generate Retargeting Configs

Generate retargeting configs for a specific robot and motion capture data type.

**Usage Example:**
```bash
python scripts/mocap_retargeting/generate_retarget_config.py \
  /path/to/file.bvh \
  unitree_g1 \
  --generator-type bvh
```

##### Automatic Alignment (WIP)

Run a GUI-based auto-alignment tool that automatically saves retargeting configs to the configuration file.

#### Retargeting

Retargeting is implemented using the **mink** library. The main steps are:

- Based on the already aligned robot and human model, get the offset of tracking points
  - Offset includes relative position and rotation between trackers on the human model and the robot
  - Offset is entirely determined by the retargeting configs obtained in the previous stage; accuracy here greatly affects retargeting performance
- For each frame in the motion capture data:
  - Get current tracker positions on the human model
  - Combine static tracker offsets to compute desired robot tracker positions
  - Use mink library to solve inverse kinematics and obtain robot generalized coordinates

##### Single Motion Retargeting

Retarget a single motion file onto a specified robot. You can choose to open a viewer window to visualize the motion (rendered by MuJoCo), and loop playback.

**Usage Example:**
```bash
python scripts/mocap_retargeting/single_retarget.py \
  /path/to/file.bvh \
  unitree_g1 \
  --generator-type bvh \
  --config-name default \
  --view \
  --speed 1.0 \
  --offset 0.0 1.0 0.0
```

##### Batch Retargeting

Process multiple motion files in bulk and save them as `.npz` files. Supports multiprocessing for acceleration.

**Usage Example:**
```bash
python scripts/mocap_retargeting/batch_retarget.py \
  /path/to/motions \
  unitree_g1 \
  --generator-type bvh \
  --config-name default \
  --target-path /path/to/output \
  --target-fps 100 \
  --num-processes 4
```

Options:
- `--overwrite/--no-overwrite`: Whether to overwrite existing `.npz` files (default: no)
- `--pos-filter`, `--neg-filter`: Filter files by filename keywords (can be used multiple times)
- `--num-processes`: Number of CPU cores to use; set to 1 disables multiprocessing

### 3. Retargeted Data Processing

Scripts in `scripts/retargeted_data_processing/` handle visualization and playback of retargeted motion data.

#### Play Robot Motion

Play retargeted robot motion data (`.npz` format) for visualization or debugging. Uses MuJoCo renderer to play action files.

**Usage Example:**
```bash
python scripts/retargeted_data_processing/play_robot_motion.py \
  /path/to/retargeted.npz \
  unitree_g1
```

**Options:**
- `--plot-ref-trans`: Plot baselink Cartesian position (x, y, z)
- `--plot-ref-euler`: Plot baselink Euler angles (roll, pitch, yaw)
- `--plot-ref-joint-pos`: Plot reference joint positions
- `--plot-ref-joint-vel`: Plot reference joint velocities
- `--dims`: Comma-separated dimensions to plot for joint positions (e.g., "0,1,2")

#### Play Robot Period Motion

Generate and play periodic robot motion based on JSON configuration. This script generates sinusoidal motion patterns for robot joints based on stepping periods and joint configurations.

**Usage Example:**
```bash
python scripts/retargeted_data_processing/play_robot_period.py \
  --config-file-path /path/to/config.json \
  --robot-name unitree_g1 \
  --frame-rate 100 \
  --max-steps 300000
```

---

## Testing

To check test coverage, run:

```bash
pytest --cov=humanoid_retargeting --cov-report=html
```

Then open `htmlcov/index.html` in your browser to view the results.
