from abc import ABC, abstractmethod
import time

import mujoco
import numpy as np
from scipy.spatial.transform import Rotation

from humanoid_retargeting.mjcf_generator.generator_base import MJCFGeneratorBase

class MotionPlayerBase(ABC):
    generator_class = MJCFGeneratorBase

    def __init__(self, source_file_path, cali_info=None, view=True):
        self.source_file_path = source_file_path
        self.cali_info = cali_info
        self.view = view

        self.generator = self.generator_class(source_file_path=source_file_path)
        self.generator.build()

        self.mujoco_model = mujoco.MjModel.from_xml_string(self.generator.mjcf_str)
        self.mujoco_data = mujoco.MjData(self.mujoco_model)
        if view:
            self.viewer = mujoco.viewer.launch_passive(self.mujoco_model, self.mujoco_data)
            self.viewer.sync()

        self.motion_data = None
        self.frame_rate = None
        self.ref_qpos = None
        self.cali_qpos = None

    @abstractmethod
    def load_motion_file(self):
        raise NotImplemented

    @abstractmethod
    def load_cali_qpos(self):
        raise NotImplemented

    def render(self):
        assert self.view, "Viewer is not enabled"
        if self.ref_qpos is None:
            self.load_motion_file()

        for i in range(self.ref_qpos.shape[0]):
            step_start = time.time()

            self.mujoco_data.qpos[:] = self.ref_qpos[i]
            self.mujoco_data.qvel[:] = 0
            mujoco.mj_forward(self.mujoco_model, self.mujoco_data)
            self.viewer.sync()

            time_until_next_step = 1 / self.frame_rate - (time.time() - step_start)
            if time_until_next_step > 0:
                time.sleep(time_until_next_step)

        self.close()

    def render_cali(self):
        assert self.view, "Viewer is not enabled"
        if self.cali_qpos is None:
            self.load_cali_qpos()

        while True:
            self.mujoco_data.qpos[:] = self.cali_qpos
            self.mujoco_data.qvel[:] = 0

            mujoco.mj_forward(self.mujoco_model, self.mujoco_data)
            self.viewer.sync()


    def close(self):
        if self.view:
            self.viewer.close()

