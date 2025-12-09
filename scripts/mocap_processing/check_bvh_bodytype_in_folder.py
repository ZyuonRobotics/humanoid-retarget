import os
from collections import defaultdict
from typing import Dict, Tuple, Set, Optional
from pathlib import Path
import click

from humanoid_retargeting.mjcf_generator import BVH2MJCFGenerator

# Global variables
Folder_BodyTypes_Dict: Dict[str, Set[str]] = {}
Folder_SkeletonCount_Dict: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
SkeletonID_Dict: Dict[Tuple[str, ...], str] = {}
Skeleton_Count_Dict: Dict[str, int] = defaultdict(int)

def assign_skeleton_id(skeleton: Tuple[str, ...]) -> str:
    if skeleton not in SkeletonID_Dict:
        SkeletonID_Dict[skeleton] = f"Skeleton_{len(SkeletonID_Dict)}"
    return SkeletonID_Dict[skeleton]

def extract_bvh_skeleton_type(bvh_path: str) -> Optional[Tuple[str, ...]]:
    try:
        generator = BVH2MJCFGenerator(bvh_path)
        generator.build()  
        body_names = generator.all_body_names
        if not body_names:
            return None
        # all_body_names is guaranteed to contain only strings, no None values
        return tuple(body_names)  # type: ignore
    except Exception as e:
        print(f"[Error] Failed to process {bvh_path}: {e}")
        return None

def process_folder(folder_path: Path):
    """Process a single folder and its subfolders recursively."""
    local_types = set()
    local_skel_count: Dict[str, int] = {}

    # Process BVH files in current folder
    for bvh_file in folder_path.glob("*.bvh"):
        skeleton = extract_bvh_skeleton_type(str(bvh_file))
        if skeleton:
            skel_id = assign_skeleton_id(skeleton)
            
            # Global occurrences
            Skeleton_Count_Dict[skel_id] = Skeleton_Count_Dict.get(skel_id, 0) + 1
            # Local occurrences
            local_skel_count[skel_id] = local_skel_count.get(skel_id, 0) + 1
            local_types.add(skel_id)

    if local_types:
        Folder_BodyTypes_Dict[str(folder_path)] = local_types
        Folder_SkeletonCount_Dict[str(folder_path)] = local_skel_count

    # Process subfolders recursively
    for subfolder in folder_path.iterdir():
        if subfolder.is_dir():
            process_folder(subfolder)

def print_summary():
    print("\n========= Folder Skeleton Type Summary =========")
    total_bvh_folders = 0
    for folder, type_ids in Folder_BodyTypes_Dict.items():
        print(f"\n[Folder] {folder}")
        print(f"  → Unique skeleton types: {len(type_ids)}")
        for skel_id in sorted(type_ids):
            count = Folder_SkeletonCount_Dict.get(folder, {}).get(skel_id, 0)
            print(f"    - {skel_id}  {count}")
        total_bvh_folders += 1

    print("\n========= Skeleton ID Legend =========")
    for skel, skel_id in SkeletonID_Dict.items():
        print(f"{skel_id}: {skel}")

    print("\n========= Skeleton Usage Statistics =========")
    for skel_id, count in Skeleton_Count_Dict.items():
        print(f"{skel_id}: {count} BVH files")
    
    print("\n========= Overall Summary =========")
    print(f"Total folders with BVH: {total_bvh_folders}")
    print(f"Total unique skeleton types in all folders: {len(SkeletonID_Dict)}")

@click.command()
@click.option('--root-folder', prompt='Enter root folder path',
              help='Root folder containing BVH subfolders.')
def main(root_folder):
    """Scan a root BVH folder and print per-folder skeleton structure summary."""
    print(f"[INFO] Scanning BVH folder: {root_folder}")
    root_path = Path(root_folder)
    if not root_path.exists():
        print(f"[ERROR] Folder {root_folder} does not exist!")
        return
    if not root_path.is_dir():
        print(f"[ERROR] {root_folder} is not a directory!")
        return
    
    process_folder(root_path)
    print_summary() 

if __name__ == '__main__':
    main()