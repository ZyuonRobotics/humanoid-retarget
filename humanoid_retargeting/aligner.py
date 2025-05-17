from abc import ABC, abstractmethod
import time
import os
from copy import deepcopy
import json
from collections import defaultdict

import mujoco
import mujoco.viewer
import numpy as np
from scipy.spatial.transform import Rotation
from hurodes import ROBOTS_PATH
from hurodes.mjcf_generator.generator_base import MJCFGeneratorComposite
from hurodes.mjcf_generator.unified_generator import UnifiedMJCFGenerator

from humanoid_retargeting.utils.rot import euler2quat
from humanoid_retargeting.mjcf_generator import generator_class, BVH2MJCFGenerator
from humanoid_retargeting.utils.retarget_params import RetargetParams, FootParams, TrackerConfig


class Aligner:
    def __init__(self, source_file_path, robot_name, generator_type, params_name=None, view=True):
        self.source_file_path = source_file_path
        self.robot_name = robot_name
        self.generator_type = generator_type
        self.params_name = params_name
        self.view = view

        if self.params_name is None:
            self.retarget_params = RetargetParams()
        else:
            self.retarget_params = RetargetParams.from_json(
                os.path.join(self.params_dir, f"{self.params_name}.json")
            )
        self.human_generator = generator_class[self.generator_type](
            source_file_path=source_file_path,
            whole_body_ratio=self.retarget_params.whole_body_ratio,
            body_ratio_dict=self.retarget_params.body_ratio_dict,
        )
        self.robot_generator = UnifiedMJCFGenerator(os.path.join(ROBOTS_PATH, robot_name))
        self.generator = MJCFGeneratorComposite([self.human_generator, self.robot_generator])
        self.generator.build()

        self.mujoco_model = mujoco.MjModel.from_xml_string(self.generator.mjcf_str)
        self.mujoco_data = mujoco.MjData(self.mujoco_model)

        self._viewer = None
        self._cali_qpos = None

    @property
    def params_dir(self) -> str:
        res = os.path.join(ROBOTS_PATH, self.robot_name, "retargeting", self.generator_type)
        os.makedirs(res, exist_ok=True)
        return str(res)

    @property
    def viewer(self):
        assert self.view, "Viewer is not enabled"
        if self._viewer is None:
            self._viewer = mujoco.viewer.launch_passive(self.mujoco_model, self.mujoco_data)
        return self._viewer

    @property
    def cali_qpos(self):
        if self._cali_qpos is None:
            self.load_cali_qpos()
        return self._cali_qpos

    def load_cali_qpos(self):
        self.set_base_pose()
        self.set_dof_pos()
        self._cali_qpos = deepcopy(self.mujoco_data.qpos)
        # make mujoco data consistent
        mujoco.mj_forward(self.mujoco_model, self.mujoco_data)

    def set_base_pose(self):
        mujoco.mj_forward(self.mujoco_model, self.mujoco_data)

        for target, generator in zip(["human", "robot"], [self.human_generator, self.robot_generator]):
            base_name = generator.all_body_names[0]
            joint = self.mujoco_data.joint(self.mujoco_model.body(base_name).jntadr[0])
            assert len(joint.qpos) == 7, "joint must be free"

            if target == "human":
                joint.qpos[:2] = [self.retarget_params.base_x_shift, self.retarget_params.base_y_shift]
            else:
                joint.qpos[:2] = 0

            foot_params : FootParams = getattr(self.retarget_params, f"{target}_foot")

            if foot_params.is_valid():
                left_foot_pos = self.mujoco_data.body(foot_params.left_name).xpos
                right_foot_pos = self.mujoco_data.body(foot_params.right_name).xpos
                foot_pos_z = (left_foot_pos[2] + right_foot_pos[2]) / 2 - foot_params.height
                joint.qpos[2] -= foot_pos_z

    def set_dof_pos(self):
        for key, value in self.retarget_params.body_rotate_dict.items():
            self.mujoco_data.joint(self.mujoco_model.body(key).jntadr[0]).qpos[0:4] = euler2quat(*value)

    def render(self):
        while self.viewer.is_running():
            self.mujoco_data.qpos[:] = self.cali_qpos
            self.mujoco_data.qvel[:] = 0

            mujoco.mj_forward(self.mujoco_model, self.mujoco_data)
            self.viewer.sync()

    def close(self):
        if self.view:
            self.viewer.close()

    def save_retarget_params(self, save_params_name=None):
        assert not (save_params_name is None and self.params_name is None)
        if save_params_name is None:
            save_params_name = self.params_name

        self.retarget_params.to_json(
            os.path.join(self.params_dir, f"{save_params_name}.json")
        )

    def get_tracker_offset(self):
        qpos_list = defaultdict(list)

        for group_name, group_value in self.retarget_params.tracker_dict.items():
            for human_tracker, robot_tracker in zip(group_value.human, group_value.robot):
                qpos = np.zeros(7)
                qpos[:3] = self.mujoco_data.body(human_tracker).xpos - self.mujoco_data.body(robot_tracker).xpos
                qpos[3:] = self.mujoco_data.body(human_tracker).xquat
                qpos_list[group_name].append(qpos)
        return qpos_list

if __name__ == '__main__':
    import os
    from humanoid_retargeting import AMASS_DATA_PATH

    AMASS_FILE_PATH = os.path.join(AMASS_DATA_PATH, "ACCAD", 'Female1General_c3d', "A1_-_Stand_stageii.npz")

    aligner = Aligner(source_file_path=AMASS_FILE_PATH, generator_type="smpl",
                          robot_name="kuavo_s45", params_name="try")
    aligner.load_cali_qpos()

    aligner.get_tracker_offset()

    aligner.render()
    aligner.save_retarget_params("try")
