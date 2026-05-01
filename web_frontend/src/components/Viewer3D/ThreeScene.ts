/**
 * ThreeScene - Three.js rendering for MuJoCo models
 * Adapted from robot_viewer's SceneManager
 */

import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import { MuJoCoModule, MuJoCoModel, MuJoCoSimulation } from './mujoco';
import {
  transformMeshVerticesM2T,
  transformMeshNormalsM2T
} from './coord';

export interface PlayerMotionUpdate {
  xpos: number[][][];
  xquat: number[][][];
  frameNum: number;
  frameRate: number;
  nbody: number;
}

export type PlayerFrameCallback = (frame: number) => void;

export interface PerformanceSettings {
  geometryDetail: number;
  shadowMapSize: number;
  maxPixelRatio: number;
  antialiasing: boolean;
}

export class ThreeScene {
  private canvas: HTMLCanvasElement;
  private scene: THREE.Scene;
  private camera: THREE.PerspectiveCamera;
  private renderer: THREE.WebGLRenderer;
  private controls: OrbitControls;
  private performanceSettings: PerformanceSettings;

  // MuJoCo data
  private model: MuJoCoModel | null = null;
  private simulation: MuJoCoSimulation | null = null;
  private bodies: Map<number, THREE.Group> = new Map();
  private mujocoRoot: THREE.Group | null = null;
  private worldBodyMeshes: THREE.Mesh[] = [];

  // On-demand rendering flags
  private _dirty = false;
  private _renderingPaused = false;

  // Lights and ground
  private directionalLight: THREE.DirectionalLight | null = null;
  private groundPlane: THREE.Mesh | null = null;
  private referenceGrid: THREE.GridHelper | null = null;

  // Instance ID for debugging
  private instanceId: number = ThreeScene.nextInstanceId++;
  private static nextInstanceId = 0;

  // Animation
  private animationFrameId: number | null = null;
  private isRunning = false;

  // Render loop
  private _renderLoopId: number | null = null;

  // Player motion data (pre-computed from backend)
  private playerMotionUpdate: PlayerMotionUpdate | null = null;
  private playerCurrentFrame = 0;
  private playerLastTime = 0;
  private playerFrameCallback: PlayerFrameCallback | null = null;

  // Skin visibility toggle (for humanoid models)
  private showSkin = true;
  private skinMeshes: THREE.Mesh[] = [];
  private skinGeometries: THREE.BufferGeometry[] = [];

  // Track model mode (combined, human-only, or robot-only)
  private hasRobotPrefix = false;
  private hasHumanPrefix = false;

  // Track visibility state for human model (needed for skin toggle)
  private humanVisible = true;

  constructor(canvas: HTMLCanvasElement, performanceSettings?: PerformanceSettings) {
    console.log(`ThreeScene[${this.instanceId}]: constructor called`);
    this.canvas = canvas;

    // Use provided settings or defaults
    this.performanceSettings = performanceSettings || {
      geometryDetail: 32,
      shadowMapSize: 2048,
      maxPixelRatio: Infinity,
      antialiasing: true,
    };

    // Create scene
    this.scene = new THREE.Scene();
    this.scene.background = new THREE.Color(0x505050);

    // Create camera (FOV 75 like robot_viewer)
    let width = canvas.clientWidth;
    let height = canvas.clientHeight;

    // Fallback to reasonable defaults if canvas has no size yet
    if (width === 0 || height === 0) {
      console.warn('ThreeScene: canvas has zero size, using defaults');
      width = 800;
      height = 600;
    }

    this.camera = new THREE.PerspectiveCamera(75, width / height, 0.1, 1000);
    this.camera.position.set(2, 2, 2);
    this.camera.lookAt(0, 0, 0);

    // Create renderer
    this.renderer = new THREE.WebGLRenderer({
      canvas: canvas,
      antialias: this.performanceSettings.antialiasing
    });
    this.renderer.setSize(width, height);
    const pixelRatio = Math.min(window.devicePixelRatio, this.performanceSettings.maxPixelRatio);
    this.renderer.setPixelRatio(pixelRatio);
    this.renderer.shadowMap.enabled = true;
    this.renderer.shadowMap.type = THREE.PCFSoftShadowMap;

    // Create controls (exactly like robot_viewer)
    this.controls = new OrbitControls(this.camera, canvas);
    this.controls.enableDamping = false;
    this.controls.enablePan = true;
    this.controls.panSpeed = 1.0;
    this.controls.enableZoom = true;
    this.controls.enableRotate = true;
    this.controls.screenSpacePanning = true;
    this.controls.target.set(0, 0, 0);

    // Mark as needing render on controls change
    this.controls.addEventListener('change', () => this.redraw());

    // Set mouse buttons to match robot_viewer
    if (this.controls.mouseButtons) {
      this.controls.mouseButtons.LEFT = THREE.MOUSE.ROTATE;
      this.controls.mouseButtons.MIDDLE = THREE.MOUSE.DOLLY;
      this.controls.mouseButtons.RIGHT = THREE.MOUSE.PAN;
    }

    // Setup lights
    this.setupLights();

    // Setup ground plane
    this.setupGroundPlane();

    // Handle resize
    this.handleResize = this.handleResize.bind(this);
    window.addEventListener('resize', this.handleResize);

    // Start continuous render loop
    this.startRenderLoop();

    // Render immediately to show initial scene
    this.redraw();

    // Trigger a resize after a short delay to ensure proper sizing
    setTimeout(() => this.handleResize(), 100);
  }

  // ==================== Render Loop ====================

