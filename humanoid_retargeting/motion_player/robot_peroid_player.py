import yaml
from itertools import product
import numpy as np

import matplotlib.pyplot as plt
from humanoid_retargeting.motion_player.robot_motion_player import RobotMotionPlayer

LEG_JOINTS = ["hip", "knee", "ankle"]
ARM_JOINTS = ["shoulder", "elbow"]

class RobotPeriodPlayer(RobotMotionPlayer):
    def __init__(self, source_file_path, robot_name, view=True, frame_rate=100, max_steps=300000):
        super().__init__(source_file_path=source_file_path, robot_name=robot_name, view=view)
        self._frame_rate = frame_rate
        self.max_steps = max_steps

    def _validate_config_structure(self, config):
        required_keys = ['stepping_period', 'leg_joints', 'arm_joints', 'height', "double_support_threshold"]
        for key in required_keys:
            assert key in config, f"Configuration must contain '{key}'"

    def _validate_leg_joints(self, leg_joints):
        required_keys = ['scale', 'offset', 'left_leg', 'right_leg']
        for key in required_keys:
            assert key in leg_joints, f"leg_joints must contain '{key}'"
        
        for config_type in ['scale', 'offset']:
            config_dict = leg_joints[config_type]
            for joint in LEG_JOINTS:
                assert joint in config_dict, f"leg_joints {config_type} must contain '{joint}'"
            if config_dict['knee'] is None:
                config_dict['knee'] = - (config_dict['hip'] + config_dict['ankle'])
        
        for side in ['left_leg', 'right_leg']:
            side_config = leg_joints[side]
            for joint in LEG_JOINTS:
                assert joint in side_config, f"{side} must have '{joint}' index"
                idx = side_config[joint]
                assert 0 <= idx < self.model.nq - 7, f"Invalid {joint} index for {side}"

    def _validate_arm_joints(self, arm_joints):
        required_keys = ['scale', 'offset', 'left_arm', 'right_arm']
        for key in required_keys:
            assert key in arm_joints, f"arm_joints must contain '{key}'"
        
        for config_type in ['scale', 'offset']:
            config_dict = arm_joints[config_type]
            for joint in ARM_JOINTS:
                assert joint in config_dict, f"arm_joints {config_type} must contain '{joint}'"
            if config_dict['elbow'] is None:
                config_dict['elbow'] = config_dict['shoulder']
        
        for side in ['left_arm', 'right_arm']:
            side_config = arm_joints[side]
            for joint in ARM_JOINTS:
                assert joint in side_config, f"{side} must have '{joint}' index"
                idx = side_config[joint]
                assert 0 <= idx < self.model.nq - 7, f"Invalid {joint} index for {side}"

    def load_motion_file(self):
        with open(self.source_file_path, 'r') as f:
            config = yaml.safe_load(f)
        
        self._validate_config_structure(config)
        self._validate_leg_joints(config['leg_joints'])
        self._validate_arm_joints(config['arm_joints'])
        
        stepping_period = config['stepping_period']
        leg_joints = config['leg_joints']
        arm_joints = config['arm_joints']
        double_support_threshold = config['double_support_threshold']

        self._ref_qpos = np.zeros((self.max_steps, self.model.nq))
        self._ref_qpos[:, 2] = config['height']

        time_idx = np.linspace(0, self.max_steps, num=self.max_steps) / self._frame_rate
        sine = np.sin(time_idx / stepping_period * 2 * np.pi)
        sin_left = np.where(sine > -double_support_threshold, 0, sine)
        sin_right = -np.where(sine < double_support_threshold, 0, sine)

        for side in ['left_leg', 'right_leg']:
            side_config = leg_joints[side]
            wave = sin_left if side.startswith('left') else sin_right
            for joint in LEG_JOINTS:
                self._ref_qpos[:, side_config[joint] + 7] = leg_joints['scale'][joint] * wave + leg_joints['offset'][joint]

        for side in ['left_arm', 'right_arm']:
            side_config = arm_joints[side]
            for joint in ARM_JOINTS:
                # arm joint motion is opposite to leg joint motion
                if joint == "shoulder":
                    wave = -sine if side.startswith('left') else sine
                else:
                    wave = sin_right if side.startswith('left') else sin_left
                self._ref_qpos[:, side_config[joint] + 7] = arm_joints['scale'][joint] * wave + arm_joints['offset'][joint]
