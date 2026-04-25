from collections import defaultdict
from copy import deepcopy
from pathlib import Path

import mujoco
import mujoco.viewer
import numpy as np
from hurodes import HumanoidRobot
from hurodes.generators import MJCFGeneratorComposite
from hurodes.generators import MJCFHumanoidGenerator

from humanoid_retargeting import CONFIGS_PATH
from humanoid_retargeting.mjcf_generator import generator_class
from humanoid_retargeting.utils.retarget_config import RetargetConfig
from humanoid_retargeting.utils.rot import euler2quat
from humanoid_retargeting.utils.human_config import HumanConfig


def get_leg_length(
    generator, 
    foot_names, 
    hip_names, 
    foot_offset, 
    hip_offset, 
    body_rotate_dict=None
):
    generator.generate(relative_mesh_path=False)
    model = mujoco.MjModel.from_xml_string(generator.xml_str) # type: ignore
    data = mujoco.MjData(model) # type: ignore
    mujoco.mj_forward(model, data) # type: ignore

    if body_rotate_dict is not None:
        for key, value in body_rotate_dict.items():
            data.joint(model.body(key).jntadr[0]).qpos[0:4] = euler2quat(*value)

    foot_pos = (data.body(foot_names[0]).xpos + data.body(foot_names[1]).xpos) / 2
    hip_pos = (data.body(hip_names[0]).xpos + data.body(hip_names[1]).xpos) / 2
    length = np.linalg.norm(hip_pos - foot_pos) + hip_offset - foot_offset
    return length