  /**
   * Start continuous render loop (borrowed from urdf-loaders implementation)
   */
  startRenderLoop() {
    const renderLoop = () => {
      // Only render when needed (controlled by _dirty flag)
      if (this._dirty) {
        this.renderer.render(this.scene, this.camera);
        this._dirty = false;
      }
      this._renderLoopId = requestAnimationFrame(renderLoop);
    };
    renderLoop();
  }

  stopRenderLoop() {
    if (this._renderLoopId) {
      cancelAnimationFrame(this._renderLoopId);
      this._renderLoopId = null;
    }
  }

  /**
   * Mark scene as needing re-render (on-demand rendering)
   * Also updates body positions from simulation or player motion before rendering
   */
  redraw() {
    // Update body positions from simulation or player motion
    if (this.playerMotionUpdate) {
      this.updateBodiesFromPlayerMotion();
    } else {
      this.updateBodiesFromSimulation();
    }
    this._dirty = true;
  }

  /**
   * Render immediately (for scenes requiring immediate update)
   */
  render() {
    if (this._renderingPaused) {
      return;
    }
    this.renderer.render(this.scene, this.camera);
    this._dirty = false;
  }

  // ==================== Lights & Environment ====================

  private setupLights(): void {
    // Ambient light
    const ambient = new THREE.AmbientLight(0xffffff, 0.6);
    this.scene.add(ambient);

    // Directional light (sun)
    this.directionalLight = new THREE.DirectionalLight(0xffffff, 0.8);
    this.directionalLight.position.set(5, 10, 5);
    this.directionalLight.castShadow = true;
    this.directionalLight.shadow.mapSize.width = this.performanceSettings.shadowMapSize;
    this.directionalLight.shadow.mapSize.height = this.performanceSettings.shadowMapSize;
    this.directionalLight.shadow.camera.near = 0.5;
    this.directionalLight.shadow.camera.far = 50;
    this.directionalLight.shadow.camera.left = -10;
    this.directionalLight.shadow.camera.right = 10;
    this.directionalLight.shadow.camera.top = 10;
    this.directionalLight.shadow.camera.bottom = -10;
    this.scene.add(this.directionalLight);

    // Fill light
    const fill = new THREE.DirectionalLight(0xffffff, 0.3);
    fill.position.set(-5, 3, -5);
    this.scene.add(fill);
  }

  private setupGroundPlane(): void {
    // Ground plane
    const groundGeometry = new THREE.PlaneGeometry(20, 20);
    const groundMaterial = new THREE.MeshPhongMaterial({
      color: 0x2a2a4a,
      depthWrite: true
    });
    this.groundPlane = new THREE.Mesh(groundGeometry, groundMaterial);
    this.groundPlane.rotation.x = -Math.PI / 2;
    this.groundPlane.position.y = 0;
    this.groundPlane.receiveShadow = true;
    this.scene.add(this.groundPlane);

    // Grid helper
    this.referenceGrid = new THREE.GridHelper(20, 20, 0x444466, 0x333355);
    this.referenceGrid.position.y = 0.001;
    this.scene.add(this.referenceGrid);
  }

  private handleResize(): void {
    const width = this.canvas.clientWidth;
    const height = this.canvas.clientHeight;

    if (width === 0 || height === 0 || !isFinite(width) || !isFinite(height)) {
      return;
    }

    this.camera.aspect = width / height;
    this.camera.updateProjectionMatrix();
    this.renderer.setSize(width, height, true);
    const pixelRatio = Math.min(window.devicePixelRatio, this.performanceSettings.maxPixelRatio);
    this.renderer.setPixelRatio(pixelRatio);

    this.render();
  }

  // ==================== Model Loading ====================

