from pathlib import Path

import mujoco
import mujoco.viewer
from hurodes.generators.mjcf_generator.mjcf_generator_composite import MJCFGeneratorComposite
from hurodes.generators.mjcf_generator.mjcf_humanoid_generator import MJCFHumanoidGenerator

from humanoid_retargeting import SMPL_DATA_PATH
from humanoid_retargeting.mjcf_generator.constants import SMPLH_JOINT_NAMES
from humanoid_retargeting.mjcf_generator.smpl2mjcf_generator import SMPL2MJCFGenerator

SMPL_FILE_PATH = Path(SMPL_DATA_PATH) / "ACCAD" / 'Female1Walking_c3d' / "B1_-_stand_to_walk_stageii.npz"


def test_smpl2mjcf():
    generator = SMPL2MJCFGenerator()
    generator.load(SMPL_FILE_PATH)
    generator.generate()

    m = mujoco.MjModel.from_xml_string(generator.xml_str) # type: ignore
    d = mujoco.MjData(m) # type: ignore


def test_body_ratio():
    generator = SMPL2MJCFGenerator(global_body_ratio=1.1, relative_body_ratio_dict={
        SMPLH_JOINT_NAMES[0]: 1,
        SMPLH_JOINT_NAMES[1]: 1.1,
        SMPLH_JOINT_NAMES[2]: [1, 1.1, 1.2]
    })
    generator.load(SMPL_FILE_PATH)
    generator.generate()

    m = mujoco.MjModel.from_xml_string(generator.xml_str) # type: ignore
    d = mujoco.MjData(m) # type: ignore

def test_smpl2mjcf_composite():
    smpl_generator = SMPL2MJCFGenerator()
    smpl_generator.load(SMPL_FILE_PATH)
    robot_generator = MJCFHumanoidGenerator.from_robot_name("zhaplin-21dof")
    composite_generator = MJCFGeneratorComposite([smpl_generator, robot_generator])
    composite_generator.generate(relative_mesh_path=False)

    m = mujoco.MjModel.from_xml_string(composite_generator.xml_str) # type: ignore
    d = mujoco.MjData(m) # type: ignore

