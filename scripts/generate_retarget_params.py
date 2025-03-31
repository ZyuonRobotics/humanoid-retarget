import os

import mujoco
import mujoco.viewer
import click


from hurodes.mjcf_generator.generator_base import MJCFGeneratorComposite
from hurodes.mjcf_generator.unified_generator import UnifiedMJCFGenerator
from hurodes import ROBOTS_PATH
from humanoid_retargeting.mjcf_generator import BVH2MJCFGenerator, SMPL2MJCFGenerator
@click.command()
@click.option("--robot_name", prompt="Enter the robot name")
@click.option("--motion_type", prompt="Enter the motion type")
@click.option("--motion_path", prompt="Enter the motion path")
def cali_check(robot_name, motion_type, motion_path):
    if motion_type.lower() == "bvh":
        human_generator_class = BVH2MJCFGenerator
    elif motion_type.lower() == "amass":
        human_generator_class = SMPL2MJCFGenerator
    else:
        raise ValueError("Invalid motion type")

    human_generator = human_generator_class(motion_path)
    robot_generator = UnifiedMJCFGenerator(os.path.join(ROBOTS_PATH, robot_name))
    generator = MJCFGeneratorComposite([human_generator, robot_generator])
    generator.build()

    m = mujoco.MjModel.from_xml_string(generator.mjcf_str)
    d = mujoco.MjData(m)

    with open("cali_check.xml", "w") as f:
        f.write(generator.mjcf_str)

    with mujoco.viewer.launch_passive(m, d) as viewer:
        while viewer.is_running():
            mujoco.mj_step(m, d)
            viewer.sync()

if __name__ == '__main__':
    cali_check()