  /**
   * Create scene from MuJoCo model
   */
  public createScene(mujoco: MuJoCoModule, model: MuJoCoModel, simulation: MuJoCoSimulation): void {
    console.log(`ThreeScene[${this.instanceId}]: createScene called, model nbody=${model.nbody}`);

    // Clear old scene first
    this.clearScene();

    // Store model and simulation
    this.model = model;
    this.simulation = simulation;

    // Create root group
    this.mujocoRoot = new THREE.Group();
    this.mujocoRoot.name = 'MuJoCoRoot';
    this.scene.add(this.mujocoRoot);

    this.bodies.clear();

    const textDecoder = new TextDecoder('utf-8');
    const namesArray = new Uint8Array(model.names);

    // First pass: detect model mode by checking for prefixes
    this.hasRobotPrefix = false;
    this.hasHumanPrefix = false;
    this.humanVisible = true;
    for (let b = 0; b < model.nbody; b++) {
      const bodyAdr = model.name_bodyadr[b];
      let endIdx = bodyAdr;
      while (endIdx < namesArray.length && namesArray[endIdx] !== 0) {
        endIdx++;
      }
      if (bodyAdr < endIdx && bodyAdr < namesArray.length) {
        const nameBuffer = namesArray.subarray(bodyAdr, endIdx);
        const bodyName = textDecoder.decode(nameBuffer);
        if (bodyName.startsWith('robot_')) this.hasRobotPrefix = true;
        if (bodyName.startsWith('human_')) this.hasHumanPrefix = true;
      }
    }

    // Iterate through all geoms and create meshes
    for (let g = 0; g < model.ngeom; g++) {
      const group = model.geom_group[g];
      if (group >= 4) continue; // Skip collision geoms (group 3+)

      const bodyId = model.geom_bodyid[g];
      const geomType = model.geom_type[g];
      const size = [
        model.geom_size[g * 3 + 0],
        model.geom_size[g * 3 + 1],
        model.geom_size[g * 3 + 2]
      ];

      // Create or get body group
      if (!this.bodies.has(bodyId)) {
        const bodyGroup = new THREE.Group();

        // Get body name
        const bodyAdr = model.name_bodyadr[bodyId];
        let endIdx = bodyAdr;
        while (endIdx < namesArray.length && namesArray[endIdx] !== 0) {
          endIdx++;
        }
        if (bodyAdr < endIdx && bodyAdr < namesArray.length) {
          const nameBuffer = namesArray.subarray(bodyAdr, endIdx);
          bodyGroup.name = textDecoder.decode(nameBuffer);
        } else {
          bodyGroup.name = `body_${bodyId}`;
        }
        bodyGroup.userData.bodyId = bodyId;

        this.bodies.set(bodyId, bodyGroup);
        this.mujocoRoot.add(bodyGroup);
      }

      const bodyGroup = this.bodies.get(bodyId)!;

      // Track if this is a human body based on body name and model mode
      // - Combined mode (human+robot): human bodies have 'human_' prefix
      // - Human-only mode: no prefixes, all bodies (except world) are human
      // - Robot-only mode: bodies may have 'robot_' prefix or no prefix
      let isHumanBody = false;
      if (this.hasHumanPrefix) {
        // Combined mode: explicit human_ prefix
        isHumanBody = bodyGroup.name.startsWith('human_');
      } else if (!this.hasRobotPrefix && bodyId > 0) {
        // Human-only mode: no prefixes at all, all non-world bodies are human
        isHumanBody = true;
      }
      // else: robot-only mode, isHumanBody stays false

      // Create geometry
      let geometry: THREE.BufferGeometry;
      const detail = this.performanceSettings.geometryDetail;
      const detailLow = Math.max(8, Math.floor(detail / 2));

      if (geomType === mujoco.mjtGeom.mjGEOM_SPHERE.value) {
        geometry = new THREE.SphereGeometry(size[0], detail, detail);
      } else if (geomType === mujoco.mjtGeom.mjGEOM_CAPSULE.value) {
        geometry = new THREE.CapsuleGeometry(size[0], size[1] * 2.0, detailLow, detailLow);
      } else if (geomType === mujoco.mjtGeom.mjGEOM_CYLINDER.value) {
        geometry = new THREE.CylinderGeometry(size[0], size[0], size[1] * 2.0, detail);
      } else if (geomType === mujoco.mjtGeom.mjGEOM_BOX.value) {
        geometry = new THREE.BoxGeometry(size[0] * 2.0, size[2] * 2.0, size[1] * 2.0);
      } else if (geomType === mujoco.mjtGeom.mjGEOM_ELLIPSOID.value) {
        geometry = new THREE.SphereGeometry(1, detail, detail);
      } else if (geomType === mujoco.mjtGeom.mjGEOM_MESH.value) {
        geometry = this.createMeshGeometry(model, model.geom_dataid[g]);
      } else {
        geometry = new THREE.SphereGeometry(size[0] || 0.1, Math.max(8, Math.floor(detail / 2)), Math.max(8, Math.floor(detail / 2)));
      }

      // Create material from rgba
      const rgba = [
        model.geom_rgba[g * 4 + 0],
        model.geom_rgba[g * 4 + 1],
        model.geom_rgba[g * 4 + 2],
        model.geom_rgba[g * 4 + 3]
      ];

      const material = new THREE.MeshPhongMaterial({
        color: new THREE.Color(rgba[0], rgba[1], rgba[2]),
        transparent: rgba[3] < 1.0,
        opacity: rgba[3],
        shininess: 50,
        specular: new THREE.Color(0.3, 0.3, 0.3)
      });

      // Create mesh
      const mesh = new THREE.Mesh(geometry, material);
      mesh.castShadow = true;
      mesh.receiveShadow = true;

      // Mesh position relative to body frame
      // MuJoCo: (x, y, z) → three.js: (x, z, -y)
      mesh.position.set(
        model.geom_pos[g * 3 + 0],
        model.geom_pos[g * 3 + 2],
        -model.geom_pos[g * 3 + 1]
      );

      // Mesh rotation
      // MuJoCo quaternion (w, x, y, z) → three.js quaternion (x, y, z, w)
      mesh.quaternion.set(
        model.geom_quat[g * 4 + 1],
        model.geom_quat[g * 4 + 3],
        -model.geom_quat[g * 4 + 2],
        model.geom_quat[g * 4 + 0]
      );

      // Handle ellipsoid scale
      if (geomType === mujoco.mjtGeom.mjGEOM_ELLIPSOID.value) {
        mesh.scale.set(size[0], size[2], size[1]);
      }

      bodyGroup.add(mesh);

      // Track human body meshes (parametric geoms) for visibility toggle
      // When skin is present, hide parametric geoms
      if (isHumanBody) {
        this.skinMeshes.push(mesh);
      }

      // Track world body meshes for centerModel calculation but don't render them
      if (bodyId === 0) {
        mesh.visible = false;
        this.worldBodyMeshes.push(mesh);
      }
    }

    // Create skin meshes if present
    if (model.nskin && model.nskin > 0) {
      this.createSkinMeshes(mujoco, model);
    }

    // Update initial body positions from simulation before centering
    this.updateBodiesFromSimulation();

    // Center model at ground level
    this.centerModel();
  }

