from abc import ABC, abstractmethod

import numpy as np

from humanoid_retargeting.motion_player.player_base import MotionPlayerBase
from humanoid_retargeting.mjcf_generator.retargeting_generator_base import RetargetingMJCFGeneratorBase
from humanoid_retargeting.utils.lowpass import filter_lowpass2d, filter_lowpass_quaternion


class HumanoidMotionPlayerBase(MotionPlayerBase, ABC):
    def __init__(self, source_file_path, global_body_ratio=1.0, relative_body_ratio_dict=None, view=True):
        self.global_body_ratio = global_body_ratio
        self.relative_body_ratio_dict = relative_body_ratio_dict

        super().__init__(source_file_path=source_file_path, view=view)


    def create_generator(self):
        assert isinstance(self.generator_class, type(RetargetingMJCFGeneratorBase)), "Generator class is not a subclass of RetargetingMJCFGeneratorBase"
        self._generator = self.generator_class(
            source_file_path=self.source_file_path,
            global_body_ratio=self.global_body_ratio,
            relative_body_ratio_dict=self.relative_body_ratio_dict
        )

    @property
    def ref_qpos(self) -> np.ndarray:
        if self._ref_qpos is None:
            self.load_motion_file()
            assert self._ref_qpos is not None, "Reference qpos is not loaded"
            self._ref_qpos[:, :3] *= self.global_body_ratio
        return self._ref_qpos

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
