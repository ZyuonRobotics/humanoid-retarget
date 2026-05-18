# Humanoid Retargeting

A Python library for retargeting human motion capture data to humanoid robots using inverse kinematics (IK) optimization.

## Overview

This library provides tools to convert human motion data (from SMPL models or BVH files) into robot-executable motion trajectories. The retargeting process involves two main steps: **alignment** and **retargeting**.

## Module Structure

### Core Modules

#### `aligner.py` - Motion Alignment
The `Aligner` class handles the initial alignment between human and robot models by computing scaling factors and tracker offsets.

**Key Functions:**
- **Body Ratio Calculation**: Computes the global scaling factor by comparing leg lengths between human and robot
  - Measures distance from hip to foot for both models
  - Calculates ratio: `global_body_ratio = robot_leg_length / human_leg_length`
  
- **Base Alignment**: Aligns the base positions and orientations
  - Sets base rotation (default: [90, 0, 90] for BVH, [0, 0, 0] for SMPL)
  - Aligns feet to ground (Z-axis alignment)
  - Applies user-defined XY shifts
  
- **Tracker Offset Computation**: Calculates position and orientation offsets between corresponding human and robot body parts
  - For each tracker pair (human body → robot body), computes the 7D offset (3D position + 4D quaternion)
  - These offsets are used to place virtual trackers on the robot model

**Alignment Process:**
1. Load human motion data and robot model
2. Calculate global body ratio based on leg lengths
3. Scale human model to match robot proportions
4. Apply base rotation and translation
5. Compute tracker offsets for each body part pair

#### `retargeter.py` - Motion Retargeting
The `Retargeter` class performs the actual motion retargeting using inverse kinematics optimization.

**Key Components:**
- **IK Solver**: Uses the `mink` library with configurable solvers (default: "daqp")
- **Tasks**: Defines optimization objectives
  - `PostureTask`: Maintains smooth posture transitions (cost: 1.0)
  - `FrameTask`: Tracks target positions and orientations for each body part
- **Limits**: Enforces physical constraints
  - `ConfigurationLimit`: Joint position limits
  - `VelocityLimit`: Joint velocity limits (optional)
  - `CollisionAvoidanceLimit`: Ground collision avoidance (optional)

**Retargeting Algorithm:**

For each frame in the motion sequence:

1. **Set Target Poses**: Extract target positions and orientations from human motion
   ```
   For each tracker (hand, foot, head, etc.):
     target_position = human_body_position
     target_orientation = human_body_orientation
   ```

2. **Solve IK Optimization**: Minimize the objective function
   ```
   minimize: Σ(position_cost * ||robot_tracker_pos - target_pos||² + 
             orientation_cost * ||robot_tracker_rot - target_rot||² +
             posture_cost * ||q - q_prev||²)
   
   subject to:
     - Joint position limits: q_min ≤ q ≤ q_max
     - Joint velocity limits: |dq/dt| ≤ v_max
     - Collision avoidance: distance(robot, ground) > threshold
   ```

3. **Integrate Velocity**: Update robot configuration
   ```
   q(t+1) = q(t) + v * dt
   ```

4. **Store Result**: Save joint positions and velocities

**Special Handling:**
- First frame: Runs optimization for `init_frame_loop_num` iterations (default: 100) to find a good initial pose
- Subsequent frames: Single iteration, using previous frame as initialization

**Output Formats:**
- NPZ format: Includes root translation, rotation (quaternion), joint positions, velocities, and frame rate
- CSV format: Concatenated qpos and qvel arrays

### Supporting Modules

#### `mjcf_generator/` - MJCF Model Generation
Converts human motion data and robot models into MuJoCo XML format.

- `smpl2mjcf_generator.py`: Converts SMPL models to MJCF
- `bvh2mjcf_generator.py`: Converts BVH files to MJCF
- `tracker_generator.py`: Generates virtual tracker sites on robot model
- `body_tree.py`: Builds hierarchical body tree structures
- `retargeting_generator_base.py`: Base class for MJCF generators

#### `motion_player/` - Motion Playback
Handles loading and playing back motion data.

- `smpl_player.py`: Plays SMPL motion data
- `bvh_player.py`: Plays BVH motion data
- `robot_motion_player.py`: Plays retargeted robot motion
- `robot_peroid_player.py`: Plays periodic robot motion
- `humanoid_player_base.py`: Base class for humanoid motion players
- `player_base.py`: Abstract base class for all players

#### `utils/` - Utility Functions
Helper functions and configuration classes.

- `retarget_config.py`: Configuration classes for retargeting parameters
  - `TrackerConfig`: Defines tracker pairs and optimization costs
  - `RetargetConfig`: Complete retargeting configuration
- `human_config.py`: Human model configuration (hip/foot names and offsets)
- `rot.py`: Rotation utilities (Euler angles, quaternions)
- `lowpass.py`: Low-pass filtering for motion smoothing
- `plot.py`: Visualization utilities

## Configuration

### RetargetConfig
Main configuration class for retargeting:

```yaml
base_x_shift: 0.0          # X-axis shift for human model
base_y_shift: 0.0          # Y-axis shift for human model
base_rotation: [0, 0, 0]   # Euler angles for base rotation
body_rotate_dict: {}       # Per-body rotation adjustments
extra_body_ratio: [1, 1, 1] # Additional scaling factors (X, Y, Z)
relative_body_ratio_dict: {} # Per-body scaling adjustments
damping_cost: 5.0          # IK solver damping

tracker_dict:              # Tracker definitions
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
Human model configuration (stored as `.yaml` alongside motion files):

```yaml
hip_names: [left_hip, right_hip]
foot_names: [left_foot, right_foot]
hip_offset: 0.0    # Vertical offset from hip joint to measurement point
foot_offset: 0.0   # Vertical offset from foot joint to ground contact
```

## Usage Example

```python
from humanoid_retargeting import Retargeter

# Initialize retargeter
retargeter = Retargeter(
    source_file_path="path/to/motion.npz",
    robot_name="DumBot13-21dof",
    generator_type="smpl",
    config_name="default",
    view=True,
    solver="daqp",
    init_frame_loop_num=100
)

# Run retargeting
retargeter.run_ik(progress_bar=True)

# Save results
retargeter.save_as_npz("output.npz", target_framerate=100)

# Play back motion
retargeter.play(speed=1.0, loop=True)
```

## Dependencies

- `mujoco`: Physics simulation and visualization
- `mink`: Inverse kinematics solver
- `numpy`: Numerical computations
- `scipy`: Interpolation and rotation utilities
- `hurodes`: Humanoid robot description system
- `tqdm`: Progress bars

## Technical Details

### Coordinate Systems
- Human model: Typically Y-up for SMPL, Z-up for BVH
- Robot model: Z-up (MuJoCo convention)
- Quaternion order: [w, x, y, z]

### Optimization
- Solver: DAQP (Dual Active-set QP solver) by default
- Time step: 1 / frame_rate
- Damping: Configurable (default: 0.1)

### Performance
- First frame: ~100 iterations for initialization
- Subsequent frames: 1 iteration per frame
- Typical processing: Real-time or faster for 30-60 FPS motion data