  /**
   * Create mesh geometry from MuJoCo mesh data
   */
  private createMeshGeometry(model: MuJoCoModel, meshId: number): THREE.BufferGeometry {
    const geometry = new THREE.BufferGeometry();

    // Get vertex data
    const vertAdr = model.mesh_vertadr[meshId];
    const vertNum = model.mesh_vertnum[meshId];
    const vertexBuffer = model.mesh_vert.subarray(
      vertAdr * 3,
      (vertAdr + vertNum) * 3
    );

    // Convert MuJoCo coord to Three.js coord using utility
    const transformedVerts = transformMeshVerticesM2T(vertexBuffer, vertNum);
    const vertsCopy = new Float32Array(transformedVerts);

    // Get normal data
    const normalBuffer = model.mesh_normal.subarray(
      vertAdr * 3,
      (vertAdr + vertNum) * 3
    );
    const transformedNormals = transformMeshNormalsM2T(normalBuffer, vertNum);
    const normalsCopy = new Float32Array(transformedNormals);

    // Get triangle data
    const faceAdr = model.mesh_faceadr[meshId];
    const faceNum = model.mesh_facenum[meshId];
    const triangleBuffer = model.mesh_face.subarray(
      faceAdr * 3,
      (faceAdr + faceNum) * 3
    );

    geometry.setAttribute('position', new THREE.BufferAttribute(vertsCopy, 3));
    geometry.setAttribute('normal', new THREE.BufferAttribute(normalsCopy, 3));
    geometry.setIndex(Array.from(triangleBuffer));
    geometry.computeVertexNormals();

    return geometry;
  }

  /**
   * Create skin meshes from MuJoCo skin data
   */
  private createSkinMeshes(_mujoco: MuJoCoModule, model: MuJoCoModel): void {
    if (!model.nskin || model.nskin === 0) return;

    console.log(`Creating ${model.nskin} skin mesh(es)`);

    for (let s = 0; s < model.nskin; s++) {
      const geometry = new THREE.BufferGeometry();

      // Get vertex data (for now assume single skin)
      const vertNum = model.nskinvert;

      // Create vertex buffer (will be updated by updateSkinVertices)
      const vertices = new Float32Array(vertNum * 3);

      // Get face data
      const faceNum = model.nskinface;
      const faces = new Uint32Array(faceNum * 3);
      for (let f = 0; f < faceNum * 3; f++) {
        faces[f] = model.skin_face[f];
      }

      geometry.setAttribute('position', new THREE.BufferAttribute(vertices, 3));
      geometry.setIndex(new THREE.BufferAttribute(faces, 1));

      // Get skin color
      const rgba = [
        model.skin_rgba[s * 4 + 0],
        model.skin_rgba[s * 4 + 1],
        model.skin_rgba[s * 4 + 2],
        model.skin_rgba[s * 4 + 3]
      ];

      const material = new THREE.MeshPhongMaterial({
        color: new THREE.Color(rgba[0], rgba[1], rgba[2]),
        transparent: rgba[3] < 1.0,
        opacity: rgba[3],
        shininess: 30,
        specular: new THREE.Color(0.2, 0.2, 0.2),
        side: THREE.DoubleSide
      });

      const mesh = new THREE.Mesh(geometry, material);
      mesh.castShadow = true;
      mesh.receiveShadow = true;
      mesh.visible = this.showSkin;

      // Store bone binding info for animation
      mesh.userData.skinId = s;
      mesh.userData.boneAdr = model.skin_boneadr[s];
      mesh.userData.boneNum = model.skin_bonenum[s];

      this.mujocoRoot!.add(mesh);
      this.skinGeometries.push(geometry);

      console.log(`Skin mesh created: ${vertNum} vertices, ${faceNum} faces, ${mesh.userData.boneNum} bones`);
    }
  }

  /**
   * Center model so it sits on the ground
   */
  private centerModel(): void {
    if (!this.model || !this.mujocoRoot) {
      console.log(`ThreeScene[${this.instanceId}]: centerModel skipped, model=${!!this.model}, mujocoRoot=${!!this.mujocoRoot}`);
      return;
    }

    // Update environment and fit camera
    this.updateEnvironment(true);
  }

  /**
   * Update environment (adjust ground position and shadows, update camera focus)
   * @param fitCamera - Whether to auto-adjust camera view
   */
  private updateEnvironment(fitCamera: boolean): void {
    const model = this.model;
    if (!model || !this.mujocoRoot) {
      return;
    }

    // Force update world matrix
    this.mujocoRoot.updateMatrixWorld(true);

    // Calculate model's bounding box in scene global coordinate system
    const bboxGlobal = new THREE.Box3();
    bboxGlobal.setFromObject(this.mujocoRoot, true);

    if (bboxGlobal.isEmpty()) {
      return;
    }

    const center = bboxGlobal.getCenter(new THREE.Vector3());
    const size = bboxGlobal.getSize(new THREE.Vector3());
    const minY = 0; 

    // Update ground position to model lowest point
    if (this.groundPlane) {
      this.groundPlane.position.y = minY;
    }

    // Update grid position
    if (this.referenceGrid) {
      this.referenceGrid.position.y = minY + 0.001;
      this.referenceGrid.updateMatrixWorld(true);
    }

    // If camera adjustment needed, perform auto-zoom and positioning
    if (fitCamera) {
      this.fitCameraToModel(bboxGlobal, center, size);
    }

    // Update directional light shadow camera
    const dirLight = this.directionalLight;
    if (dirLight && dirLight.castShadow) {
      // Use bounding sphere to set shadow camera range
      const sphere = bboxGlobal.getBoundingSphere(new THREE.Sphere());
      const minmax = sphere.radius;

      const cam = dirLight.shadow.camera;
      cam.left = cam.bottom = -minmax;
      cam.right = cam.top = minmax;

      // Make directional light follow model center
      const offset = dirLight.position.clone().sub(dirLight.target.position);
      dirLight.target.position.copy(center);
      dirLight.position.copy(center).add(offset);

      cam.updateProjectionMatrix();
    }

    this.redraw();
  }

