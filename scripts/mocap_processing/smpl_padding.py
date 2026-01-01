from pathlib import Path
import numpy as np
import click
import yaml


@click.command()
@click.option('--smpl_path', required=True, type=click.Path(exists=True, file_okay=True), help='SMPL file to extend')
@click.option('--frames', default=60, type=int, help='Number of frames to add at the beginning and end (default: 60)')
@click.option('--yaml_path', default=None, type=click.Path(exists=True, file_okay=True), help='YAML file containing pose and trans data for padding frames')
@click.option('--output_path', default=None, type=click.Path(), help='Output path. If not specified, will add "_extended" suffix to input file')
def main(smpl_path, frames, yaml_path, output_path):
    smpl_file = Path(smpl_path)
    data_dict = np.load(smpl_file)
    
    assert "poses" in data_dict, f"poses not found in {smpl_file}"
    assert "trans" in data_dict, f"trans not found in {smpl_file}"
    
    original_frames = data_dict["poses"].shape[0]
    poses_dim = data_dict["poses"].shape[1]
    
    if frames <= 0:
        click.echo("Error: frames must be positive")
        return
    
    if yaml_path is not None:
        yaml_file = Path(yaml_path)
        with open(yaml_file, 'r') as f:
            yaml_data = yaml.safe_load(f)
        
        assert "poses" in yaml_data, f"poses not found in {yaml_file}"
        assert "trans" in yaml_data, f"trans not found in {yaml_file}"
        
        padding_pose = np.array(yaml_data["poses"], dtype=np.float32)
        padding_trans = np.array(yaml_data["trans"], dtype=np.float32)
        
        if padding_pose.shape[0] != poses_dim:
            raise ValueError(f"Pose dimension mismatch: YAML has {padding_pose.shape[0]}, but SMPL file has {poses_dim}")
        
        if padding_trans.shape[0] != 3:
            raise ValueError(f"Trans dimension must be 3, but got {padding_trans.shape[0]}")
        
        click.echo(f"Using pose and trans from YAML file: {yaml_file}")
    else:
        padding_pose = data_dict["poses"][0].copy()
        padding_trans = data_dict["trans"][0].copy()
        click.echo("Using first frame for padding")
    
    first_frame_trans = data_dict["trans"][0].copy()
    last_frame_trans = data_dict["trans"][-1].copy()
    
    new_data = {}
    
    for key in data_dict.keys():
        if key == "poses":
            new_poses = np.concatenate([
                np.tile(padding_pose, (frames, 1)),
                data_dict["poses"],
                np.tile(padding_pose, (frames, 1))
            ], axis=0)
            new_data[key] = new_poses
        elif key == "trans":
            first_frames_trans = padding_trans.copy()
            first_frames_trans[:2] = first_frame_trans[:2]
            first_frames_trans = np.tile(first_frames_trans, (frames, 1))
            last_frames_trans = padding_trans.copy()
            last_frames_trans[:2] = last_frame_trans[:2]
            last_frames_trans = np.tile(last_frames_trans, (frames, 1))
            
            new_trans = np.concatenate([
                first_frames_trans,
                data_dict["trans"],
                last_frames_trans
            ], axis=0)
            new_data[key] = new_trans
        else:
            new_data[key] = data_dict[key].copy()
    
    if output_path is None:
        output_path = smpl_file.parent / f"{smpl_file.stem}_extended.npz"
    else:
        output_path = Path(output_path)
    
    np.savez_compressed(output_path, **new_data)
    click.echo(f"Extended SMPL file saved to: {output_path}")
    click.echo(f"  - Original frames: {original_frames}")
    click.echo(f"  - Added {frames} frames at the beginning")
    click.echo(f"  - Added {frames} frames at the end")
    click.echo(f"  - Total frames: {original_frames + 2 * frames}")


if __name__ == '__main__':
    main()

