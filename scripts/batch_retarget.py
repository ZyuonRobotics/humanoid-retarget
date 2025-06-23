import click
from pathlib import Path
from multiprocessing import Pool, cpu_count
from functools import partial

from humanoid_retargeting.retargeter import Retargeter
from humanoid_retargeting.motion_player import PLAYER_FILE_SUFFIXES


def process_file(file_path, output_path, robot_name, generator_type, params_name, target_fps):
    click.echo(f"Processing {file_path}")
    retargeter = Retargeter(
        source_file_path=str(file_path),
        robot_name=robot_name,
        generator_type=generator_type,
        params_name=params_name,
        view=False
    )
    retargeter.run_ik()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    retargeter.save_as_npy(str(output_path), target_framerate=target_fps)


@click.command()
@click.option('--source-path', type=click.Path(exists=True), required=True,
              help='Path to the folder containing motion files.')
@click.option('--target-path', type=click.Path(), required=True,
              help='Path to save the retargeted .npy files, preserving folder structure.')
@click.option('--robot-name', type=str, required=True, help='Name of the robot.')
@click.option('--generator-type', type=str, required=True, help='Type of generator (e.g., "smpl").')
@click.option('--params-name', type=str, default='default',
              help='Name of the retargeting parameters. Default is "default".')
@click.option('--target-fps', type=int, default=100, help='Target framerate for output files. Default is 100.')
@click.option('--overwrite/--no-overwrite', default=False,
              help='Whether to overwrite existing .npy files. Default is False.')
@click.option('--pos-filter', type=str, multiple=True,
              help='Only process files whose names contain any of these keywords. Can be used multiple times.')
@click.option('--neg-filter', type=str, multiple=True,
              help='Skip files whose names contain any of these keywords. Can be used multiple times.')
@click.option('--num-processes', type=int, default=1,
              help='Number of processes to use. Set to 1 to disable multiprocessing.')
def batch_retarget(source_path, target_path, robot_name, generator_type, params_name, target_fps, overwrite,
                   pos_filter, neg_filter, num_processes):
    """
    Batch process motion files in the specified folder using Retargeter,
    convert to .npy format and save in a separate target folder with preserved directory structure.
    Uses multiprocessing when num_processes > 1.
    """

    if generator_type not in PLAYER_FILE_SUFFIXES:
        click.echo(f"Unsupported generator_type: {generator_type}")
        click.echo(f"Supported types: {list(PLAYER_FILE_SUFFIXES.keys())}")
        return

    suffix = PLAYER_FILE_SUFFIXES[generator_type]

    source_path = Path(source_path)
    motion_files = list(source_path.rglob(f"*{suffix}"))

    if not motion_files:
        click.echo(f"No motion files found with suffix '{suffix}' in {source_path}.")
        return

    # Ensure target path exists
    target_path = Path(target_path)
    target_path.mkdir(parents=True, exist_ok=True)

    # Filter files based on pos_filter and neg_filter
    filtered_files = []
    target_files = []
    for file_path in motion_files:
        if pos_filter and not any(kw.lower() in file_path.name.lower() for kw in pos_filter):
            continue
        if neg_filter and any(kw.lower() in file_path.name.lower() for kw in neg_filter):
            continue
        target_file = target_path / file_path.relative_to(source_path).with_suffix(".npy")
        if not overwrite and target_file.exists():
            continue
        filtered_files.append(file_path)
        target_files.append(target_file)

    if not filtered_files:
        click.echo("No files matched the filters.")
        return

    func = partial(
        process_file,
        robot_name=robot_name, generator_type=generator_type,params_name=params_name,target_fps=target_fps
    )

    # Use multiprocessing only if num_processes > 1
    if num_processes > 1:
        with Pool(processes=num_processes) as pool:
            pool.starmap(func, zip(filtered_files, target_files))
    else:
        # Single process mode
        for file, out_path in zip(filtered_files, target_files):
            func(file, out_path)


if __name__ == '__main__':
    batch_retarget()
