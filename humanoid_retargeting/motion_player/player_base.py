import time
from abc import ABC, abstractmethod

import numpy as np
import mujoco
import mujoco.viewer
from scipy.spatial.transform import Rotation
from hurodes.generators import MJCFGeneratorBase
import matplotlib.pyplot as plt

from humanoid_retargeting.utils.plot import plot2d


class MotionPlayerBase(ABC):
    generator_class = MJCFGeneratorBase
    file_suffix = ""

    def __init__(self, view=True):
        self.view = view

        self.generator: MJCFGeneratorBase = None
        self.create_generator()
        assert isinstance(self.generator, self.generator_class), "Generator is not of the correct type"

        self._viewer = None
        self._frame_rate: int = None
        self._ref_qpos: np.ndarray = None

        self._model = None
        self._data = None

        self.motion_data = None

        self._loaded = False


    def load(self, **kwargs):
        self._load(**kwargs)
        self.generator.load(**kwargs)
        self._loaded = True

    @classmethod
    def from_source_file_path(cls, source_file_path, **kwargs):
        player = cls(**kwargs)
        player.load(source_file_path=source_file_path)
        return player

    @property
    def model(self):
        assert self.generator is not None and self.generator.loaded, "Generator is not loaded"
        if self._model is None:
            self.generator.generate() # call generate() lazily, because it should not be called in load()
            self._model = mujoco.MjModel.from_xml_string(self.generator.xml_str) # type: ignore
        return self._model
    
    @property
    def data(self):
        assert self.generator is not None and self.generator.loaded, "Generator is not loaded"
        if self._data is None:
            self._data = mujoco.MjData(self.model) # type: ignore
        return self._data

    @abstractmethod
    def _load(self, **kwargs):
        raise NotImplementedError()

    @abstractmethod
    def create_generator(self):
        raise NotImplementedError()

    @property
    def viewer(self):
        assert self._loaded, "Motion player is not loaded"
        assert self.view, "Viewer is not enabled"
        if self._viewer is None:
            self._viewer = mujoco.viewer.launch_passive(self.model, self.data)
        return self._viewer

    @property
    def ref_qpos(self) -> np.ndarray:
        assert self._loaded, "Motion player is not loaded"
        if self._ref_qpos is None:
            self.load()
        assert isinstance(self._ref_qpos, np.ndarray), "Reference qpos is not loaded"
        return self._ref_qpos

    @property
    def frame_rate(self) -> int:
        assert self._loaded, "Motion player is not loaded"
        if self._frame_rate is None:
            self.load_motion_file()
            assert isinstance(self._frame_rate, int), "Frame rate is not loaded"
        return self._frame_rate

    @property
    def frame_num(self):
        assert self._loaded, "Motion player is not loaded"
        return self.ref_qpos.shape[0]

    def sync_data(self, frame_idx):
        self.data.qpos[:] = self.ref_qpos[frame_idx]
        self.data.qvel[:] = 0
        mujoco.mj_forward(self.model, self.data) # type: ignore

    def render(self):
        assert self._loaded, "Motion player is not loaded"
        assert self.view, "Viewer is not enabled"

        for frame_idx in range(self.frame_num):
            step_start = time.time()

            self.sync_data(frame_idx)
            self.viewer.sync()

            time_until_next_step = 1 / self.frame_rate - (time.time() - step_start)
            if time_until_next_step > 0:
                time.sleep(time_until_next_step)

        self.close()

    def plot_ref_baselink_cartesian(self):
        plot2d(self.ref_qpos[:, :3], ["x", "y", "z"], view=self.view)

    def plot_ref_baselink_quaternion(self):
        plot2d(self.ref_qpos[:, 3:7], ["w", "x", "y", "z"], view=self.view)

    def plot_ref_baselink_euler(self):
        euler_pos = Rotation.from_quat(self.ref_qpos[:, [4, 5, 6, 3]]).as_euler("xyz")
        plot2d(euler_pos, ["roll", "pitch", "yaw"], view=self.view)

    def plot_ref_joint_quaternion(self, joint_idx=0):
        assert joint_idx + 1 < self.model.njnt, "Invalid joint index"
        assert self.model.joint(joint_idx + 1).type[0] == 1, f"Joint type of {joint_idx} is not ball"
        plot2d(
            array=self.ref_qpos[:, 7 + joint_idx * 4: 7 + (joint_idx + 1) * 4],
            dim_label=["w", "x", "y", "z"],
            view=self.view
        )

    def close(self):
        if self.view:
            self.viewer.close()

    def get_body_motion_data(self, body_names):
        """
        Play motion_data once and get position, orientation and velocity data for specified bodies
        
        Args:
            body_names (list): List of body names in the MuJoCo model
            
        Returns:
            dict: Dictionary containing position, orientation and velocity data for each body
                Format: {
                    'body_name1': {
                        'trans': numpy.ndarray,    # shape: (frame_num, 3) - translation (x, y, z) in world frame
                        'euler': numpy.ndarray,    # shape: (frame_num, 3) - euler angles (roll, pitch, yaw) in world frame
                        'lin_vel': numpy.ndarray,  # shape: (frame_num, 3) - linear velocity in body frame
                        'ang_vel': numpy.ndarray   # shape: (frame_num, 3) - angular velocity in body frame
                    },
                    ...
                }
                
        Note:
            - trans: Position of body origin in world coordinate system
            - euler: Orientation of body frame relative to world frame (world frame coordinates)
            - lin_vel: Linear velocity in body's local coordinate system
            - ang_vel: Angular velocity in body's local coordinate system
            
            The velocities are in body frame because MuJoCo's data.cvel provides velocities
            in the body's local coordinate system, which is more useful for analyzing body motion.
        """
        # Ensure motion data is loaded
        if self._ref_qpos is None:
            self.load_motion_file()
        
        # Validate body names exist
        for body_name in body_names:
            try:
                self.model.body(body_name)
            except KeyError:
                raise ValueError(f"Body '{body_name}' not found in the model")
        
        # Initialize result dictionary
        result = {}
        for body_name in body_names:
            result[body_name] = {
                'trans': np.zeros((self.frame_num, 3)),    # translation in world frame
                'euler': np.zeros((self.frame_num, 3)),    # euler angles in world frame (xyz)
                'lin_vel': np.zeros((self.frame_num, 3)),  # linear velocity in body frame
                'ang_vel': np.zeros((self.frame_num, 3))   # angular velocity in body frame
            }
        
        # Iterate through all frames
        for frame_idx in range(self.frame_num):
            # Sync data to current frame
            self.sync_data(frame_idx)
            
            # Get position, orientation and velocity for each body
            for body_name in body_names:
                body_id = self.model.body(body_name).id
                
                result[body_name]['trans'][frame_idx] = self.data.xpos[body_id].copy()
                result[body_name]['euler'][frame_idx] = Rotation.from_quat(self.data.xquat[body_id][[1, 2, 3, 0]]).as_euler('xyz')
                
        # Calculate linear and angular velocities based on position and orientation
        for body_name in body_names:
            result[body_name]['lin_vel'][:-1] = np.diff(result[body_name]['trans'], axis=0) * self.frame_rate
            euler_diff = np.diff(result[body_name]['euler'], axis=0)
            euler_diff[euler_diff > np.pi] -= 2*np.pi
            euler_diff[euler_diff < -np.pi] += 2*np.pi
            result[body_name]['ang_vel'][:-1] = euler_diff * self.frame_rate
        return result

    def adjust_root_height(
        self,
        left_foot_name: str = 'left_foot',
        right_foot_name: str = 'right_foot',
        velocity_threshold: float = 0.1,
        angular_velocity_threshold: float = 0.5,
        pitch_threshold: float = 0.1,
        foot_offset: float = 0.0,
        draw_plot: bool = True,
    ):
        """
        Calculate root height adjustment to ensure feet contact ground when meeting multiple criteria
        
        Args:
            left_foot_name (str): Name of left foot body, default 'left_foot'
            right_foot_name (str): Name of right foot body, default 'right_foot'
            velocity_threshold (float): Linear velocity threshold below which feet are considered stationary, default 0.1
            angular_velocity_threshold (float): Angular velocity threshold below which feet are considered stationary, default 0.1
            pitch_threshold (float): Absolute pitch angle threshold below which feet are considered flat, default 0.1 (radians)
            foot_offset (float): Desired foot height offset from ground (e.g., sole thickness), default 0.0
            
        Returns:
            float: Height adjustment value to be subtracted from root position
        """
        # Get motion data for both feet
        feet_names = [left_foot_name, right_foot_name]
        motion_data = self.get_body_motion_data(feet_names)
        
        low_velocity_heights = []
        
        # Initialize plotting if needed
        if draw_plot:
            fig, axes = plt.subplots(3, 2, figsize=(12, 10))
            fig.suptitle('Foot Motion Analysis for Root Height Adjustment', fontsize=14)
            frame_indices = np.arange(self.frame_num)
        
        for col, foot_name in enumerate(feet_names):
            positions = motion_data[foot_name]['trans']
            linear_velocities = motion_data[foot_name]['lin_vel']
            angular_velocities = motion_data[foot_name]['ang_vel']
            euler_angles = motion_data[foot_name]['euler']
            
            linear_velocity_magnitudes = np.linalg.norm(linear_velocities, axis=1)
            angular_velocity_magnitudes = np.linalg.norm(angular_velocities, axis=1)
            pitch_angles = euler_angles[:, 1]
            
            # Find frames meeting all criteria: low velocities and flat pitch
            low_linear_velocity = linear_velocity_magnitudes < velocity_threshold
            low_angular_velocity = angular_velocity_magnitudes < angular_velocity_threshold
            flat_pitch = np.abs(pitch_angles) < pitch_threshold
            valid_frames = low_linear_velocity & low_angular_velocity & flat_pitch
            
            if np.any(valid_frames):
                valid_z = positions[valid_frames, 2]
                low_velocity_heights.extend(valid_z.tolist())
            
            if draw_plot:
                ax = axes[0, col]
                ax.plot(frame_indices, linear_velocity_magnitudes, 'b-', linewidth=1.5, label='Linear Velocity')
                ax.axhline(y=velocity_threshold, color='r', linestyle='--', alpha=0.7, label=f'Threshold ({velocity_threshold})')
                for i in range(len(frame_indices)):
                    if valid_frames[i]:
                        ax.axvspan(i-0.5, i+0.5, alpha=0.3, color='green')
                ax.set_title(f'{foot_name.replace("_", " ").title()} - Linear Velocity Magnitude')
                ax.set_xlabel('Frame')
                ax.set_ylabel('Velocity (m/s)')
                ax.grid(True, alpha=0.3)
                ax.legend()
                
                ax = axes[1, col]
                ax.plot(frame_indices, angular_velocity_magnitudes, 'g-', linewidth=1.5, label='Angular Velocity')
                ax.axhline(y=angular_velocity_threshold, color='r', linestyle='--', alpha=0.7, label=f'Threshold ({angular_velocity_threshold})')
                for i in range(len(frame_indices)):
                    if valid_frames[i]:
                        ax.axvspan(i-0.5, i+0.5, alpha=0.3, color='green')
                ax.set_title(f'{foot_name.replace("_", " ").title()} - Angular Velocity Magnitude')
                ax.set_xlabel('Frame')
                ax.set_ylabel('Angular Velocity (rad/s)')
                ax.grid(True, alpha=0.3)
                ax.legend()
                
                ax = axes[2, col]
                ax.plot(frame_indices, np.abs(pitch_angles), 'orange', linewidth=1.5, label='|Pitch Angle|')
                ax.axhline(y=pitch_threshold, color='r', linestyle='--', alpha=0.7, label=f'Threshold ({pitch_threshold})')
                for i in range(len(frame_indices)):
                    if valid_frames[i]:
                        ax.axvspan(i-0.5, i+0.5, alpha=0.3, color='green')
                ax.set_title(f'{foot_name.replace("_", " ").title()} - Absolute Pitch Angle')
                ax.set_xlabel('Frame')
                ax.set_ylabel('|Pitch| (rad)')
                ax.grid(True, alpha=0.3)
                ax.legend()
        
        if draw_plot:
            plt.tight_layout()
            if self.view:
                plt.show()
            else:
                plt.savefig('foot_motion_analysis.png', dpi=150, bbox_inches='tight')
                plt.close()

        if len(low_velocity_heights) != 0:
            lowest_foot_height = np.mean(low_velocity_heights)
            print(f"Based on {len(low_velocity_heights)} valid frames meeting all criteria, "
                  f"average foot height: {lowest_foot_height:.4f}")
            self.ref_qpos[:, 2] -= lowest_foot_height + foot_offset
