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

  getRetargetedMotion: (outputName: string) =>
    client.get(`/model/retarget/${outputName}`).then(res => res.data),

  getRobotMJCF: (robotName: string) =>
    client.get(`/model/mjcf/${robotName}`).then(res => res.data),

  getRobotMJCFWithMeshes: (robotName: string) =>
    client.get(`/model/mjcf/${robotName}/with-meshes`).then(res => res.data),

  getAlignPreview: (sourceFile: string, robotName: string, generatorType: string, retargetConfig: RetargetConfig) =>
    client.post<AlignPreviewResponse>('/model/align-preview', retargetConfig, {
      params: { source_file: sourceFile, robot_name: robotName, generator_type: generatorType }
    }).then(res => res.data),

  getFrameData: (outputName: string, frameId: number) =>
    client.get(`/model/frame/${outputName}/${frameId}`).then(res => res.data),

  uploadMotion: (file: File, generatorType: string = 'bvh') => {
    const formData = new FormData();
    formData.append('file', file);
    return client.post(`/model/upload/motion?generator_type=${generatorType}`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }).then(res => res.data);
  },
};

export default client;
