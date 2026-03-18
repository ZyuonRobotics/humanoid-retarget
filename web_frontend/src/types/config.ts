export interface RobotInfo {
  name: string;
  generator_type: string;
}

export interface TrackerConfig {
  human: string[];
  robot: string[];
  position_cost: number;
  orientation_cost: number;
}

export interface RetargetConfig {
  base_x_shift: number;
  base_y_shift: number;
  base_rotation: number[];
  body_rotate_dict: Record<string, number[]>;
  extra_body_ratio: number[];
  relative_body_ratio_dict: Record<string, number[]>;
  damping_cost: number;
  tracker_dict: Record<string, TrackerConfig>;
}

export interface MotionInfo {
  filename: string;
  type: string;
  frame_count?: number;
  frame_rate?: number;
}

export const defaultRetargetConfig: RetargetConfig = {
  base_x_shift: 0,
  base_y_shift: 0,
  base_rotation: [0, 0, 0],
  body_rotate_dict: {},
  extra_body_ratio: [1, 1, 1],
  relative_body_ratio_dict: {},
  damping_cost: 5.0,
  tracker_dict: {},
};
