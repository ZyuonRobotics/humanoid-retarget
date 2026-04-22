/**
 * mujoco core module
 * Wrapper for mujoco physics engine in WebAssembly
 */

import { modelApi } from '../../api/client';
import { ThreeScene } from './ThreeScene';

// mujoco module types (will be populated when the package is loaded)
export interface MuJoCoModule {
  Model: {
    load_from_xml: (xmlPath: string) => Promise<MuJoCoModel>;
    loadFromXML?: (xmlPath: string) => Promise<MuJoCoModel>;
  };
  MjModel?: {
    loadFromXML: (xmlPath: string) => Promise<MuJoCoModel>;
  };
  MjData?: new (model: MuJoCoModel) => MuJoCoData;
  State?: new (model: MuJoCoModel) => MuJoCoState;
  Simulation?: new (model: MuJoCoModel, state: MuJoCoState) => MuJoCoSimulation;
  FS: {
    mkdir: (path: string) => void;
    mount: (fs: any, opts: any, mountpoint: string) => void;
    writeFile: (path: string, data: string | Uint8Array) => void;
    readdir: (path: string) => string[];
    stat: (path: string) => any;
    unlink: (path: string) => void;
    rmdir: (path: string) => void;
    isDir: (mode: number) => boolean;
    analyzePath: (path: string) => { exists: boolean };
  };
  MEMFS: any;
  mj_forward: (model: MuJoCoModel, data: MuJoCoData) => void;
  mj_resetData: (model: MuJoCoModel, data: MuJoCoData) => void;
  mjtGeom: {
    mjGEOM_SPHERE: { value: number };
    mjGEOM_CAPSULE: { value: number };
    mjGEOM_CYLINDER: { value: number };
    mjGEOM_BOX: { value: number };
    mjGEOM_ELLIPSOID: { value: number };
    mjGEOM_MESH: { value: number };
  };
  mjtJoint: {
    mjJNT_HINGE: { value: number };
    mjJNT_BALL: { value: number };
  };
}

export interface MuJoCoModel {
  names: Uint8Array;
  nq: number;
  nv: number;
  nbody: number;
  ngeom: number;
  body_mass: Float64Array;
  body_ipos: Float64Array;
  body_iquat: Float64Array;
  body_inertia: Float64Array;
  geom_group: Int32Array;
  geom_bodyid: Int32Array;
  geom_type: Int32Array;
  geom_size: Float64Array;
  geom_pos: Float64Array;
  geom_quat: Float64Array;
  geom_rgba: Float32Array;
  geom_dataid: Int32Array;
  name_bodyadr: Int32Array;
  name_meshadr: Int32Array;
  mesh_vertadr: Int32Array;
  mesh_vertnum: Int32Array;
  mesh_faceadr: Int32Array;
  mesh_facenum: Int32Array;
  mesh_vert: Float32Array;
  mesh_normal: Float32Array;
  mesh_face: Int32Array;
  name_geomsadr: Int32Array;
  njnt: number;
  jnt_type: Int32Array;
  jnt_bodyid: Int32Array;
  jnt_pos: Float64Array;
  jnt_axis: Float64Array;
  getOptions?: () => { timestep: number };
}

export interface MuJoCoData {
  qpos: Float64Array;
  qvel: Float64Array;
  xpos: Float64Array;
  xquat: Float64Array;
  qfrc_applied: Float64Array;
  forward?: () => void;
}

export interface MuJoCoState {
  delete?: () => void;
}

export interface MuJoCoSimulation {
  xpos: Float64Array;
  xquat: Float64Array;
  qpos: Float64Array;
  qvel: Float64Array;
  resetData: () => void;
  forward: () => void;
  step: () => void;
  free: () => void;
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

export let mujocoModule: MuJoCoModule | null = null;
export let currentModel: MuJoCoModel | null = null;
export let currentData: MuJoCoData | MuJoCoSimulation | null = null;
let currentScene: ThreeScene | null = null;
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
    // Dynamic import from mujoco-js npm package (same as robot_viewer)
    const load_mujoco = (await import('mujoco-js/dist/mujoco_wasm.js')).default;
    const loaded: any = await load_mujoco();

    // Setup virtual file system
    loaded.FS.mkdir('/working');
    loaded.FS.mount(loaded.MEMFS, { root: '.' }, '/working');

