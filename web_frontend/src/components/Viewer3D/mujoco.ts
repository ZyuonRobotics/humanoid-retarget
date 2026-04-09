/**
 * mujoco core module
 * Wrapper for mujoco physics engine in WebAssembly
 */

import { modelApi } from '../../api/client';

// mujoco module types (will be populated when the package is loaded)
export interface MuJoCoModule {
  loadModel: (xml: string) => Promise<MuJoCoModel>;
  Model: new (xml: string) => MuJoCoModel;
  Data: new (model: MuJoCoModel) => MuJoCoData;
}

export interface MuJoCoModel {
  ptr: number;
  nq: number;
  nv: number;
  nbody: number;
  bodyNames: string[];
  bodyId: Record<string, number>;
  geomId: Record<string, number>;
}

export interface MuJoCoData {
  ptr: number;
  qpos: Float64Array;
  qvel: Float64Array;
  xpos: Float32Array;
  xquat: Float32Array;
  geomXpos: Float32Array;
}

export interface MuJoCoVisualizer {
  model: MuJoCoModel;
  data: MuJoCoData;
  scene: any;
  renderer: any;
}

// Camera and rendering types
export interface CameraConfig {
  azimuth: number;
  elevation: number;
  distance: number;
  lookat: [number, number, number];
}

export interface RenderCallbacks {
  onBodyClick?: (bodyId: number, bodyName: string) => void;
  onBodyHover?: (bodyId: number | null, bodyName: string | null) => void;
}

let mujocoModule: MuJoCoModule | null = null;
let currentModel: MuJoCoModel | null = null;
let currentData: MuJoCoData | null = null;
let currentScene: any = null;
let currentRenderer: any = null;
let currentConfig: CameraConfig = {
  azimuth: 0,
  elevation: -30,
  distance: 3,
  lookat: [0, 0, 0.5]
};

/**
 * Initialize mujoco module
 */
export async function initMuJoCoModule(): Promise<void> {
  if (mujocoModule) return;

  try {
    // Dynamic import of mujoco
    // @ts-ignore - mujoco types
    const module = await import('mujoco');
    // @ts-ignore - type mismatch between mujoco module types
    mujocoModule = await module.default();
  } catch (error) {
    console.warn('mujoco not available, using fallback renderer');
    mujocoModule = null;
  }
}

/**
 * Initialize MuJoCo with XML string and optional initial qpos
 */
export async function initMuJoCo(xmlString: string, qpos?: number[]): Promise<boolean> {
  try {
    await initMuJoCoModule();

    if (!mujocoModule) {
      console.warn('mujoco not loaded, cannot initialize');
      return false;
    }

    // Load model from XML
    currentModel = mujocoModule.Model ? new mujocoModule.Model(xmlString) : await mujocoModule.loadModel(xmlString);
    currentData = new mujocoModule.Data(currentModel);

    // Set initial qpos if provided
    if (qpos && currentData.qpos) {
      for (let i = 0; i < Math.min(qpos.length, currentData.qpos.length); i++) {
        currentData.qpos[i] = qpos[i];
      }
    }

    return true;
  } catch (error) {
    console.error('Failed to initialize MuJoCo:', error);
    return false;
  }
}

/**
 * Set qpos values
 */
export function setQPos(qpos: number[]): void {
  if (!currentData) return;

  for (let i = 0; i < Math.min(qpos.length, currentData.qpos.length); i++) {
    currentData.qpos[i] = qpos[i];
  }
}

/**
 * Get current qpos values
 */
export function getQPos(): number[] {
  if (!currentData) return [];
  return Array.from(currentData.qpos);
}

/**
 * Get body ID at screen position (for picking)
 */
export function getBodyAtPosition(_x: number, _y: number, _canvas: HTMLCanvasElement): number | null {
  if (!currentModel || !currentData) return null;

  // Simple ray casting based on mouse position
  // This is a simplified version - actual implementation depends on mujoco API
  // TODO: implement proper body picking using camera parameters and ray casting

  // For now, return null (actual body picking requires more sophisticated implementation)
  return null;
}

/**
 * Get body name from body ID
 */
export function getBodyName(bodyId: number): string | null {
  if (!currentModel) return null;
  const names = currentModel.bodyNames;
  if (bodyId >= 0 && bodyId < names.length) {
    return names[bodyId];
  }
  return null;
}

/**
 * Get body position from body ID
 */
export function getBodyPosition(bodyId: number): [number, number, number] | null {
  if (!currentModel || !currentData) return null;

  // Body positions are stored in xpos array
  // Each body has 3 values (x, y, z)
  if (bodyId < 0 || bodyId * 3 + 2 >= currentData.xpos.length) return null;

  const idx = bodyId * 3;
  return [
    currentData.xpos[idx],
    currentData.xpos[idx + 1],
    currentData.xpos[idx + 2]
  ];
}

/**
 * Highlight a body by changing its material color
 */
