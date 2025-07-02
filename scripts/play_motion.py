from humanoid_retargeting.motion_player import PLAYERS_CLASS
import click
import os
from humanoid_retargeting import BVH_DATA_PATH

SOURCE_FILE_PATH = os.path.join(BVH_DATA_PATH, "Reallusion", "Folk Artistry - Ba Jia Jiang", '1_BJJ_General_03.bvh')

@click.command()
@click.option('--source-file-path', default=SOURCE_FILE_PATH, help='Path to the BVH file.')
@click.option('--generator-type', type=click.Choice(list(PLAYERS_CLASS.keys())), default='bvh',
              help='Type of generator (e.g., bvh, amass).')
def main(source_file_path, generator_type):
    player_class = PLAYERS_CLASS[generator_type]

    player = player_class(source_file_path=source_file_path)
    player.render()
    player.close()


if __name__ == '__main__':
    main()
