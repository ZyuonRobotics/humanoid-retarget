from humanoid_retargeting.motion_player import PLAYERS_CLASS, HumanoidMotionPlayerBase
import click
from pathlib import Path
from humanoid_retargeting import BVH_DATA_PATH

SOURCE_FILE_PATH = Path(BVH_DATA_PATH) / "Reallusion" / "Folk Artistry - Ba Jia Jiang" / '1_BJJ_General_03.bvh'

@click.command()
@click.argument('source_file_path', default=SOURCE_FILE_PATH)
@click.option('--generator-type', type=str, default='bvh',
              help='Type of generator (e.g., bvh, smpl).', prompt="Type of generator")
def main(source_file_path, generator_type):
    if source_file_path.startswith('"') or source_file_path.startswith("'"):
        source_file_path = Path(source_file_path[1:-1])
    else:
        source_file_path = Path(source_file_path)
    
    player_class = PLAYERS_CLASS[generator_type]

    player: HumanoidMotionPlayerBase = player_class()
    player.load(source_file_path=source_file_path)
    
    if player.human_params.height_adjustment is None:
        player.calculate_height_adjustment(draw_plot=True)

    if not source_file_path.with_suffix('.json').exists():
        player.save_config(source_file_path)

    player.adjust_height_adjustment()
    player.render()
    player.close()



if __name__ == '__main__':
    main()

