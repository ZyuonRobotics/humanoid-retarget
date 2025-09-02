from humanoid_retargeting.motion_player.smpl_player import SMPLPlayer
from humanoid_retargeting.motion_player.bvh_player import BVHPlayer
from humanoid_retargeting.motion_player.robot_motion_player import RobotMotionPlayer
from humanoid_retargeting.motion_player.robot_peroid_player import RobotPeriodPlayer
from humanoid_retargeting.motion_player.humanoid_player_base import HumanoidMotionPlayerBase

PLAYERS = [SMPLPlayer, BVHPlayer]
PLAYERS_CLASS = {p.generator_class.generator_type: p for p in PLAYERS}
PLAYER_FILE_SUFFIXES = {p.generator_class.generator_type: p.file_suffix for p in PLAYERS}

PLAYERS_CLASS["robot"] = RobotMotionPlayer
PLAYER_FILE_SUFFIXES["robot"] = "npz"

PLAYERS_CLASS["robot_period"] = RobotPeriodPlayer
PLAYER_FILE_SUFFIXES["robot_period"] = "json"
