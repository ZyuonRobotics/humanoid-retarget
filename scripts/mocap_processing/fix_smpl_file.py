import os
from pathlib import Path
import numpy as np
import click

def process_npz_file(npz_file, mocap_framerate):
    """
    Check and fix a single npz file. If 'mocap_framerate' is missing, fill it with the provided value.
    If neither the npz file nor the argument provides it, raise an error.
    """
    with np.load(npz_file, allow_pickle=True) as data:
        data_dict = {k: data[k] for k in data.files}

    assert "poses" in data_dict, f"poses not found in {npz_file}"
    assert "trans" in data_dict, f"trans not found in {npz_file}"
    assert "betas" in data_dict, f"betas not found in {npz_file}"
    if "mocap_framerate" not in data_dict and "mocap_frame_rate" not in data_dict:
        if mocap_framerate is not None:
            click.echo(f"[Warning] {npz_file} is missing mocap_framerate, filled with {mocap_framerate}")
            data_dict["mocap_framerate"] = mocap_framerate
            np.savez_compressed(npz_file, **data_dict)
        else:
            raise ValueError(f"mocap_framerate not found in {npz_file}")

@click.command()
@click.option('--folder_path', required=True, type=click.Path(exists=True, file_okay=False), help='Folder containing npz files to check')
@click.option('--mocap_framerate', required=False, type=int, default=None, help='Framerate to fill in if missing (optional)')
def main(folder_path, mocap_framerate):
    """
    Recursively check all npz files in the given folder. If 'mocap_framerate' is missing,
    fill it with the provided value. If neither the npz file nor the argument provides it, raise an error.
    """
    folder_path = Path(folder_path)
    npz_files = list(folder_path.rglob('*.npz'))
    if not npz_files:
        click.echo(f"No npz files found in: {folder_path}")
        return
    for npz_file in npz_files:
        process_npz_file(npz_file, mocap_framerate)

if __name__ == '__main__':
    main()
