import os
from collections import defaultdict
from typing import List, Dict, Tuple, Set
import click

from humanoid_retargeting.mjcf_generator import BVH2MJCFGenerator

# Global variables
Folder_BodyTypes_Dict: Dict[str, Set[str]] = {}
Folder_SkeletonCount_Dict: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
SkeletonID_Dict: Dict[Tuple[str], str] = {}
Skeleton_Count_Dict: Dict[str, int] = defaultdict(int)

class FolderNode:
    def __init__(self, path: str):
        self.path = path
        self.children: List['FolderNode'] = []

    def is_leaf(self):
        return len(self.children) == 0

def build_folder_tree(root_path: str) -> FolderNode:
    root = FolderNode(root_path)
    for entry in os.listdir(root_path):
        full_path = os.path.join(root_path, entry)
        if os.path.isdir(full_path):
            child_node = build_folder_tree(full_path)
            root.children.append(child_node)
    return root

def assign_skeleton_id(skeleton: Tuple[str]) -> str:
    if skeleton not in SkeletonID_Dict:
        SkeletonID_Dict[skeleton] = f"Skeleton_{len(SkeletonID_Dict)}"
    return SkeletonID_Dict[skeleton]

def extract_bvh_skeleton_type(bvh_path: str) -> Tuple[str]:
    try:
        generator = BVH2MJCFGenerator(bvh_path)
        generator.build()  
        return tuple(generator.all_body_names) if generator.all_body_names else ()
    except Exception as e:
        print(f"[Error] Failed to process {bvh_path}: {e}")
        return ()

def process_node(node: FolderNode):
    folder_path = node.path
    local_types = set()
    local_skel_count: Dict[str, int] = {}

    for filename in os.listdir(folder_path):
        if filename.lower().endswith(".bvh"):
            bvh_path = os.path.join(folder_path, filename)
            skeleton = extract_bvh_skeleton_type(bvh_path)
            if skeleton:
                skel_id = assign_skeleton_id(skeleton)
                
                # Global occurences
                Skeleton_Count_Dict[skel_id] = Skeleton_Count_Dict.get(skel_id, 0) + 1
                # Local occurences
                local_skel_count[skel_id] = local_skel_count.get(skel_id, 0) + 1
                local_types.add(skel_id)

    if local_types:
        Folder_BodyTypes_Dict[folder_path] = local_types
        Folder_SkeletonCount_Dict[folder_path] = local_skel_count

    for child in node.children:
        process_node(child)

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
    root = build_folder_tree(root_folder)
    process_node(root)
    print_summary() 

if __name__ == '__main__':
    main()