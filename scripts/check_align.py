from humanoid_retargeting.aligner import Aligner
import click
import os
from humanoid_retargeting import BVH_DATA_PATH

SOURCE_FILE_PATH = os.path.join(BVH_DATA_PATH, "Reallusion", "Folk Artistry - Ba Jia Jiang", '1_BJJ_General_03.bvh')

@click.command()
@click.option('--source-file-path', default=SOURCE_FILE_PATH, help='Path to the motion file.', prompt="Path to the motion file")
@click.option('--robot-name', default='unitree_g1', help='Name of the robot.', prompt="Name of the robot")
@click.option('--generator-type', default='bvh', help='Type of generator.', prompt="Type of generator")
@click.option('--params-name', default=None, help='Name of parameters.')

def main(source_file_path, robot_name, generator_type, params_name):
    aligner = Aligner(
        source_file_path=source_file_path,
        robot_name=robot_name,
        generator_type=generator_type,
        params_name=params_name
    )

    aligner.load_cali_qpos()
    aligner.get_tracker_offset()
    aligner.render()
    if params_name is not None:
        aligner.save_retarget_params(params_name)
    else:
        aligner.save_retarget_params("default")


if __name__ == '__main__':
    main()
