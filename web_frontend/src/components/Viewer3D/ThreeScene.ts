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

export class ThreeScene {
  private canvas: HTMLCanvasElement;
  private scene: THREE.Scene;
  private camera: THREE.PerspectiveCamera;
  private renderer: THREE.WebGLRenderer;
  private controls: OrbitControls;

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

  constructor(canvas: HTMLCanvasElement) {
    console.log(`ThreeScene[${this.instanceId}]: constructor called`);
    this.canvas = canvas;

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
      antialias: true
    });
    this.renderer.setSize(width, height);
    this.renderer.setPixelRatio(window.devicePixelRatio);
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
    this.directionalLight.shadow.mapSize.width = 2048;
    this.directionalLight.shadow.mapSize.height = 2048;
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
    this.renderer.setPixelRatio(window.devicePixelRatio);

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

      // Create geometry
      let geometry: THREE.BufferGeometry;

      if (geomType === mujoco.mjtGeom.mjGEOM_SPHERE.value) {
        geometry = new THREE.SphereGeometry(size[0], 32, 32);
      } else if (geomType === mujoco.mjtGeom.mjGEOM_CAPSULE.value) {
        geometry = new THREE.CapsuleGeometry(size[0], size[1] * 2.0, 20, 20);
      } else if (geomType === mujoco.mjtGeom.mjGEOM_CYLINDER.value) {
        geometry = new THREE.CylinderGeometry(size[0], size[0], size[1] * 2.0, 32);
      } else if (geomType === mujoco.mjtGeom.mjGEOM_BOX.value) {
        geometry = new THREE.BoxGeometry(size[0] * 2.0, size[2] * 2.0, size[1] * 2.0);
      } else if (geomType === mujoco.mjtGeom.mjGEOM_ELLIPSOID.value) {
        geometry = new THREE.SphereGeometry(1, 32, 32);
      } else if (geomType === mujoco.mjtGeom.mjGEOM_MESH.value) {
        geometry = this.createMeshGeometry(model, model.geom_dataid[g]);
      } else {
        geometry = new THREE.SphereGeometry(size[0] || 0.1, 16, 16);
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

      // Track world body meshes for centerModel calculation but don't render them
      if (bodyId === 0) {
        mesh.visible = false;
        this.worldBodyMeshes.push(mesh);
      }
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
    const minY = bboxGlobal.min.y;

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
          this.playerCurrentFrame = (this.playerCurrentFrame + frameAdvance) % this.playerMotionUpdate.frameNum;
          this.playerLastTime = currentTime;
        }
        this.updateBodiesFromPlayerMotion();
        this._dirty = true;
        // Notify frame change
        if (this.playerFrameCallback) {
          this.playerFrameCallback(this.playerCurrentFrame);
        }
      } else {
        this.playerLastTime = currentTime;
      }
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
    this.playerMotionUpdate = update;
    this.playerCurrentFrame = 0;
    if (autostart) {
      this.start();
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
    this.stop();
  }

  /**
   * Resume player motion animation
   */
  public resumePlayer(): void {
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

    for (let b = 0; b < nbody; b++) {
      const bodyGroup = this.bodies.get(b);
      if (!bodyGroup) continue;

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
  }

  /**
   * Set callback for frame changes (called on every frame update during playback)
   */
  public setPlayerFrameCallback(callback: PlayerFrameCallback | null): void {
    this.playerFrameCallback = callback;
  }
}