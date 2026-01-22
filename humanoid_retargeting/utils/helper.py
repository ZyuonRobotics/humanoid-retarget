from pathlib import Path
from typing import Optional

from humanoid_retargeting import MOCAP_DATA_PATH


def find_config_file(source_file_path: str) -> Optional[Path]:
    source_path = Path(source_file_path)
    current_dir = source_path.parent

    config_path = source_path.with_suffix('.yaml')
    if config_path.exists():
        return config_path

    while current_dir.name != "mocap" and current_dir != current_dir.parent:
        dir_config_path = current_dir.with_suffix('.yaml')
        if dir_config_path.exists():
            return dir_config_path
        current_dir = current_dir.parent

    return None

def check_mocap_path(source_file_path: str) -> bool:
    if not Path(source_file_path).exists():
        return False
    source_path = Path(source_file_path).resolve()
    mocap_path = MOCAP_DATA_PATH.resolve()
    try:
        source_path.relative_to(mocap_path)
        return True
    except ValueError:
        return False
