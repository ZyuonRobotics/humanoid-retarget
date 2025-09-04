from collections import defaultdict
from copy import deepcopy
from pathlib import Path

import mujoco
import mujoco.viewer
import numpy as np
from hurodes import ROBOTS_PATH
from hurodes.generators import MJCFGeneratorComposite
from hurodes.generators import MJCFHumanoidGenerator

from humanoid_retargeting import PARAMETERS_PATH
from humanoid_retargeting.mjcf_generator import generator_class
from humanoid_retargeting.utils.retarget_params import RetargetParams, FootParams
from humanoid_retargeting.utils.rot import euler2quat


def get_leg_length(generator, foot_params, hip_params, body_rotate_dict=None):
    if not (foot_params.is_valid() and hip_params.is_valid()):
        return None
    generator.build()
    model = mujoco.MjModel.from_xml_string(generator.mjcf_str) # type: ignore
    data = mujoco.MjData(model) # type: ignore
    mujoco.mj_forward(model, data) # type: ignore

    if body_rotate_dict is not None:
        for key, value in body_rotate_dict.items():
            data.joint(model.body(key).jntadr[0]).qpos[0:4] = euler2quat(*value)

    foot_pos = (data.body(foot_params.left_name).xpos + data.body(foot_params.right_name).xpos) / 2
    hip_pos = (data.body(hip_params.left_name).xpos + data.body(hip_params.right_name).xpos) / 2
    length = np.linalg.norm(hip_pos - foot_pos) + hip_params.offset - foot_params.offset
    return length


class Aligner:
    def __init__(self, source_file_path, robot_name, generator_type, params_name=None, view=True):
        self.source_file_path = source_file_path
        self.robot_name = robot_name
        self.generator_type = generator_type
        self.params_name = params_name
        self.view = view

        self.load_mujoco()


    def load_mujoco(self, retarget_params=None):
        if retarget_params is None:
            if self.params_name is None:
                self.retarget_params = RetargetParams()
            else:
                self.retarget_params = RetargetParams.from_json(
                    Path(self.params_dir) / f"{self.params_name}.json"
                )
        else:
            self.retarget_params = retarget_params

        self.global_body_ratio = self.get_global_body_ratio()
        self.human_generator = generator_class[self.generator_type](
            source_file_path=self.source_file_path,
            global_body_ratio=self.global_body_ratio * np.array(self.retarget_params.extra_body_ratio),
            relative_body_ratio_dict=self.retarget_params.relative_body_ratio_dict
        )
        self.robot_generator = MJCFHumanoidGenerator.from_robot_name(self.robot_name)
        self.generator = MJCFGeneratorComposite(dict(human=self.human_generator, robot=self.robot_generator))
        self.generator.build()

        try:
            self.model = mujoco.MjModel.from_xml_string(self.generator.xml_str) # type: ignore
        except ValueError:
            with open("tmp.xml", "w") as f:
                f.write(self.generator.xml_str)
            print("wrong xml")
            exit()
        self.data = mujoco.MjData(self.model)

        self._viewer = None
        self._cali_qpos = None

        mujoco.mj_forward(self.model, self.data)

    def get_global_body_ratio(self):
        human_length = get_leg_length(
            generator=generator_class[self.generator_type](source_file_path=self.source_file_path),
            foot_params=self.retarget_params.human_foot,
            hip_params=self.retarget_params.human_hip,
            body_rotate_dict=self.retarget_params.body_rotate_dict
        )
        robot_length = get_leg_length(
            generator=MJCFHumanoidGenerator.from_robot_name(self.robot_name),
            foot_params=self.retarget_params.robot_foot,
            hip_params=self.retarget_params.robot_hip,
        )
        if human_length is not None and robot_length is not None:
            return float(robot_length / human_length)
        else:
            return 1

    @property
    def params_dir(self) -> str:
        res = Path(PARAMETERS_PATH) / self.robot_name / self.generator_type
        res.mkdir(parents=True, exist_ok=True)
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
        self.set_base_rotation()
        self.set_base_translation()
        self.set_dof_pos()
        self._cali_qpos = deepcopy(self.data.qpos)
        # make mujoco data consistent
        mujoco.mj_forward(self.model, self.data) # type: ignore

    def set_base_translation(self):
        """Set base XY translation and Z height alignment based on feet positions."""
        mujoco.mj_forward(self.model, self.data)

        for target, generator in zip(["human", "robot"], [self.human_generator, self.robot_generator]):
            base_name = generator.all_body_names[0]
            joint = self.data.joint(self.model.body(base_name).jntadr[0])
            assert len(joint.qpos) == 7, "joint must be free"

            if target == "human":
                joint.qpos[:2] = [self.retarget_params.base_x_shift, self.retarget_params.base_y_shift]
            else:
                joint.qpos[:2] = 0

            mujoco.mj_forward(self.model, self.data)

            # Align feet on Z axis
            foot_params: FootParams = getattr(self.retarget_params, f"{target}_foot")
            if foot_params.is_valid():
                left_foot_pos = self.data.body(f"{target}_{foot_params.left_name}").xpos
                right_foot_pos = self.data.body(f"{target}_{foot_params.right_name}").xpos
                foot_pos_z = (left_foot_pos[2] + right_foot_pos[2]) / 2 + foot_params.offset
                joint.qpos[2] -= foot_pos_z

    def set_base_rotation(self):
        """Apply user-defined base Euler rotation to the human root."""
        if self.params_name is None:
            base_rot = [90, 0, 90] if self.generator_type == "bvh" else [0, 0, 0]
        else:
            base_rot = getattr(self.retarget_params, "base_rotation")
        
        base_name = self.human_generator.all_body_names[0]
        joint = self.data.joint(self.model.body(base_name).jntadr[0])
        assert len(joint.qpos) == 7

        base_quat = euler2quat(*base_rot)
        joint.qpos[3:7] = base_quat
        
        mujoco.mj_forward(self.model, self.data)

    def set_dof_pos(self):
        for key, value in self.retarget_params.body_rotate_dict.items():
            self.data.joint(self.model.body(f"human_{key}").jntadr[0]).qpos[0:4] = euler2quat(*value)

    def render(self):
        while self.viewer.is_running():
            self.data.qpos[:] = self.cali_qpos
            self.data.qvel[:] = 0

            mujoco.mj_forward(self.model, self.data) # type: ignore
            self.viewer.sync()

    def close(self):
        if self.view:
            self.viewer.close()

    def save_retarget_params(self, save_params_name=None):
        assert not (save_params_name is None and self.params_name is None)
        if save_params_name is None:
            save_params_name = self.params_name

        self.retarget_params.to_json(
            Path(self.params_dir) / f"{save_params_name}.json"
        )

    def get_tracker_offset(self):
        if self._cali_qpos is None:
            self.load_cali_qpos()

        qpos_list = defaultdict(list)

        for group_name, group_value in self.retarget_params.tracker_dict.items():
            for human_tracker, robot_tracker in zip(group_value.human, group_value.robot):
                qpos = np.zeros(7)
                qpos[:3] = self.data.body(f"human_{human_tracker}").xpos - self.data.body(f"robot_{robot_tracker}").xpos
                qpos[3:] = self.data.body(f"human_{human_tracker}").xquat
                qpos_list[group_name].append(qpos)
        return qpos_list

