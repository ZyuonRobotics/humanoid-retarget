import os

import mujoco
import mujoco.viewer
from hurodes import ROBOTS_PATH
from hurodes.mjcf_generator.generator_base import MJCFGeneratorComposite
from hurodes.mjcf_generator.unified_generator import UnifiedMJCFGenerator

from humanoid_retargeting import BVH_DATA_PATH
from humanoid_retargeting.mjcf_generator.bvh2mjcf_generator import BVH2MJCFGenerator

BVH_FILE_PATH = os.path.join(BVH_DATA_PATH, "Reallusion", "Martial Arts - Taichi", '1_Skill.bvh')
ROBOT_EHDF_PATH = os.path.join(ROBOTS_PATH, "kuavo_s45")


def test_bvh2mjcf():
    generator = BVH2MJCFGenerator(BVH_FILE_PATH)
    generator.build()

    m = mujoco.MjModel.from_xml_string(generator.mjcf_str)
    d = mujoco.MjData(m)


def test_bvh2mjcf_parsing_end():
    generator = BVH2MJCFGenerator(BVH_FILE_PATH, parsing_end=True)
    generator.build()

    m = mujoco.MjModel.from_xml_string(generator.mjcf_str)
    d = mujoco.MjData(m)


def test_bvh2mjcf_composite():
    smpl_generator = BVH2MJCFGenerator(BVH_FILE_PATH)
    robot_generator = UnifiedMJCFGenerator(ROBOT_EHDF_PATH)
    generator = MJCFGeneratorComposite([smpl_generator, robot_generator])
    generator.build()

    m = mujoco.MjModel.from_xml_string(generator.mjcf_str)
    d = mujoco.MjData(m)