    mujocoModule = loaded as MuJoCoModule;
  } catch (error) {
    console.warn('mujoco not available:', error);
    mujocoModule = null;
  }
}

/**
 * Load robot model with mesh files (for robot-only display)
 */
export async function loadRobotModel(
  _robotName: string,
  xml: string,
  meshes: Record<string, string> // base64 encoded mesh files
): Promise<boolean> {
  try {
    await initMuJoCoModule();

    if (!mujocoModule) {
      console.warn('mujoco not loaded, cannot initialize');
      return false;
    }

    // Clear any existing model
    dispose();

    // Write XML to VFS
    const xmlPath = '/working/robot.xml';
    // Modify meshdir to point to /working since files are in VFS, not filesystem
    const modifiedXml = xml
      .replace(/meshdir="[^"]*"/, 'meshdir="/working"')
      .replace(/texturedir="[^"]*"/, 'texturedir="/working"');
    mujocoModule.FS.writeFile(xmlPath, modifiedXml);

    // Write mesh files to VFS
    for (const [filename, base64Data] of Object.entries(meshes)) {
      const binaryData = Uint8Array.from(atob(base64Data), c => c.charCodeAt(0));
      const meshPath = `/working/${filename}`;
      mujocoModule.FS.writeFile(meshPath, binaryData);
    }

    // Load model
    if (mujocoModule.Model?.load_from_xml) {
      currentModel = await mujocoModule.Model.load_from_xml(xmlPath);
    } else if (mujocoModule.MjModel?.loadFromXML) {
      currentModel = mujocoModule.MjModel.loadFromXML(xmlPath) as any;
    }
    if (!currentModel) {
      console.error('Failed to load model');
      return false;
    }

    // Create data with MjData constructor
    if (mujocoModule.MjData) {
      currentData = new mujocoModule.MjData(currentModel) as any;
    } else {
      console.error('MjData constructor not found');
      return false;
    }

    // Reset and forward to compute initial positions
    if (mujocoModule.mj_resetData && currentModel && currentData) {
      mujocoModule.mj_resetData(currentModel, currentData as any);
    }
    if (mujocoModule.mj_forward && currentModel && currentData) {
      mujocoModule.mj_forward(currentModel, currentData as any);
    }

    return true;
  } catch (error) {
    console.error('Failed to load robot model:', error);
    return false;
  }
}

/**
 * Load align preview (robot + human combined model)
 */
