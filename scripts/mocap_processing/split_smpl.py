from pathlib import Path
import numpy as np
import click


@click.command()
@click.option('--smpl_path', required=True, type=click.Path(exists=True, file_okay=True), help='SMPL file to split')
@click.option('--split_indices', required=True, type=str, help='Split indices (comma-separated integers, e.g., "100,200,300")')
@click.option('--clip', required=False, is_flag=True, help='Clip the smpl file to the split indices')
def main(smpl_path, split_indices, clip):
    """
    Split the smpl file into multiple files based on the split indices.
    """
    smpl_file = Path(smpl_path)
    data_dict = np.load(smpl_file)
    data_length = data_dict["poses"].shape[0]

    try:
        split_indices = [int(idx.strip()) for idx in split_indices.split(',')]
    except ValueError:
        raise click.BadParameter('split_indices must be comma-separated integers (e.g., "100,200,300")')
    
    split_indices = sorted(set(split_indices)) 
    if clip:
        start_index = split_indices[0]
        assert len(split_indices) > 1
        split_indices = split_indices[1:]
    else:
        assert split_indices[-1] < data_length
        split_indices.append(data_length)
        start_index = 0

    for i in range(len(split_indices)):
        end_index = split_indices[i]
        if end_index > data_length:
            break
        new_data = {}
        new_data["gender"] = data_dict['gender']
        new_data["mocap_framerate"] = data_dict["mocap_framerate"]
        new_data["poses"] = data_dict["poses"][start_index:end_index]
        new_data["trans"] = data_dict["trans"][start_index:end_index]
        new_data["betas"] = data_dict["betas"]
        output_path = smpl_file.parent / f"{smpl_file.stem}_{start_index}_{end_index}.npz"
        np.savez_compressed(output_path, **new_data)
        print(f"Split {start_index} to {end_index} and save to {output_path}")
        start_index = end_index

if __name__ == '__main__':
    main()