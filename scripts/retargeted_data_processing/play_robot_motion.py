from humanoid_retargeting.motion_player import RobotMotionPlayer
import click
from pathlib import Path
from hurodes import HumanoidRobot
from humanoid_retargeting import BVH_DATA_PATH

SOURCE_FILE_PATH = Path(BVH_DATA_PATH) / "Reallusion" / "Folk Artistry - Ba Jia Jiang" / '1_BJJ_General_03.bvh'

@click.command()
@click.argument('source_file_path', default=SOURCE_FILE_PATH)
@click.argument('robot-name', default='zhaplin-21dof')
@click.option('--plot-ref-trans', is_flag=True, default=False, help='Plot baselink Cartesian position (x, y, z)')
@click.option('--plot-ref-euler', is_flag=True, default=False, help='Plot baselink Euler angles (roll, pitch, yaw)')
@click.option('--plot-ref-joint-pos', is_flag=True, default=False, help='Plot reference joint positions')
@click.option('--plot-ref-joint-vel', is_flag=True, default=False, help='Plot reference joint velocities')
@click.option('--dims', type=str, default=None, help='Comma-separated dimensions to plot for joint positions (e.g., "0,1,2"). Plots all if not specified.')
def main(source_file_path, robot_name, plot_ref_trans, plot_ref_euler, plot_ref_joint_pos, plot_ref_joint_vel, dims):

    if source_file_path.startswith('"') or source_file_path.startswith("'"):
        source_file_path = source_file_path[1:-1]
    
    robot = HumanoidRobot.from_name(robot_name)
    player: RobotMotionPlayer = RobotMotionPlayer(robot_name=robot_name)
    player.load(source_file_path=source_file_path, hrdf=robot.hrdf)
    
    if plot_ref_joint_pos:
        dims_list = [int(d.strip()) for d in dims.split(',')] if dims is not None else None
        player.plot_ref_joint_positions(dims_list=dims_list)

    if plot_ref_joint_vel:
        dims_list = [int(d.strip()) for d in dims.split(',')] if dims is not None else None
        player.plot_ref_joint_velocities(dims_list=dims_list)

    if plot_ref_trans:
        player.plot_ref_baselink_cartesian()

    if plot_ref_euler:
        player.plot_ref_baselink_euler()
    
    # player.adjust_root_height()

    player.render()
    player.close()



if __name__ == '__main__':
    main()

