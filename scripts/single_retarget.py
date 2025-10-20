import click

from humanoid_retargeting.retargeter import Retargeter

@click.command()
@click.argument('source-file-path')
@click.argument('robot-name')
@click.option('--generator-type', default='bvh', help='Type of generator.', prompt="Type of generator")
@click.option('--params-name', default='default', help='Name of parameters.', prompt="Name of parameters")
@click.option('--view/--no-view', default=True, help='Enable or disable viewing.')
@click.option('--speed', default=1.0, help='Playback speed.')
@click.option('--offset', nargs=3, type=float, default=[0.0, 1.0, 0.0], help='Offset for playback.')

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
    #retargeter.save_as_npz('/home/zym/.humanoid_retargeting/retargeted/smpl/ldwalk.npz')


if __name__ == '__main__':
    main()
