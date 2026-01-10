import os
from pathlib import Path
import numpy as np
import click
import pickle
import torch
from scipy.spatial.transform import Rotation

def process_pkl_file(npz_file, mocap_framerate):
    data_dict = pickle.load(open(npz_file, 'rb'))
    new_data = {}
    new_data["gender"] = "neutral"
    new_data["poses"] = data_dict["fullpose"]
    new_data["trans"] = data_dict["trans"]
    new_data["betas"] = data_dict["betas"]
    new_data["mocap_framerate"] = mocap_framerate
    np.savez_compressed(npz_file.with_suffix('.npz'), **new_data)

def process_gvhmr_file(pt_file, mocap_framerate):
    data = torch.load(pt_file)
    smplx_data = data["smpl_params_global"]

    rot_x_90 = Rotation.from_euler('x', 90, degrees=True)
    global_orient_rot = Rotation.from_rotvec(smplx_data["global_orient"])
    global_orient_rotated = rot_x_90 * global_orient_rot
    global_orient_rotvec = global_orient_rotated.as_rotvec()
    
    transl_rotated = rot_x_90.apply(smplx_data["transl"])

    poses = np.concatenate([global_orient_rotvec, smplx_data["body_pose"], np.zeros_like(smplx_data["body_pose"][:, :3]), np.zeros_like(smplx_data["body_pose"][:, :3])], axis=1)
    new_data = {
        "gender": "female",
        "poses": poses,
        "trans": transl_rotated,
        "betas": smplx_data["betas"][0],
        "mocap_framerate": mocap_framerate
    }
    np.savez_compressed(pt_file.with_suffix('.npz'), **new_data)

@click.command()
@click.option('--folder_path', required=True, type=click.Path(exists=True, file_okay=False), help='Folder containing npz files to check')
@click.option('--mocap_framerate', required=False, type=int, default=30, help='Framerate to fill in if missing (optional)')
@click.option('--process_type', required=False, type=str, default='pkl', help='Process type (pkl or gvhmr)')
def main(folder_path, mocap_framerate, process_type):
    """
    Recursively check all npz files in the given folder. If 'mocap_framerate' is missing,
    fill it with the provided value. If neither the npz file nor the argument provides it, raise an error.
    """
    folder_path = Path(folder_path)

    if process_type == 'pkl':
        npz_files = list(folder_path.rglob('*.pkl'))
        if not npz_files:
            click.echo(f"No npz files found in: {folder_path}")
            return
        for npz_file in npz_files:
            process_pkl_file(npz_file, mocap_framerate)
            print(f"Processed {npz_file}")
    elif process_type == 'gvhmr':
        pt_files = list(folder_path.rglob('*.pt'))
        if not pt_files:
            click.echo(f"No pt files found in: {folder_path}")
            return
        for pt_file in pt_files:
            process_gvhmr_file(pt_file, mocap_framerate)
            print(f"Processed {pt_file}")
    else:
        raise ValueError(f"Invalid process type: {process_type}")

if __name__ == '__main__':
    main()
