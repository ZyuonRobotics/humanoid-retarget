from humanoid_retargeting.motion_player.amass_player import AMASSPlayer
from humanoid_retargeting.motion_player.bvh_player import BVHPlayer
from humanoid_retargeting.motion_player.player_base import MotionPlayerBase

players = [AMASSPlayer, BVHPlayer]
player_class = {p.generator_class.generator_type: p for p in players}