  /**
   * Auto-adjust camera position to fit model size
   * View angle: oblique from side-back (looking at model from side-back)
   */
  private fitCameraToModel(_bbox: THREE.Box3, center: THREE.Vector3, size: THREE.Vector3): void {
    // Calculate model's maximum dimension
    const maxDim = Math.max(size.x, size.y, size.z);

    if (maxDim < 0.001) {
      return;
    }

    // Calculate appropriate camera distance (based on FOV and model size)
    const fov = this.camera.fov * (Math.PI / 180);
    const distanceMultiplier = 1.8; // robot model uses 1.8x
    const distance = maxDim / (2 * Math.tan(fov / 2)) * distanceMultiplier;

    // Side-back oblique view:
    // - From right-back (X positive + Z negative)
    // - Slightly looking down (Y positive)
    // Standard oblique angle: horizontal 135 degrees (back-side), vertical about 35 degrees
    const horizontalAngle = Math.PI * 3 / 4;  // 135 degrees (right-back)
    const verticalAngle = Math.PI / 6;        // 30 degrees (slightly looking down)

    // Calculate camera position (relative to model center)
    const cameraOffset = new THREE.Vector3(
      distance * Math.cos(verticalAngle) * Math.sin(horizontalAngle),
      distance * Math.sin(verticalAngle),
      -distance * Math.cos(verticalAngle) * Math.cos(horizontalAngle)
    );

    // Set camera position and target
    this.camera.position.copy(center).add(cameraOffset);
    this.controls.target.copy(center);

    // Update controls and camera
    this.controls.update();
    this.camera.updateProjectionMatrix();

    this.redraw();
  }

  /**
   * Update body positions from simulation (called every frame in animation loop)
   */
  public setShowSkin(show: boolean): void {
    this.showSkin = show;

    // If we have skin geometries, toggle between skin and parametric geoms
    if (this.skinGeometries.length > 0) {
      // Show/hide skin meshes, but only if human model is visible
      this.mujocoRoot?.children.forEach(child => {
        if (child instanceof THREE.Mesh && child.userData.skinId !== undefined) {
          child.visible = show && this.humanVisible;
        }
      });

      // Hide/show parametric geoms (inverse of skin visibility)
      for (const mesh of this.skinMeshes) {
        if (this.humanVisible) {
          mesh.visible = !show;
        } else {
          mesh.visible = false;
        }
      }
    } else {
      // No skin available, just toggle parametric geoms
      for (const mesh of this.skinMeshes) {
        mesh.visible = show;
      }
    }

    this._dirty = true;
  }

  public getShowSkin(): boolean {
    return this.showSkin;
  }

  /**
   * Update skin mesh vertices based on bone transforms
   */
  private updateSkinVertices(): void {
    if (!this.model || !this.simulation || this.skinGeometries.length === 0) {
      return;
    }

    const model = this.model;
    const simulation = this.simulation;

    this.mujocoRoot?.children.forEach(child => {
      if (!(child instanceof THREE.Mesh) || child.userData.skinId === undefined) {
        return;
      }

      const geometry = child.geometry as THREE.BufferGeometry;
      const boneAdr = child.userData.boneAdr;
      const boneNum = child.userData.boneNum;

      const positionAttr = geometry.getAttribute('position');
      const positions = positionAttr.array as Float32Array;

      // Initialize all positions to zero for weighted blending
      positions.fill(0);

      // Apply bone transforms with skinning weights
      for (let b = 0; b < boneNum; b++) {
        const boneIdx = boneAdr + b;
        const bodyId = model.skin_bonebodyid[boneIdx];

        // Get bone bind pose (in MuJoCo coords)
        const bindPosX = model.skin_bonebindpos[boneIdx * 3 + 0];
        const bindPosY = model.skin_bonebindpos[boneIdx * 3 + 1];
        const bindPosZ = model.skin_bonebindpos[boneIdx * 3 + 2];

        const bindQuatW = model.skin_bonebindquat[boneIdx * 4 + 0];
        const bindQuatX = model.skin_bonebindquat[boneIdx * 4 + 1];
        const bindQuatY = model.skin_bonebindquat[boneIdx * 4 + 2];
        const bindQuatZ = model.skin_bonebindquat[boneIdx * 4 + 3];

        // Get current body pose (in MuJoCo coords)
        const bodyPosX = simulation.xpos[bodyId * 3 + 0];
        const bodyPosY = simulation.xpos[bodyId * 3 + 1];
        const bodyPosZ = simulation.xpos[bodyId * 3 + 2];

        const bodyQuatW = simulation.xquat[bodyId * 4 + 0];
        const bodyQuatX = simulation.xquat[bodyId * 4 + 1];
        const bodyQuatY = simulation.xquat[bodyId * 4 + 2];
        const bodyQuatZ = simulation.xquat[bodyId * 4 + 3];

        // Get vertices influenced by this bone
        const vertAdr = model.skin_bonevertadr[boneIdx];
        const vertNum = model.skin_bonevertnum[boneIdx];

        for (let v = 0; v < vertNum; v++) {
          const vertId = model.skin_bonevertid[vertAdr + v];
          const weight = model.skin_bonevertweight[vertAdr + v];

          if (weight < 0.001) continue;

          // Get original vertex in MuJoCo coords (bind pose)
          const origX = model.skin_vert[vertId * 3 + 0];
          const origY = model.skin_vert[vertId * 3 + 1];
          const origZ = model.skin_vert[vertId * 3 + 2];

          // Transform vertex from bind pose to current pose
          // 1. Subtract bind position (to bone local space)
          let localX = origX - bindPosX;
          let localY = origY - bindPosY;
          let localZ = origZ - bindPosZ;

          // 2. Apply inverse bind rotation (quaternion conjugate)
          const invBindQuat = { w: bindQuatW, x: -bindQuatX, y: -bindQuatY, z: -bindQuatZ };
          const rotated1 = this.rotateByQuat(localX, localY, localZ, invBindQuat);

          // 3. Apply current body rotation
          const bodyQuat = { w: bodyQuatW, x: bodyQuatX, y: bodyQuatY, z: bodyQuatZ };
          const rotated2 = this.rotateByQuat(rotated1.x, rotated1.y, rotated1.z, bodyQuat);

          // 4. Add current body position
          const newX = rotated2.x + bodyPosX;
          const newY = rotated2.y + bodyPosY;
          const newZ = rotated2.z + bodyPosZ;

          // Convert to Three.js coords
          // MuJoCo: (x, y, z) → Three.js: (x, z, -y)
          const threeX = newX;
          const threeY = newZ;
          const threeZ = -newY;

          // Accumulate weighted position
          positions[vertId * 3 + 0] += threeX * weight;
          positions[vertId * 3 + 1] += threeY * weight;
          positions[vertId * 3 + 2] += threeZ * weight;
        }
      }

      positionAttr.needsUpdate = true;
      geometry.computeVertexNormals();
    });
  }

