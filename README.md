# humanoid-retargeting

[中文](README_zh.md)

**humanoid-retargeting** is a tool for retargeting human motion data (e.g., from BVH or SMPL) onto humanoid robots. It supports various motion file formats, provides alignment tools, and allows batch processing.

## Installation

It is recommended to use `conda` or `mamba` to manage the Python environment:

```bash
conda create -n humanoid-retargeting python=3.10
conda activate humanoid-retargeting
pip install git+https://github.com/ZyuonRobotics/humanoid-robot-description
pip install -e .
```


If you need to use the GUI-based alignment tool, run:
```bash
pip install -e .[gui]
```


### Main Dependencies

- Python >= 3.10
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
└── parameters
    ├── unitree_g1     
    │   ├── smpl      # Retargeting parameters for Unitree G1 robot using SMPL dataset
    │   └── bvh       # Retargeting parameters for Unitree G1 robot using BVH dataset
    └── ...           # Other retargeting configuration parameters
```


---

## Workflow Overview

### Play Motion (Optional)

Allows playing motion sequences using selected player classes (e.g., `BVHPlayer`, `SMPLPlayer`) for visualization or debugging before retargeting. Uses MuJoCo renderer to play action files.

You should use the appropriate player according to the `generator-type`. For example, set `generator-type` to `bvh` or `smpl` to play BVH format or SMPL format data respectively.

**Example Usage (Play BVH motion data):**
```bash
python scripts/play_motion.py \
  --source-file-path /path/to/file.bvh \
  --generator-type bvh
```


### Alignment

Before retargeting, it's necessary to ensure that the robot and human model are aligned.

The **humanoid-retargeting** algorithm reads configuration files located in `~/.humanoid_retargeting/parameters` for alignment. The fields used include:

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

#### Alignment Process

- **Compute Base Global Scale Factor**
  - Calculate leg lengths based on `foot` and `hip` positions for both robot and human model, then take their ratio as the global scale factor
  - Note: This factor will be used during retargeting to scale the motion capture data, preventing foot sliding
- Apply base global scale, extra scale, and relative body ratios to scale the human model
  - Each body part’s final scale is determined by: `global_body_ratio * extra_body_ratio * relative_body_ratio_dict[body_name]`
- Translate the robot
  - Adjust the baselink vertically based on `robot_foot` so that the robot’s feet are exactly on the ground
  - Only Z-axis changes; other adjustments are made via the human model
- Translate and rotate the human model
  - Move the human model’s baselink so its feet are on the ground
  - Rotate the human model to match the robot's orientation
- Rotate human joints to match the robot's posture

#### Manual Alignment

Since repeated parameter tuning may be required for perfect alignment, you can repeatedly execute the script [scripts/check_align.py](file:///Users/frank/Projects/humanoid-retargeting/scripts/check_align.py) and modify the parameter file accordingly.

**Usage Example:**
```bash
python scripts/align.py \
  --bvh-file-path /path/to/file.bvh \
  --robot-name unitree_g1 \
  --generator-type bvh \
  --params-name default
```


#### Automatic Alignment (WIP)

Run a GUI-based auto-alignment tool that automatically saves retargeting parameters to the configuration file.

### Retargeting

Retargeting is implemented using the **mink** library. The main steps are:

- Based on the already aligned robot and human model, get the offset of tracking points
  - Offset includes relative position and rotation between trackers on the human model and the robot
  - Offset is entirely determined by the retargeting parameters obtained in the previous stage; accuracy here greatly affects retargeting performance
- For each frame in the motion capture data:
  - Get current tracker positions on the human model
  - Combine static tracker offsets to compute desired robot tracker positions
  - Use mink library to solve inverse kinematics and obtain robot generalized coordinates

#### Single Motion Retargeting

Retarget a single motion file onto a specified robot. You can choose to open a viewer window to visualize the motion (rendered by MuJoCo), and loop playback.

**Usage Example:**
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


#### Batch Retargeting

Process multiple motion files in bulk and save them as `.npy` files. Supports multiprocessing for acceleration.

**Usage Example:**
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


Options:
- `--overwrite/--no-overwrite`: Whether to overwrite existing `.npy` files (default: no)
- `--pos-filter`, `--neg-filter`: Filter files by filename keywords (can be used multiple times)
- `--num-processes`: Number of CPU cores to use; set to 1 disables multiprocessing

---

## Testing

To check test coverage, run:

```bash
pytest --cov=humanoid_retargeting --cov-report=html
```

Then open `htmlcov/index.html` in your browser to view the results.