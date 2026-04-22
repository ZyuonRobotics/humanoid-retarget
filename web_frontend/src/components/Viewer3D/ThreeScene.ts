/**
 * ThreeScene - Three.js rendering for MuJoCo models
 * Adapted from robot_viewer's MujocoSimulationManager
 */

import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import { MuJoCoModule, MuJoCoModel, MuJoCoSimulation, CameraConfig } from './mujoco';
import {
  transformMeshVerticesM2T,
  transformMeshNormalsM2T
} from './coord';

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
  // Instance ID for debugging
  private instanceId: number = ThreeScene.nextInstanceId++;
  private static nextInstanceId = 0;

  // Camera config
  private cameraConfig: CameraConfig = {
    azimuth: 0,
    elevation: -30,
    distance: 3,
    lookat: [0, 0, 0.5]
  };

  // Animation
  private animationFrameId: number | null = null;
  private isRunning = false;

  constructor(canvas: HTMLCanvasElement) {
    console.log(`ThreeScene[${this.instanceId}]: constructor called`);
    this.canvas = canvas;

    // Create scene
    this.scene = new THREE.Scene();
    this.scene.background = new THREE.Color(0x1a1a2e);

    // Create camera
    const width = canvas.clientWidth;
    const height = canvas.clientHeight;
    this.camera = new THREE.PerspectiveCamera(60, width / height, 0.1, 1000);
    this.updateCameraFromConfig();

    // Create renderer
    this.renderer = new THREE.WebGLRenderer({
      canvas: canvas,
      antialias: true
    });
    this.renderer.setSize(width, height);
    this.renderer.setPixelRatio(window.devicePixelRatio);
    this.renderer.shadowMap.enabled = true;
    this.renderer.shadowMap.type = THREE.PCFSoftShadowMap;

    // Create controls
    this.controls = new OrbitControls(this.camera, canvas);
    this.controls.enableDamping = true;
    this.controls.dampingFactor = 0.05;
    this.controls.enablePan = true;
    this.controls.enableZoom = true;
    this.controls.enableRotate = true;

    // Setup lights
    this.setupLights();

    // Setup ground plane
    this.setupGround();

    // Handle resize
    this.handleResize = this.handleResize.bind(this);
    window.addEventListener('resize', this.handleResize);
  }

  private setupLights(): void {
    // Ambient light
    const ambient = new THREE.AmbientLight(0xffffff, 0.6);
    this.scene.add(ambient);

    // Directional light (sun)
    const directional = new THREE.DirectionalLight(0xffffff, 0.8);
    directional.position.set(5, 10, 5);
    directional.castShadow = true;
    directional.shadow.mapSize.width = 2048;
    directional.shadow.mapSize.height = 2048;
    directional.shadow.camera.near = 0.5;
    directional.shadow.camera.far = 50;
    directional.shadow.camera.left = -10;
    directional.shadow.camera.right = 10;
    directional.shadow.camera.top = 10;
    directional.shadow.camera.bottom = -10;
    this.scene.add(directional);

    // Fill light
    const fill = new THREE.DirectionalLight(0xffffff, 0.3);
    fill.position.set(-5, 3, -5);
    this.scene.add(fill);
  }

  private setupGround(): void {
    // Ground plane
    const groundGeometry = new THREE.PlaneGeometry(20, 20);
    const groundMaterial = new THREE.MeshPhongMaterial({
      color: 0x2a2a4a,
      depthWrite: true
    });
    const ground = new THREE.Mesh(groundGeometry, groundMaterial);
    ground.rotation.x = -Math.PI / 2;
    ground.position.y = 0;
    ground.receiveShadow = true;
    this.scene.add(ground);

    // Grid helper
    const gridHelper = new THREE.GridHelper(20, 20, 0x444466, 0x333355);
    gridHelper.position.y = 0.001;
    this.scene.add(gridHelper);
  }

  private handleResize(): void {
    const width = this.canvas.clientWidth;
    const height = this.canvas.clientHeight;

    this.camera.aspect = width / height;
    this.camera.updateProjectionMatrix();
    this.renderer.setSize(width, height);
  }

  public setCamera(config: Partial<CameraConfig>): void {
    this.cameraConfig = { ...this.cameraConfig, ...config };
    this.updateCameraFromConfig();
  }

  private updateCameraFromConfig(): void {
    const { azimuth, elevation, distance, lookat } = this.cameraConfig;
    const azimuthRad = (azimuth * Math.PI) / 180;
    const elevationRad = (elevation * Math.PI) / 180;

    this.camera.position.x = lookat[0] + distance * Math.cos(elevationRad) * Math.sin(azimuthRad);
    this.camera.position.y = lookat[1] + distance * Math.sin(elevationRad);
    this.camera.position.z = lookat[2] + distance * Math.cos(elevationRad) * Math.cos(azimuthRad);
    this.camera.lookAt(new THREE.Vector3(lookat[0], lookat[1], lookat[2]));
  }

  /**
   * Create scene from MuJoCo model
   */
  public createScene(mujoco: MuJoCoModule, model: MuJoCoModel, simulation: MuJoCoSimulation): void {
    console.log(`ThreeScene[${this.instanceId}]: createScene called, model nbody=${model.nbody}`);

    // Clear old scene first (before setting new model/simulation)
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

    // Find minimum y position (ground level)
    let minY = Infinity;
    for (let b = 0; b < this.model.nbody; b++) {
      const bodyGroup = this.bodies.get(b);
      if (bodyGroup) {
        bodyGroup.updateMatrixWorld(true);
        const worldPos = new THREE.Vector3();
        bodyGroup.getWorldPosition(worldPos);
        if (worldPos.y < minY) {
          minY = worldPos.y;
        }
      }
    }

    console.log(`ThreeScene[${this.instanceId}]: centerModel, minY=${minY}, mujocoRoot.position.y before=${this.mujocoRoot.position.y}`);
    if (isFinite(minY) && minY !== 0) {
      this.mujocoRoot.position.y = -minY;
    }
    console.log(`ThreeScene[${this.instanceId}]: centerModel, mujocoRoot.position.y after=${this.mujocoRoot.position.y}`);

    // Auto-fit camera to model
    this.fitCameraToModel();
  }

  /**
   * Fit camera to show entire model
   */
  private fitCameraToModel(): void {
    if (!this.mujocoRoot) return;

    // Calculate bounding box
    const box = new THREE.Box3().setFromObject(this.mujocoRoot);
    const size = box.getSize(new THREE.Vector3());
    const center = box.getCenter(new THREE.Vector3());

    // Set camera distance based on model size
    const maxDim = Math.max(size.x, size.y, size.z);
    const distance = maxDim * 2.5;

    this.camera.position.set(center.x + distance * 0.5, center.y + distance * 0.3, center.z + distance);
    this.camera.lookAt(center);

    // Update camera config
    this.cameraConfig.distance = distance;
    this.cameraConfig.lookat = [center.x, center.y, center.z];
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
  }

  /**
   * Update simulation and render
   */
  private update = (): void => {
    if (!this.isRunning) return;

    this.animationFrameId = requestAnimationFrame(this.update);

    // Update controls
    this.controls.update();

    // Update body positions from simulation
    if (this.model && this.simulation) {
      this.updateBodiesFromSimulation();
    }

    // Render
    this.renderer.render(this.scene, this.camera);
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
    this.model = null;
    this.simulation = null;
  }

  /**
   * Dispose resources
   */
  public dispose(): void {
    this.stop();
    window.removeEventListener('resize', this.handleResize);
    this.controls.dispose();
    this.renderer.dispose();
  }
}