  /**
   * Rotate a point by a quaternion
   */
  private rotateByQuat(x: number, y: number, z: number, q: { w: number; x: number; y: number; z: number }): { x: number; y: number; z: number } {
    // q * v * q^-1
    const ix = q.w * x + q.y * z - q.z * y;
    const iy = q.w * y + q.z * x - q.x * z;
    const iz = q.w * z + q.x * y - q.y * x;
    const iw = -q.x * x - q.y * y - q.z * z;

    return {
      x: ix * q.w + iw * -q.x + iy * -q.z - iz * -q.y,
      y: iy * q.w + iw * -q.y + iz * -q.x - ix * -q.z,
      z: iz * q.w + iw * -q.z + ix * -q.y - iy * -q.x
    };
  }
  private updateBodiesFromSimulation(): void {
    if (!this.model || !this.simulation) {
      return;
    }

    for (let b = 0; b < this.model.nbody; b++) {
      const bodyGroup = this.bodies.get(b);
      if (!bodyGroup) continue;

      // Get position from simulation xpos
      // MuJoCo: (x, y, z) → three.js: (x, z, -y)
      bodyGroup.position.set(
        this.simulation.xpos[b * 3 + 0],
        this.simulation.xpos[b * 3 + 2],
        -this.simulation.xpos[b * 3 + 1]
      );

      // Get rotation from simulation xquat
      // MuJoCo quaternion (w, x, y, z) → three.js quaternion (x, y, z, w)
      bodyGroup.quaternion.set(
        this.simulation.xquat[b * 4 + 1],
        this.simulation.xquat[b * 4 + 3],
        -this.simulation.xquat[b * 4 + 2],
        this.simulation.xquat[b * 4 + 0]
      );
    }

    // Update skin vertices if present
    if (this.skinGeometries.length > 0) {
      this.updateSkinVertices();
    }

    // Mark scene as dirty so it will be rendered
    this._dirty = true;
  }

  // ==================== Animation Loop ====================

  private update = (): void => {
    if (!this.isRunning) return;

    this.animationFrameId = requestAnimationFrame(this.update);

    // Update controls
    this.controls.update();

    // Update body positions from simulation or player motion
    if (this.playerMotionUpdate) {
      // Advance frame based on elapsed time
      const currentTime = performance.now();
      if (this.playerLastTime > 0) {
        const elapsed = (currentTime - this.playerLastTime) / 1000; // seconds
        const frameRate = this.playerMotionUpdate.frameRate || 30;
        const frameAdvance = Math.floor(elapsed * frameRate);
        if (frameAdvance > 0) {
          const nextFrame = this.playerCurrentFrame + frameAdvance;
          const maxLoadedFrame = this.playerMotionUpdate.xpos.length - 1;

          // In streaming mode, pause if we reach unloaded frames
          if (nextFrame > maxLoadedFrame) {
            // Pause at the last loaded frame
            this.playerCurrentFrame = maxLoadedFrame;
            this.stop(); // Pause playback until more frames arrive
            console.log('ThreeScene: paused at frame', maxLoadedFrame, 'waiting for more frames');
          } else {
            this.playerCurrentFrame = nextFrame % this.playerMotionUpdate.frameNum;
          }

          this.playerLastTime = currentTime;
          // Notify frame change
          if (this.playerFrameCallback) {
            this.playerFrameCallback(this.playerCurrentFrame);
          }
        }
      } else {
        this.playerLastTime = currentTime;
      }
      // Always update bodies and render when player motion is active
      this.updateBodiesFromPlayerMotion();
      this._dirty = true;
    } else if (this.model && this.simulation) {
      this.updateBodiesFromSimulation();
    }

    // Render (on-demand via _dirty flag)
    if (this._dirty) {
      this.renderer.render(this.scene, this.camera);
      this._dirty = false;
    }
  };

  /**
   * Start rendering loop
   */
  public start(): void {
    if (this.isRunning) return;
    this.isRunning = true;
    this.update();
  }

