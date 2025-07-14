from humanoid_retargeting.motion_player.smpl_player import SMPLPlayer
from humanoid_retargeting.motion_player.bvh_player import BVHPlayer
from humanoid_retargeting.motion_player.player_base import MotionPlayerBase

PLAYERS = [SMPLPlayer, BVHPlayer]
PLAYERS_CLASS = {p.generator_class.generator_type: p for p in PLAYERS}
PLAYER_FILE_SUFFIXES = {p.generator_class.generator_type: p.file_suffix for p in PLAYERS}
