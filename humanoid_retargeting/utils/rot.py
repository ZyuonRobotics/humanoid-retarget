from scipy.spatial.transform import Rotation
import numpy as np

def euler2quat(x: float, y: float, z: float) -> np.ndarray:
    rot = Rotation.from_euler('xyz', [x, y, z], degrees=True)
    return rot.as_quat()[[3, 0, 1, 2]]
