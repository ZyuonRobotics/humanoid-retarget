/**
 * MuJoCo to three.js coordinate and rotation conversion utilities
 *
 * Coordinate mapping: MuJoCo (x, y, z) → three.js (x, z, -y)
 * - MuJoCo: Z-up, X-forward, Y-left
 * - three.js: Y-up, X-forward, Z-forward
 */

import * as THREE from 'three';

/**
 * Convert MuJoCo position to three.js position
 * MuJoCo: (x, y, z) → three.js: (x, z, -y)
 */
export function mujocoPositionToThree(pos: [number, number, number]): THREE.Vector3 {
  return new THREE.Vector3(pos[0], pos[2], -pos[1]);
}

/**
 * Convert three.js position to MuJoCo position
 * three.js: (x, y, z) → MuJoCo: (x, -z, y)
 */
export function threePositionToMujoco(pos: [number, number, number]): [number, number, number] {
  return [pos[0], -pos[2], pos[1]];
}

/**
 * Convert MuJoCo quaternion (w, x, y, z) to three.js quaternion (x, y, z, w)
 * with coordinate mapping (x, y, z) -> (x, z, -y)
 */
export function mujocoQuaternionToThree(w: number, x: number, y: number, z: number): THREE.Quaternion {
  return new THREE.Quaternion(x, z, -y, w);
}

/**
 * Convert MuJoCo quaternion array [w, x, y, z] to three.js quaternion
 */
export function mujocoQuaternionArrayToThree(quat: [number, number, number, number]): THREE.Quaternion {
  return mujocoQuaternionToThree(quat[0], quat[1], quat[2], quat[3]);
}

/**
 * Convert three.js quaternion to MuJoCo quaternion (w, x, y, z)
 */
export function threeQuaternionToMujoco(q: THREE.Quaternion): [number, number, number, number] {
  return [q.w, q.x, -q.z, q.y];
}

/**
 * Apply coordinate transformation to a Vector3 (in-place)
 * MuJoCo → three.js: (x, y, z) -> (x, z, -y)
 */
export function transformVector3M2T(v: THREE.Vector3): void {
  const x = v.x;
  const y = v.y;
  const z = v.z;
  v.set(x, z, -y);
}

/**
 * Apply coordinate transformation to a Vector3 (in-place)
 * three.js → MuJoCo: (x, y, z) -> (x, -z, y)
 */
export function transformVector3T2M(v: THREE.Vector3): void {
  const x = v.x;
  const y = v.y;
  const z = v.z;
  v.set(x, -z, y);
}

/**
 * Transform mesh vertex positions from MuJoCo to three.js coordinate system
 * MuJoCo: (x, y, z) → three.js: (x, z, -y)
 * @param vertices - Float32Array with interleaved x,y,z values
 * @param count - number of vertices
 * @returns new Float32Array with transformed coordinates
 */
export function transformMeshVerticesM2T(vertices: Float32Array, count: number): Float32Array {
  const result = new Float32Array(vertices.length);

  for (let i = 0; i < count; i++) {
    const x = vertices[i * 3 + 0];
    const y = vertices[i * 3 + 1];
    const z = vertices[i * 3 + 2];
    result[i * 3 + 0] = x;
    result[i * 3 + 1] = z;
    result[i * 3 + 2] = -y;
  }

  return result;
}

/**
 * Transform mesh normals from MuJoCo to three.js coordinate system
 * MuJoCo: (x, y, z) → three.js: (x, z, -y)
 * @param normals - Float32Array with interleaved x,y,z values
 * @param count - number of normals
 * @returns new Float32Array with transformed normals
 */
export function transformMeshNormalsM2T(normals: Float32Array, count: number): Float32Array {
  const result = new Float32Array(normals.length);

  for (let i = 0; i < count; i++) {
    const x = normals[i * 3 + 0];
    const y = normals[i * 3 + 1];
    const z = normals[i * 3 + 2];
    result[i * 3 + 0] = x;
    result[i * 3 + 1] = z;
    result[i * 3 + 2] = -y;
  }

  return result;
}

/**
 * Create a rotation matrix for MuJoCo → three.js transformation
 * (x, y, z) -> (x, z, -y)
 */
export function createM2TRotationMatrix(): THREE.Matrix4 {
  return new THREE.Matrix4().set(
    1, 0, 0, 0,
    0, 0, 1, 0,
    0, -1, 0, 0,
    0, 0, 0, 1
  );
}

/**
 * Create a rotation matrix for three.js → MuJoCo transformation
 * (x, y, z) -> (x, -z, y)
 */
export function createT2MRotationMatrix(): THREE.Matrix4 {
  return new THREE.Matrix4().set(
    1, 0, 0, 0,
    0, 0, -1, 0,
    0, 1, 0, 0,
    0, 0, 0, 1
  );
}