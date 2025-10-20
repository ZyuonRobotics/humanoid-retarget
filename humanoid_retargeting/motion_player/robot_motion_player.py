from pathlib import Path
import mujoco

from hurodes import ROBOTS_PATH
import numpy as np
import matplotlib.pyplot as plt

from hurodes.generators import MJCFHumanoidGenerator
from humanoid_retargeting.motion_player.player_base import MotionPlayerBase


class RobotMotionPlayer(MotionPlayerBase):
    generator_class = MJCFHumanoidGenerator
    file_suffix = "npz"

    def __init__(self, robot_name, view=True):
        self.robot_name = robot_name

        super().__init__(view=view)
    
    @property
    def model(self):
        assert self.generator is not None and self.generator.loaded, "Generator is not loaded"
        if self._model is None:
            self.generator.generate(relative_mesh_path=False) # call generate() lazily, because it should not be called in load()
            self._model = mujoco.MjModel.from_xml_string(self.generator.xml_str) # type: ignore
        return self._model

    def create_generator(self):
        self.generator = self.generator_class()

    def load_motion_file(self, source_file_path):
        motion_dict = np.load(source_file_path)

        self._frame_rate = motion_dict["frame_rate"]
        self._ref_qpos = np.concatenate([
            motion_dict["root_trans"],
            motion_dict["root_quat"][:],
            motion_dict["joint_pos"]
        ], axis=1)
    
    def _load(self, source_file_path, **kwargs):
        self.load_motion_file(source_file_path)