class Aligner:
    def __init__(self, source_file_path, robot_name, generator_type, config_name=None, view=True):
        self.source_file_path = source_file_path
        self.robot_name = robot_name
        self.generator_type = generator_type
        self.config_name = config_name
        self.view = view
        self.generate_skin = True 

        self.robot_hip_names = None
        self.robot_foot_names = None
        self.robot_hip_offset = None
        self.robot_foot_offset = None
        self.human_hip_names = None
        self.human_foot_names = None
        self.human_hip_offset = None
        self.human_foot_offset = None

        self.load_robot_parmas()
        self.load_human_parmas()
        self.load_mujoco()

    def load_robot_parmas(self):
        self.robot = HumanoidRobot.from_name(self.robot_name)
        self.robot_hip_names = self.robot.hrdf.hip_names
        self.robot_foot_names = self.robot.hrdf.foot_names
        # TODO: move this to hurodes
        self.robot_hip_offset = 0.0
        self.robot_foot_offset = -0.045

    def load_human_parmas(self):
        human_config_path = Path(self.source_file_path).with_suffix('.yaml')
        assert human_config_path.exists(), "Human config file not found"
        human_config = HumanConfig.from_yaml(str(human_config_path))
        assert human_config.is_valid(), "Human play config are not valid"
        self.human_hip_names = human_config.hip_names
        self.human_foot_names = human_config.foot_names
        self.human_hip_offset = human_config.hip_offset
        self.human_foot_offset = human_config.foot_offset

    def load_mujoco(self, retarget_config=None, generate_skin=None):
        if retarget_config is None:
            if self.config_name is None:
                self.retarget_config = RetargetConfig()
            else:
                self.retarget_config = RetargetConfig.from_yaml(
                    Path(self.config_dir) / f"{self.config_name}.yaml"
                )
        else:
            self.retarget_config = retarget_config
        
        self.global_body_ratio = self.get_global_body_ratio()

        generator_kwargs = {
            'source_file_path': self.source_file_path,
            'global_body_ratio': self.global_body_ratio * np.array(self.retarget_config.extra_body_ratio),
            'relative_body_ratio_dict': self.retarget_config.relative_body_ratio_dict
        }

        if generate_skin is not None:
            self.generate_skin = generate_skin
        if self.generator_type == 'smpl' and hasattr(self, 'generate_skin'):
            generator_kwargs['generate_skin'] = self.generate_skin

        self.human_generator = generator_class[self.generator_type].from_source_file_path(**generator_kwargs)
        self.robot_generator = MJCFHumanoidGenerator.from_robot_name(self.robot_name)
        self.generator = MJCFGeneratorComposite(dict(human=self.human_generator, robot=self.robot_generator))
        self.generator.generate(relative_mesh_path=False)

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
        generator_kwargs = {'source_file_path': self.source_file_path}
        if self.generator_type == 'smpl':
            generator_kwargs['generate_skin'] = False

        human_length = get_leg_length(
            generator=generator_class[self.generator_type].from_source_file_path(**generator_kwargs),
            foot_names=self.human_foot_names,
            hip_names=self.human_hip_names,
            foot_offset=self.human_foot_offset,
            hip_offset=self.human_hip_offset,
            body_rotate_dict=self.retarget_config.body_rotate_dict
        )
        robot_length = get_leg_length(
            generator=MJCFHumanoidGenerator.from_robot_name(self.robot_name),
            foot_names=self.robot_foot_names,
            hip_names=self.robot_hip_names,
            foot_offset=self.robot_foot_offset,
            hip_offset=self.robot_hip_offset,
        )
        if human_length is not None and robot_length is not None:
            return float(robot_length / human_length)
        else:
            return 1

    @property
    def config_dir(self) -> str:
        res = Path(CONFIGS_PATH) / self.robot_name / self.generator_type
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
                joint.qpos[:2] = [self.retarget_config.base_x_shift, self.retarget_config.base_y_shift]
            else:
                joint.qpos[:2] = 0

            mujoco.mj_forward(self.model, self.data)

            # Align feet on Z axis
            assert getattr(self, f"{target}_foot_names") is not None, "Foot names are not set"
            foot_names = [f"{target}_{name}" for name in getattr(self, f"{target}_foot_names")]
            assert getattr(self, f"{target}_foot_offset") is not None, "Foot offset is not set"
            foot_offset = getattr(self, f"{target}_foot_offset")
            if target == "human":
                foot_offset *= self.global_body_ratio

            foot_pos = (self.data.body(foot_names[0]).xpos + self.data.body(foot_names[1]).xpos) / 2
            foot_pos_z = foot_pos[2] + foot_offset
            joint.qpos[2] -= foot_pos_z

    def set_base_rotation(self):
        """Apply user-defined base Euler rotation to the human root."""
        if self.config_name is None:
            base_rot = [90, 0, 90] if self.generator_type == "bvh" else [0, 0, 0]
            self.retarget_config.base_rotation = base_rot
        else:
            base_rot = getattr(self.retarget_config, "base_rotation")
        
        base_name = self.human_generator.all_body_names[0]
        joint = self.data.joint(self.model.body(base_name).jntadr[0])
        assert len(joint.qpos) == 7

        base_quat = euler2quat(*base_rot)
        joint.qpos[3:7] = base_quat
        
        mujoco.mj_forward(self.model, self.data)

    def set_dof_pos(self):
        for key, value in self.retarget_config.body_rotate_dict.items():
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

    def save_retarget_config(self, save_config_name=None):
        assert not (save_config_name is None and self.config_name is None)
        if save_config_name is None:
            save_config_name = self.config_name

        self.retarget_config.to_yaml(
            Path(self.config_dir) / f"{save_config_name}.yaml"
        )

    def get_tracker_offset(self):
        if self._cali_qpos is None:
            self.load_cali_qpos()

        qpos_list = defaultdict(list)

        for group_name, group_value in self.retarget_config.tracker_dict.items():
            for human_tracker, robot_tracker in zip(group_value.human, group_value.robot):
                qpos = np.zeros(7)
                qpos[:3] = self.data.body(f"human_{human_tracker}").xpos - self.data.body(f"robot_{robot_tracker}").xpos
                qpos[3:] = self.data.body(f"human_{human_tracker}").xquat
                qpos_list[group_name].append(qpos)
        return qpos_list

