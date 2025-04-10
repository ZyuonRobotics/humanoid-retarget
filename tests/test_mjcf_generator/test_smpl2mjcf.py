import os

import mujoco
import mujoco.viewer
from hurodes.mjcf_generator.generator_base import MJCFGeneratorComposite
from hurodes.mjcf_generator.unified_generator import UnifiedMJCFGenerator
from hurodes import ROBOTS_PATH

from humanoid_retargeting import AMASS_DATA_PATH
from humanoid_retargeting.mjcf_generator.smpl2mjcf import SMPL2MJCFGenerator
from humanoid_retargeting.mjcf_generator.constants import SMPLH_JOINT_NAMES

AMASS_FILE_PATH = os.path.join(AMASS_DATA_PATH, "ACCAD", 'Female1General_c3d', "A1_-_Stand_stageii.npz")
ROBOT_EHDF_PATH = os.path.join(ROBOTS_PATH, "kuavo_s45")

def test_smpl2mjcf():
    generator = SMPL2MJCFGenerator(AMASS_FILE_PATH)
    generator.build()

    m = mujoco.MjModel.from_xml_string(generator.mjcf_str)
    d = mujoco.MjData(m)

def test_body_ratio():
    generator = SMPL2MJCFGenerator(AMASS_FILE_PATH, whole_body_ratio=1.1, body_ratio_dict={
        SMPLH_JOINT_NAMES[0]: 1,
        SMPLH_JOINT_NAMES[1]: 1.1,
        SMPLH_JOINT_NAMES[2]: [1, 1.1, 1.2]
    })
    generator.build()

    m = mujoco.MjModel.from_xml_string(generator.mjcf_str)
    d = mujoco.MjData(m)

def test_smpl2mjcf_composite():
    smpl_generator = SMPL2MJCFGenerator(AMASS_FILE_PATH)
    robot_generator = UnifiedMJCFGenerator(ROBOT_EHDF_PATH)
    composite_generator = MJCFGeneratorComposite([smpl_generator, robot_generator])
    composite_generator.build()

    m = mujoco.MjModel.from_xml_string(composite_generator.mjcf_str)
    d = mujoco.MjData(m)