export async function loadAlignPreview(
  sourceFile: string,
  robotName: string,
  generatorType: string,
  retargetConfig: any
): Promise<AlignPreviewData | null> {
  try {
    await initMuJoCoModule();

    if (!mujocoModule) {
      console.warn('mujoco not loaded');
      return null;
    }

    // Get align preview from backend
    const response = await modelApi.getAlignPreview(sourceFile, robotName, generatorType, retargetConfig);

    // Clear any existing model
    dispose();

    // Write XML to VFS
    const xmlPath = '/working/align.xml';
    // Modify meshdir to point to /working since files are in VFS
    const modifiedXml = response.xml
      .replace(/meshdir="[^"]*"/, 'meshdir="/working"')
      .replace(/texturedir="[^"]*"/, 'texturedir="/working"');
    mujocoModule.FS.writeFile(xmlPath, modifiedXml);

    // Load model - use consistent MjModel/MjData API
    if (mujocoModule.MjModel?.loadFromXML) {
      currentModel = await mujocoModule.MjModel.loadFromXML(xmlPath);
    } else if (mujocoModule.Model?.load_from_xml) {
      currentModel = await mujocoModule.Model.load_from_xml(xmlPath);
    }
    if (!currentModel) {
      throw new Error('Failed to load model');
    }

    // Create data using MjData constructor (consistent with loadRobotModel)
    if (mujocoModule.MjData) {
      currentData = new mujocoModule.MjData(currentModel) as any;
    } else {
      throw new Error('MjData constructor not found');
    }

    // Set initial qpos
    if (currentData && response.qpos) {
      for (let i = 0; i < Math.min(response.qpos.length, currentData.qpos.length); i++) {
        currentData.qpos[i] = response.qpos[i];
      }
      // Forward to apply qpos using mj_forward
      if (mujocoModule.mj_forward && currentModel && currentData) {
        mujocoModule.mj_forward(currentModel, currentData as any);
      }
    }

    return {
      xml: response.xml,
      qpos: response.qpos,
      bodyNames: response.body_names,
      globalBodyRatio: response.global_body_ratio
    };
  } catch (error) {
    console.error('Failed to load align preview:', error);
    return null;
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

    // Clear any existing model
    dispose();

    // Write XML to VFS
    const xmlPath = '/working/model.xml';
    // Modify meshdir to point to /working since files are in VFS, not filesystem
    const modifiedXml = xmlString
      .replace(/meshdir="[^"]*"/, 'meshdir="/working"')
      .replace(/texturedir="[^"]*"/, 'texturedir="/working"');
    mujocoModule.FS.writeFile(xmlPath, modifiedXml);

    // Load model (compatible with old and new API)
    try {
      if (mujocoModule.MjModel?.loadFromXML) {
        currentModel = await mujocoModule.MjModel.loadFromXML(xmlPath);
      } else if (mujocoModule.Model?.load_from_xml) {
        currentModel = await mujocoModule.Model.load_from_xml(xmlPath);
      } else {
        throw new Error('Cannot find MuJoCo model loading method');
      }
      if (!currentModel) {
        throw new Error('Failed to load model');
      }

      // Create data using MjData constructor (same as loadRobotModel)
      if (mujocoModule.MjData) {
        currentData = new mujocoModule.MjData(currentModel) as any;
      } else {
        throw new Error('MjData constructor not found');
      }
    } catch (loadError) {
      console.error('MuJoCo model loading error:', loadError);
      throw loadError;
    }

    // Set initial qpos if provided
    if (qpos && currentData) {
      for (let i = 0; i < Math.min(qpos.length, currentData.qpos.length); i++) {
        currentData.qpos[i] = qpos[i];
      }
      // Forward to apply qpos
      if (mujocoModule.mj_forward && currentModel && currentData) {
        mujocoModule.mj_forward(currentModel, currentData as any);
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
  return null;
}

/**
 * Get body name from body ID
 */
export function getBodyName(bodyId: number): string | null {
  if (!currentModel) return null;

  const names_array = currentModel.names;
  if (!names_array) return null;

  const name_adr = currentModel.name_bodyadr;
  if (!name_adr || bodyId >= name_adr.length) return null;

  const start_idx = name_adr[bodyId];
  let end_idx = start_idx;
  while (end_idx < names_array.length && names_array[end_idx] !== 0) {
    end_idx++;
  }

  if (start_idx >= end_idx || start_idx >= names_array.length) return null;

  const bytes = names_array.subarray(start_idx, end_idx);
  const decoder = new TextDecoder('utf-8');
  return decoder.decode(bytes);
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
  console.debug('Highlight body:', bodyId, color);
}

/**
 * Initialize Three.js scene for rendering
 */
export function initThreeScene(canvas: HTMLCanvasElement): ThreeScene | null {
  try {
    // Dispose old scene if exists
    if (currentScene) {
      currentScene.dispose();
    }

    // Create new ThreeScene
    currentScene = new ThreeScene(canvas);

    // If model is already loaded, create scene
    if (mujocoModule && currentModel && currentData) {
      currentScene.createScene(mujocoModule, currentModel, currentData as MuJoCoSimulation);
    }

    return currentScene;
  } catch (error) {
    console.error('Failed to initialize ThreeScene:', error);
    return null;
  }
}

/**
 * Start Three.js rendering loop
 */
export function startRendering(): void {
  if (currentScene) {
    currentScene.start();
  }
}

/**
 * Stop Three.js rendering loop
 */
export function stopRendering(): void {
  if (currentScene) {
    currentScene.stop();
  }
}

/**
 * Render the current state (legacy function - now uses ThreeScene)
 */
export function render(canvas: HTMLCanvasElement): void {
  // If ThreeScene is available and has model loaded, it's already rendering
  if (currentScene && currentModel && currentData) {
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
  if (currentScene) {
    currentScene.setCamera(config);
  }
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
  if (!currentModel || !currentModel.nbody) return [];
  const names: string[] = [];
  for (let i = 0; i < currentModel.nbody; i++) {
    const name = getBodyName(i);
    names.push(name || `body_${i}`);
  }
  return names;
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
  if (currentScene) {
    currentScene.clearScene();
  }
  currentModel = null;
  currentData = null;
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
