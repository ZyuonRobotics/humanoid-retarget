import os
from pathlib import Path
import numpy as np
import click
import pickle
import c3d

def process_pkl_file(npz_file, mocap_framerate):
    data_dict = pickle.load(open(npz_file, 'rb'))
    new_data = {}
    new_data["gender"] = "neutral"
    new_data["poses"] = data_dict["fullpose"]
    new_data["trans"] = data_dict["trans"]
    new_data["betas"] = data_dict["betas"]
    new_data["mocap_framerate"] = 120.0
    np.savez_compressed(npz_file.with_suffix('.npz'), **new_data)


@click.command()
@click.option('--folder_path', required=True, type=click.Path(exists=True, file_okay=False), help='Folder containing npz files to check')
@click.option('--mocap_framerate', required=False, type=int, default=None, help='Framerate to fill in if missing (optional)')
def main(folder_path, mocap_framerate):
    """
    Recursively check all npz files in the given folder. If 'mocap_framerate' is missing,
    fill it with the provided value. If neither the npz file nor the argument provides it, raise an error.
    """
    folder_path = Path(folder_path)
    npz_files = list(folder_path.rglob('*.pkl'))
    if not npz_files:
        click.echo(f"No npz files found in: {folder_path}")
        return
    for npz_file in npz_files:
        process_pkl_file(npz_file, mocap_framerate)

if __name__ == '__main__':
    main()
