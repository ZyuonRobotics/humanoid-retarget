import axios from 'axios';
import { RobotInfo, RetargetConfig, MotionInfo } from '../types/config';

const API_BASE = '/api';

const client = axios.create({
  baseURL: API_BASE,
  timeout: 30000,
});

// Re-export types from types/config
export type { RobotInfo, RetargetConfig, MotionInfo };

// Config API
export const configApi = {
  getRobots: () => client.get<string[]>('/robots').then(res => res.data),

  listConfigs: (robotName: string, generatorType: string) =>
    client.get<string[]>(`/config/${robotName}/${generatorType}/configs`).then(res => res.data),

  getConfig: (robotName: string, generatorType: string, configName: string) =>
    client.get<RetargetConfig>(`/config/${robotName}/${generatorType}/${configName}`).then(res => res.data),

  saveConfig: (robotName: string, generatorType: string, configName: string, config: RetargetConfig) =>
    client.post(`/config/${robotName}/${generatorType}/${configName}`, config),

  deleteConfig: (robotName: string, generatorType: string, configName: string) =>
    client.delete(`/config/${robotName}/${generatorType}/${configName}`),

  getBodyTree: (robotName: string, generatorType: string, motionFile?: string) =>
    client.get(`/config/${robotName}/${generatorType}/body-tree`, {
      params: motionFile ? { motion_file: motionFile } : {}
    }).then(res => res.data),
};

export interface AlignPreviewResponse {
  xml: string;
  qpos: number[];
  body_names: string[];
  global_body_ratio: number;
}

// Retarget preview response
export interface RetargetPreviewResponse {
  status: string;
  output_name: string;
  robot_name: string;
  frame_num: number;
  frame_rate: number;
  body_names: string[];
  nbody: number;
  xml: string;
  body_transforms: {
    xpos: number[][][];
    xquat: number[][][];
  };
}

// Motion file tree types
export interface MotionFileInfo {
  filename: string;
  relative_path: string;
  type: 'bvh' | 'npz';
}

export interface MotionTreeNode {
  motions: MotionFileInfo[];
  subdirs: Record<string, MotionTreeNode>;
}

// Player motion data types
export interface PlayerBodyTransforms {
  xpos: number[][][];  // [frame][body][3]
  xquat: number[][][]; // [frame][body][4]
}

export interface PlayerMotionResponse {
  robot_name: string;
  motion_file: string;
  frame_num: number;
  frame_rate: number;
  frameRate?: number;  // camelCase variant from backend
  body_names: string[];
  nbody: number;
  body_transforms: PlayerBodyTransforms;
}

export interface HumanPlayerMotionResponse {
  generator_type: string;
  motion_file: string;
  frame_num: number;
  frame_rate: number;
  frameRate?: number;
  body_names: string[];
  nbody: number;
  body_transforms: PlayerBodyTransforms;
  xml: string;
  has_skin: boolean;
}

// HumanConfig for human motion player
export interface HumanConfig {
  height_adjustment: number | null;
  hip_names: string[] | null;
  hip_offset: number | null;
  foot_names: string[] | null;
  foot_offset: number | null;
  joint_adjustments: Record<string, number[]>;
}

// Model API
export const modelApi = {
  listMotions: (generatorType: string) =>
    client.get<MotionInfo[]>(`/model/motions/${generatorType}`).then(res => res.data),

  listMotionsTree: () =>
    client.get<Record<string, MotionTreeNode>>(`/model/motions/tree`).then(res => res.data),

  getMotionInfo: (generatorType: string, filename: string) =>
    client.get(`/model/motions/${generatorType}/${filename}`).then(res => res.data),

  retarget: (motionFile: string, robotName: string, generatorType: string, configName: string, outputName?: string) =>
    client.post('/model/retarget', null, {
      params: { motion_file: motionFile, robot_name: robotName, generator_type: generatorType, config_name: configName, output_name: outputName }
    }).then(res => res.data),

  retargetPreview: (motionFile: string, robotName: string, generatorType: string, configName: string, outputName?: string) =>
    client.post<RetargetPreviewResponse>('/model/retarget-preview', null, {
      params: { motion_file: motionFile, robot_name: robotName, generator_type: generatorType, config_name: configName, output_name: outputName }
    }).then(res => res.data),

  saveRetarget: () =>
    client.post('/model/save-retarget').then(res => res.data),

  getRetargetedMotion: (robotName: string, outputName: string) =>
    client.get(`/model/retarget/${robotName}/${outputName}`).then(res => res.data),

  getRobotMJCF: (robotName: string) =>
    client.get(`/model/mjcf/${robotName}`).then(res => res.data),

  getRobotMJCFWithMeshes: (robotName: string) =>
    client.get(`/model/mjcf/${robotName}/with-meshes`).then(res => res.data),

  getAlignPreview: (sourceFile: string, robotName: string, generatorType: string, retargetConfig: RetargetConfig) =>
    client.post<AlignPreviewResponse>('/model/align-preview', retargetConfig, {
      params: { source_file: sourceFile, robot_name: robotName, generator_type: generatorType }
    }).then(res => res.data),

  getHumanPreview: (sourceFile: string, generatorType: string, retargetConfig: RetargetConfig) =>
    client.post<AlignPreviewResponse>('/model/human-preview', retargetConfig, {
      params: { source_file: sourceFile, generator_type: generatorType }
    }).then(res => res.data),

  getFrameData: (robotName: string, outputName: string, frameId: number) =>
    client.get(`/model/frame/${robotName}/${outputName}/${frameId}`).then(res => res.data),

  getRobotPlayerMotionData: (robotName: string, motionFile: string) =>
    client.get<PlayerMotionResponse>(`/model/player/robot/${robotName}/motion/${motionFile}`).then(res => res.data),

  getHumanPlayerMotionData: (generatorType: string, motionFile: string, generateSkin: boolean = true) =>
    client.get<HumanPlayerMotionResponse>(`/model/player/human/${generatorType}/motion/${motionFile}`, {
      params: { generate_skin: generateSkin }
    }).then(res => res.data),

  getHumanPlayerConfig: (generatorType: string, motionFile: string) =>
    client.get<HumanConfig>(`/model/player/human/${generatorType}/config/${motionFile}`).then(res => res.data),

  saveHumanPlayerConfig: (generatorType: string, motionFile: string, config: HumanConfig) =>
    client.post(`/model/player/human/${generatorType}/config/${motionFile}`, config).then(res => res.data),

  uploadMotion: (file: File, generatorType: string = 'bvh') => {
    const formData = new FormData();
    formData.append('file', file);
    return client.post(`/model/upload/motion?generator_type=${generatorType}`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }).then(res => res.data);
  },

  uploadRobotMotion: (robotName: string, file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    return client.post(`/model/upload/robot-motion/${robotName}`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }).then(res => res.data);
  },

  uploadHumanMotion: (file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    return client.post(`/model/upload/human-motion`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }).then(res => res.data);
  },

  listRetargetedMotions: (robotName: string) =>
    client.get<string[]>(`/model/retargeted/${robotName}`).then(res => res.data),

  splitMotion: (generatorType: string, motionFile: string, splitIndices: string) =>
    client.post('/model/split-motion', null, {
      params: { generator_type: generatorType, motion_file: motionFile, split_indices: splitIndices }
    }).then(res => res.data),

  splitRobotMotion: (robotName: string, motionFile: string, splitIndices: string) =>
    client.post('/model/split-robot-motion', null, {
      params: { robot_name: robotName, motion_file: motionFile, split_indices: splitIndices }
    }).then(res => res.data),
};

export default client;
