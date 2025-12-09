import click

from humanoid_retargeting.aligner import Aligner

@click.command()
@click.argument('source-file-path')
@click.argument('robot-name')
@click.option('--generator-type', default='bvh', help='Type of generator.', prompt="Type of generator")
@click.option('--params-name', default=None, help='Name of parameters.', prompt="Name of parameters")

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


if __name__ == '__main__':
    main()