export function highlightBody(bodyId: number, color?: [number, number, number]): void {
  // This would modify rendering materials
  // Implementation depends on mujoco rendering API
  console.debug('Highlight body:', bodyId, color);
}

/**
 * Render the current state to canvas
 */
export function render(canvas: HTMLCanvasElement): void {
  if (!currentModel || !currentData) {
    renderFallback(canvas);
    return;
  }

  // If mujoco is available, use it for rendering
  if (mujocoModule && currentRenderer) {
    // Use mujoco renderer
    try {
      currentRenderer.render(currentScene, currentData);
    } catch (error) {
      console.error('Render error:', error);
      renderFallback(canvas);
    }
    return;
  }

  // Fallback: render using canvas 2D
  renderFallback(canvas);
}

/**
 * Fallback 2D rendering when mujoco is not available
 */
function renderFallback(canvas: HTMLCanvasElement): void {
  const ctx = canvas.getContext('2d');
  if (!ctx) return;

  const width = canvas.width;
  const height = canvas.height;

  // Clear canvas with gradient background
  const gradient = ctx.createLinearGradient(0, 0, width, height);
  gradient.addColorStop(0, '#1a1a2e');
  gradient.addColorStop(1, '#16213e');
  ctx.fillStyle = gradient;
  ctx.fillRect(0, 0, width, height);

  // Draw grid
  ctx.strokeStyle = 'rgba(255, 255, 255, 0.1)';
  ctx.lineWidth = 1;

  const gridSize = 50;
  for (let x = 0; x < width; x += gridSize) {
    ctx.beginPath();
    ctx.moveTo(x, 0);
    ctx.lineTo(x, height);
    ctx.stroke();
  }
  for (let y = 0; y < height; y += gridSize) {
    ctx.beginPath();
    ctx.moveTo(0, y);
    ctx.lineTo(width, y);
    ctx.stroke();
  }

  // Draw placeholder humanoid shape
  ctx.save();
  ctx.translate(width / 2, height / 2);

  // Scale based on camera distance
  const scale = 100 * (currentConfig.distance / 3);
  ctx.scale(scale, scale);

  // Draw simple humanoid skeleton representation
  ctx.strokeStyle = '#3a7bd5';
  ctx.lineWidth = 2 / scale;
  ctx.lineCap = 'round';

  // Torso
  ctx.beginPath();
  ctx.moveTo(0, -0.3);
  ctx.lineTo(0, 0.1);
  ctx.stroke();

  // Head
  ctx.beginPath();
  ctx.arc(0, -0.45, 0.1, 0, Math.PI * 2);
  ctx.stroke();

  // Arms
  ctx.beginPath();
  ctx.moveTo(-0.15, -0.25);
  ctx.lineTo(-0.4, 0);
  ctx.moveTo(0.15, -0.25);
  ctx.lineTo(0.4, 0);
  ctx.stroke();

  // Legs
  ctx.beginPath();
  ctx.moveTo(-0.1, 0.1);
  ctx.lineTo(-0.15, 0.5);
  ctx.moveTo(0.1, 0.1);
  ctx.lineTo(0.15, 0.5);
  ctx.stroke();

  ctx.restore();

  // Draw info text
  ctx.fillStyle = 'rgba(255, 255, 255, 0.5)';
  ctx.font = '14px monospace';
  ctx.textAlign = 'center';
  ctx.fillText('3D Preview (mujoco loading...)', width / 2, height - 20);
}

/**
 * Update camera configuration
 */
export function setCamera(config: Partial<CameraConfig>): void {
  currentConfig = { ...currentConfig, ...config };
}

/**
 * Get current camera configuration
 */
export function getCamera(): CameraConfig {
  return { ...currentConfig };
}

/**
 * Get all body names
 */
export function getBodyNames(): string[] {
  if (!currentModel) return [];
  return currentModel.bodyNames || [];
}

/**
 * Get model info
 */
export function getModelInfo(): { nq: number; nv: number; nbody: number } | null {
  if (!currentModel) return null;
  return {
    nq: currentModel.nq,
    nv: currentModel.nv,
    nbody: currentModel.nbody
  };
}

/**
 * Dispose of MuJoCo resources
 */
export function dispose(): void {
  currentModel = null;
  currentData = null;
  currentScene = null;
  currentRenderer = null;
}

/**
 * Align preview data holder
 */
export interface AlignPreviewData {
  xml: string;
  qpos: number[];
  bodyNames: string[];
  globalBodyRatio: number;
}

/**
 * Fetch align preview from backend
 */
export async function fetchAlignPreview(
  sourceFile: string,
  robotName: string,
  generatorType: string,
  retargetConfig: any
): Promise<AlignPreviewData | null> {
  try {
    const response = await modelApi.getAlignPreview(sourceFile, robotName, generatorType, retargetConfig);
    return {
      xml: response.xml,
      qpos: response.qpos,
      bodyNames: response.body_names,
      globalBodyRatio: response.global_body_ratio
    };
  } catch (error) {
    console.error('Failed to fetch align preview:', error);
    return null;
  }
}