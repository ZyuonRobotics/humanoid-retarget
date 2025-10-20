from humanoid_retargeting.motion_player import PLAYERS_CLASS, RobotMotionPlayer, HumanoidMotionPlayerBase
import click
from pathlib import Path
from hurodes import HumanoidRobot
from humanoid_retargeting import BVH_DATA_PATH

SOURCE_FILE_PATH = Path(BVH_DATA_PATH) / "Reallusion" / "Folk Artistry - Ba Jia Jiang" / '1_BJJ_General_03.bvh'

@click.command()
@click.argument('source_file_path', default=SOURCE_FILE_PATH)
@click.option('--generator-type', type=str, default='bvh',
              help='Type of generator (e.g., bvh, smpl, robot).', prompt="Type of generator")
@click.option('--robot-name', default='zhaplin-v0.1.3', help='Name of the robot.')
def main(source_file_path, generator_type, robot_name):
    if generator_type == "robot" and robot_name is None:
        robot_name = click.prompt("Name of the robot")
    
    if source_file_path.startswith('"') or source_file_path.startswith("'"):
        source_file_path = source_file_path[1:-1]
    
    player_class = PLAYERS_CLASS[generator_type]

    if generator_type == "robot":
        robot = HumanoidRobot.from_name(robot_name)
        player: RobotMotionPlayer = player_class(robot_name=robot_name)
        player.load(source_file_path=source_file_path, hrdf=robot.hrdf)
    else:
        player: HumanoidMotionPlayerBase = player_class()
        player.load(source_file_path=source_file_path)
    
    # player.adjust_root_height()

    player.render()
    player.close()



if __name__ == '__main__':
    main()