  /**
   * Stop rendering loop
   */
  public stop(): void {
    this.isRunning = false;
    if (this.animationFrameId !== null) {
      cancelAnimationFrame(this.animationFrameId);
      this.animationFrameId = null;
    }
  }

  /**
   * Clear scene
   */
  public clearScene(): void {
    this.stop();

    if (this.mujocoRoot) {
      this.scene.remove(this.mujocoRoot);
      this.mujocoRoot = null;
    }
    this.bodies.clear();
    this.worldBodyMeshes = [];
    this.skinMeshes = [];
    this.skinGeometries = [];
    this.hasRobotPrefix = false;
    this.hasHumanPrefix = false;
    this.humanVisible = true;
    this.model = null;
    this.simulation = null;
  }

  /**
   * Dispose resources
   */
  public dispose(): void {
    this.stop();
    this.stopRenderLoop();
    window.removeEventListener('resize', this.handleResize);
    this.controls.dispose();
    this.renderer.dispose();
  }

  /**
   * Update - called externally to update controls
   */
  public updateControls(): void {
    this.controls.update();
  }

  public setCamera(config: { lookat?: [number, number, number] }): void {
    if (config.lookat) {
      this.controls.target.set(config.lookat[0], config.lookat[2], -config.lookat[1]);
      this.controls.update();
      this.redraw();
    }
  }

  /**
   * Set pre-computed player motion data for animation playback
   * @param autostart if true, immediately starts the animation loop (default: true)
   */
  public setPlayerMotion(update: PlayerMotionUpdate, autostart = true): void {
    console.log('ThreeScene: setPlayerMotion called', {
      frameNum: update.frameNum,
      frameRate: update.frameRate,
      autostart
    });
    this.playerMotionUpdate = update;
    this.playerCurrentFrame = 0;
    this.playerLastTime = 0; // Reset to 0, will be initialized on first update
    if (autostart) {
      this.playerLastTime = performance.now(); // Initialize for autostart
      this.start();
    }
  }

  /**
   * Update streaming frames (for retarget-stream mode)
   * Incrementally adds new frames without rebuilding the entire array
   */
  public updateStreamingFrames(update: PlayerMotionUpdate): void {
    const newFrameCount = update.xpos.length;
    console.log('ThreeScene: updateStreamingFrames called', {
      currentFrames: this.playerMotionUpdate?.xpos.length || 0,
      newFrames: newFrameCount,
      totalFrames: update.frameNum
    });

    if (!this.playerMotionUpdate) {
      // First update, initialize player motion
      this.playerMotionUpdate = update;
      this.playerCurrentFrame = 0;
      this.playerLastTime = 0;
    } else {
      // Incremental update: only append new frames
      const currentFrameCount = this.playerMotionUpdate.xpos.length;
      if (newFrameCount > currentFrameCount) {
        // Append new frames
        for (let i = currentFrameCount; i < newFrameCount; i++) {
          this.playerMotionUpdate.xpos.push(update.xpos[i]);
          this.playerMotionUpdate.xquat.push(update.xquat[i]);
        }
        console.log(`ThreeScene: appended ${newFrameCount - currentFrameCount} new frames`);
      }
      // Update metadata
      this.playerMotionUpdate.frameNum = update.frameNum;
      this.playerMotionUpdate.frameRate = update.frameRate;
    }

    // Only redraw if we're not currently playing (playing will redraw automatically)
    if (!this.isRunning) {
      this.redraw();
    }
  }

  /**
   * Set current frame for player motion playback
   */
  public setPlayerFrame(frame: number): void {
    if (!this.playerMotionUpdate) return;
    this.playerCurrentFrame = Math.max(0, Math.min(frame, this.playerMotionUpdate.frameNum - 1));
    this.redraw();
  }

  /**
   * Get current player frame
   */
  public getPlayerFrame(): number {
    return this.playerCurrentFrame;
  }

  /**
   * Pause player motion animation
   */
  public pausePlayer(): void {
    console.log('ThreeScene: pausePlayer called');
    this.stop();
  }

  /**
   * Resume player motion animation
   */
  public resumePlayer(): void {
    console.log('ThreeScene: resumePlayer called', {
      hasPlayerMotion: !!this.playerMotionUpdate,
      currentFrame: this.playerCurrentFrame
    });
    if (this.playerMotionUpdate) {
      this.playerLastTime = performance.now(); // Initialize to now so elapsed is computed correctly
      this.start();
    }
  }

  /**
   * Check if player animation is currently running
   */
  public isPlayerRunning(): boolean {
    return this.isRunning && !!this.playerMotionUpdate;
  }

