from collections import defaultdict
from copy import deepcopy
import os

import mujoco
import mujoco.viewer
import numpy as np
from hurodes import ROBOTS_PATH
from hurodes.mjcf_generator.generator_base import MJCFGeneratorComposite
from hurodes.mjcf_generator.unified_generator import UnifiedMJCFGenerator

from humanoid_retargeting.mjcf_generator import generator_class
from humanoid_retargeting.utils.retarget_params import RetargetParams, FootParams
from humanoid_retargeting.utils.rot import euler2quat


def get_whole_height(generator, foot_params, neck_params, body_rotate_dict=None):
    if not (foot_params.is_valid() and neck_params.is_valid()):
        return None
    generator.build()
    model = mujoco.MjModel.from_xml_string(generator.mjcf_str)
    data = mujoco.MjData(model)
    mujoco.mj_forward(model, data)

    if body_rotate_dict is not None:
        for key, value in body_rotate_dict.items():
            data.joint(model.body(key).jntadr[0]).qpos[0:4] = euler2quat(*value)

    left_foot_pos = data.body(foot_params.left_name).xpos
    right_foot_pos = data.body(foot_params.right_name).xpos
    foot_pos_z = (left_foot_pos[2] + right_foot_pos[2]) / 2 + foot_params.offset
    neck_pos_z = data.body(neck_params.name).xpos[2] + neck_params.offset
    return neck_pos_z - foot_pos_z


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

        self.global_body_ratio = self.get_global_body_ratio()
        self.human_generator = generator_class[self.generator_type](
            source_file_path=source_file_path,
            global_body_ratio=self.global_body_ratio * np.array(self.retarget_params.extra_body_ratio),
            relative_body_ratio_dict=self.retarget_params.relative_body_ratio_dict,
        )
        self.robot_generator = UnifiedMJCFGenerator(os.path.join(ROBOTS_PATH, robot_name))
        self.generator = MJCFGeneratorComposite([self.human_generator, self.robot_generator])
        self.generator.build()

        try:
            self.model = mujoco.MjModel.from_xml_string(self.generator.mjcf_str)
        except ValueError:
            with open("tmp.xml", "w") as f:
                f.write(self.generator.mjcf_str)
            print("wrong xml")
            exit()
        self.data = mujoco.MjData(self.model)

        self._viewer = None
        self._cali_qpos = None

    def get_global_body_ratio(self):
        human_height = get_whole_height(
            generator=generator_class[self.generator_type](source_file_path=self.source_file_path),
            foot_params=self.retarget_params.human_foot,
            neck_params=self.retarget_params.human_neck,
            body_rotate_dict=self.retarget_params.body_rotate_dict
        )
        robot_height = get_whole_height(
            generator=UnifiedMJCFGenerator(os.path.join(ROBOTS_PATH, self.robot_name)),
            foot_params=self.retarget_params.robot_foot,
            neck_params=self.retarget_params.robot_neck,
        )
        if human_height is not None and robot_height is not None:
            return float(robot_height / human_height)
        else:
            return 1

    @property
    def params_dir(self) -> str:
        res = os.path.join(ROBOTS_PATH, self.robot_name, "retargeting", self.generator_type)
        os.makedirs(res, exist_ok=True)
        return str(res)

    @property
    def viewer(self):
        assert self.view, "Viewer is not enabled"
        if self._viewer is None:
            self._viewer = mujoco.viewer.launch_passive(self.model, self.data)
        return self._viewer

    @property
    def cali_qpos(self):
        if self._cali_qpos is None:
            self.load_cali_qpos()
        return self._cali_qpos

    def load_cali_qpos(self):
        self.set_base_pose()
        self.set_dof_pos()
        self._cali_qpos = deepcopy(self.data.qpos)
        # make mujoco data consistent
        mujoco.mj_forward(self.model, self.data)

    def set_base_pose(self):
        mujoco.mj_forward(self.model, self.data)

        for target, generator in zip(["human", "robot"], [self.human_generator, self.robot_generator]):
            base_name = generator.all_body_names[0]
            joint = self.data.joint(self.model.body(base_name).jntadr[0])
            assert len(joint.qpos) == 7, "joint must be free"

            if target == "human":
                joint.qpos[:2] = [self.retarget_params.base_x_shift, self.retarget_params.base_y_shift]
            else:
                joint.qpos[:2] = 0

            foot_params: FootParams = getattr(self.retarget_params, f"{target}_foot")

            if foot_params.is_valid():
                left_foot_pos = self.data.body(foot_params.left_name).xpos
                right_foot_pos = self.data.body(foot_params.right_name).xpos
                foot_pos_z = (left_foot_pos[2] + right_foot_pos[2]) / 2 + foot_params.offset
                joint.qpos[2] -= foot_pos_z

    def set_dof_pos(self):
        for key, value in self.retarget_params.body_rotate_dict.items():
            self.data.joint(self.model.body(key).jntadr[0]).qpos[0:4] = euler2quat(*value)

    def render(self):
        while self.viewer.is_running():
            self.data.qpos[:] = self.cali_qpos
            self.data.qvel[:] = 0

            mujoco.mj_forward(self.model, self.data)
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
        if self._cali_qpos is None:
            self.load_cali_qpos()

        qpos_list = defaultdict(list)

        for group_name, group_value in self.retarget_params.tracker_dict.items():
            for human_tracker, robot_tracker in zip(group_value.human, group_value.robot):
                qpos = np.zeros(7)
                qpos[:3] = self.data.body(human_tracker).xpos - self.data.body(robot_tracker).xpos
                qpos[3:] = self.data.body(human_tracker).xquat
                qpos_list[group_name].append(qpos)
        return qpos_list


if __name__ == '__main__':
    # import os
    # from humanoid_retargeting import AMASS_DATA_PATH

    # AMASS_FILE_PATH = os.path.join(AMASS_DATA_PATH, "ACCAD", 'Female1General_c3d', "A1_-_Stand_stageii.npz")

    # aligner = Aligner(source_file_path=AMASS_FILE_PATH, generator_type="smpl",
    #                   robot_name="kuavo_s45", params_name="try")
    
    # aligner.load_cali_qpos()

    # aligner.get_tracker_offset()

    # aligner.render()
    # aligner.save_retarget_params("try")
    
    import os
    from pathlib import Path
    from humanoid_retargeting import BVH_DATA_PATH

    BVH_FILE_PATH = os.path.join(BVH_DATA_PATH, "Reallusion", "myData", 'BJJ_General_02_calibrated.bvh')

    aligner = Aligner(source_file_path=BVH_FILE_PATH, generator_type="bvh",
                      robot_name="kuavo_s45", params_name="try")
    
    aligner.load_cali_qpos()

    aligner.get_tracker_offset()

    aligner.render()
    aligner.save_retarget_params("try")