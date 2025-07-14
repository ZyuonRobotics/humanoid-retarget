import os

import mujoco
import mujoco.viewer
from hurodes import ROBOTS_PATH
from hurodes.mjcf_generator.generator_composite import MJCFGeneratorComposite
from hurodes.mjcf_generator.unified_generator import UnifiedMJCFGenerator

from humanoid_retargeting import SMPL_DATA_PATH
from humanoid_retargeting.mjcf_generator.constants import SMPLH_JOINT_NAMES
from humanoid_retargeting.mjcf_generator.smpl2mjcf_generator import SMPL2MJCFGenerator

SMPL_FILE_PATH = os.path.join(SMPL_DATA_PATH, "ACCAD", 'Female1Walking_c3d', "B1_-_stand_to_walk_stageii.npz")
ROBOT_EHDF_PATH = os.path.join(ROBOTS_PATH, "kuavo_s45")


def test_smpl2mjcf():
    generator = SMPL2MJCFGenerator(SMPL_FILE_PATH)
    generator.build()

    m = mujoco.MjModel.from_xml_string(generator.mjcf_str) # type: ignore
    d = mujoco.MjData(m) # type: ignore


def test_body_ratio():
    generator = SMPL2MJCFGenerator(SMPL_FILE_PATH, global_body_ratio=1.1, relative_body_ratio_dict={
        SMPLH_JOINT_NAMES[0]: 1,
        SMPLH_JOINT_NAMES[1]: 1.1,
        SMPLH_JOINT_NAMES[2]: [1, 1.1, 1.2]
    })
    generator.build()

    m = mujoco.MjModel.from_xml_string(generator.mjcf_str) # type: ignore
    d = mujoco.MjData(m) # type: ignore


def test_smpl2mjcf_composite():
    smpl_generator = SMPL2MJCFGenerator(SMPL_FILE_PATH)
    robot_generator = UnifiedMJCFGenerator(ROBOT_EHDF_PATH)
    composite_generator = MJCFGeneratorComposite([smpl_generator, robot_generator])
    composite_generator.build()

    m = mujoco.MjModel.from_xml_string(composite_generator.mjcf_str) # type: ignore
    d = mujoco.MjData(m) # type: ignore
