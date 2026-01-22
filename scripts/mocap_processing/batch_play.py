from humanoid_retargeting.motion_player import PLAYERS_CLASS, PLAYER_FILE_SUFFIXES
from humanoid_retargeting.utils.human_config import HumanConfig
import click
from pathlib import Path


@click.command()
@click.argument('input_folder', type=click.Path(exists=True, file_okay=False, dir_okay=True))
@click.option('--generator-type', type=str, default='bvh',
              help='Type of generator (e.g., bvh, smpl).', prompt="Type of generator")
@click.option('--config-file', type=click.Path(exists=True, file_okay=True, dir_okay=False), default=None,
              help='Path to template config YAML file. Will use this config and only recalculate height_adjustment.',
              required=False)
@click.option('--foot-offset', type=float, default=0.0,
              help='Custom foot offset value (overrides config file if specified).',  required=False)
@click.option('--hip-offset', type=float, default=0.0,
              help='Custom hip offset value (overrides config file if specified).', required=False)
@click.option('--draw-plot', is_flag=True, default=False,
              help='Whether to draw analysis plots for height adjustment.')
def main(input_folder, generator_type, config_file, foot_offset, hip_offset, draw_plot):
    """
    Batch process motion files in a folder to generate configs.

    Args:
        input_folder: Path to folder containing motion files
        generator_type: Type of motion file (bvh, smpl)
        config_file: Path to template config YAML file (optional). Uses this config and
                     only recalculates height_adjustment.
        foot_offset: Custom foot offset value (overrides config file if specified)
        hip_offset: Custom hip offset value (overrides config file if specified)
        draw_plot: Whether to draw analysis plots
    """
    input_path = Path(input_folder)
    player_class = PLAYERS_CLASS[generator_type]
    file_suffix = PLAYER_FILE_SUFFIXES.get(generator_type, f".{generator_type}")

    motion_files = list(input_path.rglob(f"*{file_suffix}"))
    motion_files.sort()

    if not motion_files:
        print(f"No files with suffix '{file_suffix}' found in {input_path}")
        return

    # Load template config if provided
    template_config = None
    if config_file:
        template_config = HumanConfig.from_yaml(config_file)

    print(f"Found {len(motion_files)} files to process")
    if foot_offset is not None:
        print(f"Foot offset: {foot_offset}")
    if hip_offset is not None:
        print(f"Hip offset: {hip_offset}")
    print("-" * 50)

    for idx, source_file_path in enumerate(motion_files, 1):
        print(f"\n[{idx}/{len(motion_files)}] Processing: {source_file_path.name}")
        config_path = source_file_path.with_suffix('.yaml')
        if config_path.exists():
            print(f"Config already exists, skipping: {config_path.name}")
            continue

        player = None
        try:
            player = player_class(view=False)
            player.load(source_file_path=source_file_path)
            print("Reload config:")
            if template_config is not None:
                player.human_config = template_config
                print(f"    Using {Path(config_file).name} config for {source_file_path.name}.")
            else:
                player.init_config()
                player.human_config.foot_offset = foot_offset
                player.human_config.hip_offset = hip_offset
                print(f"    Using default config for {source_file_path.name}.")
                
            player.calculate_height_adjustment(draw_plot=draw_plot)
            player.save_config(source_file_path)

        except Exception as e:
            print(f"  Error processing {source_file_path.name}: {e}")
        finally:
            if player is not None:
                player.close()

    print("\n" + "-" * 50)
    print("Batch processing complete!")


if __name__ == '__main__':
    main()
