from pipes import SOURCE

from humanoid_retargeting.retargeter import Retargeter
import click
import os
from humanoid_retargeting import BVH_DATA_PATH

SOURCE_FILE_PATH = os.path.join(BVH_DATA_PATH, "Reallusion", "Folk Artistry - Ba Jia Jiang", '1_BJJ_General_03.bvh')

@click.command()
@click.option('--source-file-path', default=SOURCE_FILE_PATH, help='Path to the BVH file.')
@click.option('--robot-name', default='unitree_g1', help='Name of the robot.')
@click.option('--generator-type', default='bvh', help='Type of generator.')
@click.option('--params-name', default='default', help='Name of parameters.')
@click.option('--view/--no-view', default=True, help='Enable or disable viewing.')
@click.option('--speed', default=1.0, help='Playback speed.')
@click.option('--offset', nargs=3, type=float, default=[0.0, 0, 0.0], help='Offset for playback.')

def main(source_file_path, robot_name, generator_type, params_name, view, speed, offset):
    retargeter = Retargeter(
        source_file_path=source_file_path,
        robot_name=robot_name,
        generator_type=generator_type,
        params_name=params_name,
        view=view
    )
    retargeter.run_ik()
    retargeter.play(speed=speed, offset=offset)
    retargeter.close()


if __name__ == '__main__':
    main()
