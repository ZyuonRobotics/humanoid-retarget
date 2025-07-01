import numpy as np
from scipy.spatial.transform import Rotation

from humanoid_retargeting.mjcf_generator.bvh2mjcf_generator import BVH2MJCFGenerator
from humanoid_retargeting.motion_player.humanoid_player_base import HumanoidMotionPlayerBase


class BVHPlayer(HumanoidMotionPlayerBase):
    generator_class = BVH2MJCFGenerator
    file_suffix = "bvh"

    def __init__(
            self,
            source_file_path,
            view=True,
            rotating_baselink=True,
            global_body_ratio=1.0,
            relative_body_ratio_dict=None
    ):
        super().__init__(
            source_file_path=source_file_path,
            view=view,
            global_body_ratio=global_body_ratio,
            relative_body_ratio_dict=relative_body_ratio_dict
        )
        self.rotating_baselink = rotating_baselink

    def parse_bvh_file(self):
        with open(self.source_file_path, 'r') as f:
            lines = f.readlines()
            for i in range(len(lines)):
                if lines[i].startswith('Frame Time'):
                    frame_time = float(lines[i].split('Frame Time:')[1].strip())
                    frame_rate = 1 / frame_time
                    break
            motion_data = []
            for line in lines[i + 1:]:
                data = [float(x) for x in line.split()]
                if len(data) == 0:
                    break
                motion_data.append(np.array(data).reshape(1, -1))
            motion_data = np.concatenate(motion_data, axis=0)
        return frame_rate, motion_data

    def parse_channel(self, joint_idx, array, channel):
        pos, euler, pos_order, euler_order = [], [], "", ""

        for i, c in enumerate(channel):
            assert c[0] in ['X', 'Y', 'Z'] and c[1:] in ['position', 'rotation']
            if c[1:] == 'position':
                pos.append(array[:, i] / 100)
                pos_order += c[0]
            else:
                euler.append(array[:, i])
                euler_order += c[0]

        if len(pos) == 0:
            pos_array = None
        else:
            pos_array = np.stack(pos, axis=1)
            pos_array = pos_array[:, np.array([pos_order.index('X'), pos_order.index('Y'), pos_order.index('Z')])]
            if self.rotating_baselink and joint_idx == 0:
                pos_array += self.generator.joint_offsets[0]
                pos_array = Rotation.from_euler('x', 90, degrees=True).apply(pos_array)

        euler_array = np.stack(euler, axis=1)
        r = Rotation.from_euler(euler_order, euler_array, degrees=True)
        if self.rotating_baselink and joint_idx == 0:
            r = Rotation.from_euler('x', 90, degrees=True) * r

        quat_array = r.as_quat()
        quat_array = np.roll(quat_array, shift=1, axis=1)

        return pos_array, quat_array

    def load_motion_file(self):
        self._frame_rate, self.motion_data = self.parse_bvh_file()

        qpos = []
        begin_idx = 0
        for joint_idx, channel in enumerate(self.generator.channels):
            pos, quat = self.parse_channel(joint_idx, self.motion_data[:, begin_idx:begin_idx + len(channel)], channel)
            begin_idx += len(channel)
            if joint_idx == 0:
                qpos.append(pos)
            qpos.append(quat)

        self._ref_qpos = np.concatenate(qpos, axis=1)


if __name__ == '__main__':
    import os
    from humanoid_retargeting import BVH_DATA_PATH

    BVH_FILE_PATH = os.path.join(BVH_DATA_PATH, "Reallusion", "Folk Artistry - Ba Jia Jiang", 'test.bvh')

    player = BVHPlayer(source_file_path=BVH_FILE_PATH)
    player.render()
    player.close()
