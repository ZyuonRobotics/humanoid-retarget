from abc import ABC, abstractmethod
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt

from humanoid_retargeting.motion_player.player_base import MotionPlayerBase
from humanoid_retargeting.mjcf_generator.retargeting_generator_base import RetargetingMJCFGeneratorBase
from humanoid_retargeting.utils.lowpass import filter_lowpass2d, filter_lowpass_quaternion
from humanoid_retargeting.utils.human_config import HumanConfig

class HumanoidMotionPlayerBase(MotionPlayerBase, ABC):
    def __init__(self, global_body_ratio=1.0, relative_body_ratio_dict=None, view=True):
        self.global_body_ratio = global_body_ratio
        self.relative_body_ratio_dict = relative_body_ratio_dict

        super().__init__(view=view)
        self.human_config: HumanConfig = HumanConfig()

    def create_generator(self):
        assert isinstance(self.generator_class, type(RetargetingMJCFGeneratorBase)), "Generator class is not a subclass of RetargetingMJCFGeneratorBase"
        self.generator = self.generator_class(
            global_body_ratio=self.global_body_ratio,
            relative_body_ratio_dict=self.relative_body_ratio_dict
        )

    def load(self, **kwargs):
        source_file_path = kwargs["source_file_path"]
        
        self.generator.load(source_file_path)
        self._load(source_file_path)
        self.load_config(source_file_path)

        assert self._ref_qpos is not None, "Reference qpos is not loaded"
        self._ref_qpos[:, :3] *= self.global_body_ratio

        self._loaded = True


    def load_config(self, source_file_path):
        config_path = Path(source_file_path).with_suffix('.yaml')
        
        if config_path.exists():
            self.human_config = HumanConfig.from_yaml(str(config_path))
        else:
            # Create default HumanConfig if config doesn't exist
            self.human_config = HumanConfig()
            # Set default foot and hip names from player properties
            if self.foot_names is not None:
                self.human_config.foot_names = self.foot_names
            if self.hip_names is not None:
                self.human_config.hip_names = self.hip_names

    def save_config(self, source_file_path):
        config_path = Path(source_file_path).with_suffix('.yaml')
        self.human_config.to_yaml(str(config_path))
        print(f"Configuration saved to {config_path}")

    @property
    def foot_names(self):
        return None

    @property
    def hip_names(self):
        return None

    def lowpass_all_qpos(self, cutoff=20, order=2):
        assert isinstance(self._ref_qpos, np.ndarray) and self._ref_qpos.ndim == 2, "Reference qpos is not loaded"

        for joint_idx in range(self.model.njnt):
            if joint_idx == 0:
                assert self.model.joint(0).type[0] == 0, "Root joint should be free"
                self._ref_qpos[:, :3] = filter_lowpass2d(self.ref_qpos[:, :3], cutoff, order)
            else:
                assert self.model.joint(joint_idx).type[0] == 1, f"Joint type of {joint_idx} is not ball"
            
            quat = self.ref_qpos[:, 3 + joint_idx * 4: 3 + (joint_idx + 1) * 4]
            res_quat = filter_lowpass_quaternion(quat, cutoff, order)
            self._ref_qpos[:, 3 + joint_idx * 4: 3 + (joint_idx + 1) * 4] = res_quat


    def calculate_height_adjustment(
        self,
        velocity_threshold: float = 0.1,
        angular_velocity_threshold: float = 0.5,
        pitch_threshold: float = 0.1,
        draw_plot: bool = True,
    ):
        """
        Calculate root height adjustment to ensure feet contact ground when meeting multiple criteria.
        The height adjustment is calculated and saved to human_config.height_adjustment, but not applied to ref_qpos.
        
        Args:
            velocity_threshold (float): Linear velocity threshold below which feet are considered stationary, default 0.1
            angular_velocity_threshold (float): Angular velocity threshold below which feet are considered stationary, default 0.5
            pitch_threshold (float): Absolute pitch angle threshold below which feet are considered flat, default 0.1 (radians)
            draw_plot (bool): Whether to draw analysis plots, default True
            
        Returns:
            float: Height adjustment value that was calculated, or None if human_config.human_foot is not valid
        """
        # Check if human_config has valid human_foot
        if not self.human_config.foot_names is not None:
            print("human_config.foot_names is not valid. Cannot calculate height adjustment.")
            return None
        # Get motion data for both feet
        feet_names = self.human_config.foot_names
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
            height_adjustment = np.mean(low_velocity_heights)
            print(f"Based on {len(low_velocity_heights)} valid frames meeting all criteria, "
                  f"height adjustment: {height_adjustment:.4f}")
            self.human_config.height_adjustment = float(height_adjustment)


    def adjust_height_adjustment(self):
        if self.human_config.height_adjustment is not None and self.human_config.foot_offset is not None:
            height_adjustment = self.human_config.height_adjustment + self.human_config.foot_offset
            self._ref_qpos[:, 2] -= height_adjustment