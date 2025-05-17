from abc import ABC, abstractmethod
import time
import os
from copy import deepcopy
import json

import mujoco
import mujoco.viewer
import numpy as np
from scipy.spatial.transform import Rotation
from hurodes import ROBOTS_PATH
from hurodes.mjcf_generator.generator_base import MJCFGeneratorComposite
from hurodes.mjcf_generator.unified_generator import UnifiedMJCFGenerator

from humanoid_retargeting.utils.rot import euler2quat
from humanoid_retargeting.mjcf_generator import generator_class, BVH2MJCFGenerator

RETARGET_PARAMS = {
    "robot":{
        "left_foot": None,
        "right_foot": None,
        "foot_height": 0.0,
    },
    "human": {
        "left_foot": None,
        "right_foot": None,
        "foot_height": 0,
    },
    "whole_body_ratio": [1., 1., 1.],
    "body_ratio_dict": {},
    "body_rotate_dict": {}
}

class Aligner:
    def __init__(self, source_file_path, robot_name, generator_type, params_name=None, view=True):
        self.source_file_path = source_file_path
        self.robot_name = robot_name
        self.generator_type = generator_type
        self.params_name = params_name
        self.view = view

        if self.params_name is None:
            self.retarget_params = deepcopy(RETARGET_PARAMS)
        else:
            with open(os.path.join(self.params_dir, f"{self.params_name}.json"), "r") as f:
                self.retarget_params = json.load(f)

        self.human_generator = generator_class[self.generator_type](
            source_file_path=source_file_path,
            whole_body_ratio=self.retarget_params["whole_body_ratio"],
            body_ratio_dict=self.retarget_params["body_ratio_dict"],
        )
        self.robot_generator = UnifiedMJCFGenerator(os.path.join(ROBOTS_PATH, robot_name))
        self.generator = MJCFGeneratorComposite([self.human_generator, self.robot_generator])
        self.generator.build()

        self.mujoco_model = mujoco.MjModel.from_xml_string(self.generator.mjcf_str)
        self.mujoco_data = mujoco.MjData(self.mujoco_model)

        self._viewer = None
        self._cali_qpos = None

    @property
    def params_dir(self):
        res = os.path.join(ROBOTS_PATH, self.robot_name, "retargeting", self.generator_type)
        os.makedirs(res, exist_ok=True)
        return res

    @property
    def viewer(self):
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

    def set_base_pose(self):
        mujoco.mj_forward(self.mujoco_model, self.mujoco_data)

        for target, generator in zip(["human", "robot"], [self.human_generator, self.robot_generator]):
            base_name = generator.all_body_names[0]
            joint = self.mujoco_data.joint(self.mujoco_model.body(base_name).jntadr[0])
            assert len(joint.qpos) == 7, "joint must be free"

            if target == "human":
                joint.qpos[:2] = [self.retarget_params["base_x_shift"], self.retarget_params["base_y_shift"]]
            else:
                joint.qpos[:2] = 0

            if all([v is not None for v in self.retarget_params[target].values()]):
                left_foot_pos = self.mujoco_data.body(self.retarget_params[target]["left_foot"]).xpos
                right_foot_pos = self.mujoco_data.body(self.retarget_params[target]["right_foot"]).xpos
                foot_height = self.retarget_params[target]["foot_height"]
                foot_pos_z = (left_foot_pos[2] + right_foot_pos[2]) / 2 - foot_height
                joint.qpos[2] -= foot_pos_z

    def set_dof_pos(self):
        for key, value in self.retarget_params["body_rotate_dict"].items():
            self.mujoco_data.joint(self.mujoco_model.body(key).jntadr[0]).qpos[0:4] = euler2quat(*value)

    def render(self):
        assert self.view, "Viewer is not enabled"
        if self.cali_qpos is None:
            self.load_cali_qpos()

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

        UnifiedMJCFGenerator(os.path.join(ROBOTS_PATH, self.robot_name, "retargeting"))

        with open(os.path.join(self.params_dir, f"{save_params_name}.json"), "w") as f:
            json.dump(self.retarget_params, f, indent=4)

if __name__ == '__main__':
    import os
    from humanoid_retargeting import AMASS_DATA_PATH

    AMASS_FILE_PATH = os.path.join(AMASS_DATA_PATH, "ACCAD", 'Female1General_c3d', "A1_-_Stand_stageii.npz")

    aligner = Aligner(source_file_path=AMASS_FILE_PATH, generator_type="smpl",
                          robot_name="kuavo_s45", params_name="try")
    aligner.set_base_pose()
    aligner.render()
    aligner.save_retarget_params("try")