  /**
   * Update body positions from pre-computed player motion data
   */
  private updateBodiesFromPlayerMotion(): void {
    if (!this.playerMotionUpdate || !this.simulation) return;

    const frameIdx = this.playerCurrentFrame;
    const { xpos, xquat, nbody } = this.playerMotionUpdate;

    // Check if frame data is available (for streaming mode)
    if (frameIdx >= xpos.length || frameIdx >= xquat.length) {
      console.warn('ThreeScene: frame', frameIdx, 'not yet loaded');
      return;
    }

    for (let b = 0; b < nbody; b++) {
      const bodyGroup = this.bodies.get(b);
      if (!bodyGroup) continue;

      // Update simulation data arrays for skin vertex computation
      // Copy player motion data into simulation.xpos and simulation.xquat
      this.simulation.xpos[b * 3 + 0] = xpos[frameIdx][b][0];
      this.simulation.xpos[b * 3 + 1] = xpos[frameIdx][b][1];
      this.simulation.xpos[b * 3 + 2] = xpos[frameIdx][b][2];

      this.simulation.xquat[b * 4 + 0] = xquat[frameIdx][b][0];
      this.simulation.xquat[b * 4 + 1] = xquat[frameIdx][b][1];
      this.simulation.xquat[b * 4 + 2] = xquat[frameIdx][b][2];
      this.simulation.xquat[b * 4 + 3] = xquat[frameIdx][b][3];

      // MuJoCo: (x, y, z) → three.js: (x, z, -y)
      bodyGroup.position.set(
        xpos[frameIdx][b][0],
        xpos[frameIdx][b][2],
        -xpos[frameIdx][b][1]
      );

      // MuJoCo quaternion (w, x, y, z) → three.js quaternion (x, y, z, w)
      bodyGroup.quaternion.set(
        xquat[frameIdx][b][1],
        xquat[frameIdx][b][3],
        -xquat[frameIdx][b][2],
        xquat[frameIdx][b][0]
      );
    }

    // Update skin vertices if present (same as updateBodiesFromSimulation)
    if (this.skinGeometries.length > 0) {
      this.updateSkinVertices();
    }
  }

  /**
   * Set callback for frame changes (called on every frame update during playback)
   */
  public setPlayerFrameCallback(callback: PlayerFrameCallback | null): void {
    this.playerFrameCallback = callback;
  }

  /**
   * Set visibility for robot bodies (bodies with 'robot_' prefix or all non-world bodies in robot-only mode)
   */
  public setRobotVisible(visible: boolean): void {
    console.log(`ThreeScene[${this.instanceId}]: setRobotVisible(${visible})`, {
      hasRobotPrefix: this.hasRobotPrefix,
      hasHumanPrefix: this.hasHumanPrefix,
      bodiesCount: this.bodies.size,
      hasMujocoRoot: !!this.mujocoRoot,
      mujocoRootInScene: this.mujocoRoot ? this.scene.children.includes(this.mujocoRoot) : false,
      mujocoRootVisible: this.mujocoRoot?.visible
    });

    // In combined mode (has robot_ prefix), only toggle robot_ bodies
    if (this.hasRobotPrefix) {
      let count = 0;
      for (const bodyGroup of this.bodies.values()) {
        if (bodyGroup.name.startsWith('robot_')) {
          bodyGroup.visible = visible;
          // Also set visibility for all child meshes
          let meshCount = 0;
          bodyGroup.traverse((child) => {
            if (child instanceof THREE.Mesh) {
              child.visible = visible;
              meshCount++;
            }
          });
          console.log(`  → Body ${bodyGroup.name}: set ${meshCount} meshes to visible=${visible}`);
          count++;
        }
      }
      console.log(`  → Toggled ${count} robot_ bodies`);
    } else if (!this.hasHumanPrefix) {
      // Robot-only mode: no prefixes, toggle all non-world bodies
      let count = 0;
      let totalMeshes = 0;
      for (const [bodyId, bodyGroup] of this.bodies) {
        if (bodyId > 0) { // Skip world body
          bodyGroup.visible = visible;
          // Also set visibility for all child meshes
          let meshCount = 0;
          bodyGroup.traverse((child) => {
            if (child instanceof THREE.Mesh) {
              child.visible = visible;
              meshCount++;
            }
          });
          totalMeshes += meshCount;
          console.log(`  → Body ${bodyId} (${bodyGroup.name}): children=${bodyGroup.children.length}, meshes=${meshCount}, visible=${visible}`);
          count++;
        }
      }
      console.log(`  → Toggled ${count} non-world bodies, ${totalMeshes} total meshes`);
    } else {
      console.log(`  → Human-only mode, no robot to toggle`);
    }

    this._dirty = true;
    console.log(`  → Set _dirty=true, forcing immediate render`);
    // Force immediate render to ensure visibility change is applied
    this.render();
  }

  /**
   * Set visibility for human bodies (bodies with 'human_' prefix or all non-world bodies in human-only mode)
   */
  public setHumanVisible(visible: boolean): void {
    this.humanVisible = visible;

    // In combined mode, hide bodies with 'human_' prefix
    if (this.hasHumanPrefix) {
      for (const bodyGroup of this.bodies.values()) {
        if (bodyGroup.name.startsWith('human_')) {
          bodyGroup.visible = visible;
          // Also set visibility for all child meshes
          bodyGroup.traverse((child) => {
            if (child instanceof THREE.Mesh) {
              child.visible = visible;
            }
          });
        }
      }
    } else if (!this.hasRobotPrefix) {
      // Human-only mode: hide all non-world bodies
      for (const [bodyId, bodyGroup] of this.bodies) {
        if (bodyId > 0) { // Skip world body
          bodyGroup.visible = visible;
          // Also set visibility for all child meshes
          bodyGroup.traverse((child) => {
            if (child instanceof THREE.Mesh) {
              child.visible = visible;
            }
          });
        }
      }
    }
    // else: Robot-only mode (hasRobotPrefix && !hasHumanPrefix) - do nothing, no human bodies to toggle

    // Also toggle skin meshes visibility
    if (this.skinGeometries.length > 0) {
      this.mujocoRoot?.children.forEach(child => {
        if (child instanceof THREE.Mesh && child.userData.skinId !== undefined) {
          child.visible = visible && this.showSkin;
        }
      });

      // Toggle parametric geoms (inverse of skin when skin is available)
      for (const mesh of this.skinMeshes) {
        if (visible) {
          mesh.visible = !this.showSkin;
        } else {
          mesh.visible = false;
        }
      }
    }

    this._dirty = true;
    // Force immediate render to ensure visibility change is applied
    this.render();
  }
}