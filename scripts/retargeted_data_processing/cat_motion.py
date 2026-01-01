import numpy as np
import click
from pathlib import Path


@click.command()
@click.argument('file_a', type=click.Path(exists=True))
@click.argument('file_b', type=click.Path(exists=True))
@click.argument('output_file', type=click.Path())
@click.option('--dims', '-d', default=None, 
              help='Comma-separated list of dimension indices to copy from B to A (e.g., "1,2,3"). If not specified, copies last 8 dimensions.')
def main(file_a, file_b, output_file, dims):
    """
    Merge joint_pos and joint_vel from file B into file A.
    
    By default, copies the last 8 dimensions from B to A.
    If --dims is specified (e.g., --dims 1,2,3), copies only the specified dimensions.
    """
    data_a = np.load(file_a)
    data_b = np.load(file_b)

    joint_pos_a = data_a['joint_pos']
    joint_vel_a = data_a['joint_vel']
    joint_pos_b = data_b['joint_pos']
    joint_vel_b = data_b['joint_vel']

    if joint_pos_a.shape != joint_pos_b.shape:
        raise ValueError(f"joint_pos shape mismatch: A has {joint_pos_a.shape}, B has {joint_pos_b.shape}")
    if joint_vel_a.shape != joint_vel_b.shape:
        raise ValueError(f"joint_vel shape mismatch: A has {joint_vel_a.shape}, B has {joint_vel_b.shape}")
    
    if joint_pos_a.shape[0] != joint_pos_b.shape[0]:
        raise ValueError(f"Frame number mismatch: A has {joint_pos_a.shape[0]} frames, B has {joint_pos_b.shape[0]} frames")

    total_dims = joint_pos_a.shape[1]
    
    if dims is None:
        dim_indices = list(range(total_dims - 8, total_dims))
        click.echo(f"Copying last 8 dimensions ({dim_indices[0]} to {dim_indices[-1]}) from B to A")
    else:
        try:
            dim_indices = [int(d.strip()) for d in dims.split(',')]
        except ValueError:
            raise ValueError(f"Invalid dims format: {dims}. Expected comma-separated integers (e.g., '1,2,3')")

        for idx in dim_indices:
            if idx < 0 or idx >= total_dims:
                raise ValueError(f"Dimension index {idx} out of range [0, {total_dims-1}]")
        
        click.echo(f"Copying dimensions {dim_indices} from B to A")
    
    for idx in dim_indices:
        joint_pos_a[:, idx] = joint_pos_b[:, idx]
        joint_vel_a[:, idx] = joint_vel_b[:, idx]
    
    output_data = {
        'root_trans': data_a['root_trans'],
        'root_quat': data_a['root_quat'],
        'joint_pos': joint_pos_a,
        'root_lin_vel': data_a['root_lin_vel'],
        'root_ang_vel': data_a['root_ang_vel'],
        'joint_vel': joint_vel_a,
        'frame_rate': data_a['frame_rate'],
        'frame': data_a['frame']
    }

    np.savez_compressed(output_file, **output_data)
    click.echo(f"Saved merged motion to {output_file}")


if __name__ == '__main__':
    main()