from pathlib import Path

import mujoco
import mujoco.viewer
from hurodes.generators.mjcf_generator.mjcf_generator_composite import MJCFGeneratorComposite
from hurodes.generators.mjcf_generator.mjcf_humanoid_generator import MJCFHumanoidGenerator

from humanoid_retargeting import BVH_DATA_PATH
from humanoid_retargeting.mjcf_generator.bvh2mjcf_generator import BVH2MJCFGenerator

BVH_FILE_PATH = Path(BVH_DATA_PATH) / "Reallusion" / "Martial Arts - Taichi" / '1_Skill.bvh'


def test_bvh2mjcf():
    generator = BVH2MJCFGenerator()
    generator.load(BVH_FILE_PATH)
    generator.generate()

    m = mujoco.MjModel.from_xml_string(generator.xml_str) # type: ignore
    d = mujoco.MjData(m) # type: ignore


def test_bvh2mjcf_parsing_end():
    generator = BVH2MJCFGenerator(parsing_end=True)
    generator.load(BVH_FILE_PATH)
    generator.generate()

    m = mujoco.MjModel.from_xml_string(generator.xml_str) # type: ignore
    d = mujoco.MjData(m) # type: ignore

def test_bvh2mjcf_composite():
    smpl_generator = BVH2MJCFGenerator()
    smpl_generator.load(BVH_FILE_PATH)
    robot_generator = MJCFHumanoidGenerator.from_robot_name("zhaplin-21dof")
    generator = MJCFGeneratorComposite([smpl_generator, robot_generator])
    generator.generate(relative_mesh_path=False)

    m = mujoco.MjModel.from_xml_string(generator.xml_str) # type: ignore
    d = mujoco.MjData(m) # type: ignore

