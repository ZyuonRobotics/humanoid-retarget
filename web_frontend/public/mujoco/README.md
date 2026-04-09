# MuJoCo WASM Binaries

This directory should contain MuJoCo WebAssembly binaries for 3D rendering.

## Setup Instructions

1. Download MuJoCo WASM binaries from https://github.com/google-deepmind/mujoco/releases

2. Place the following files in this directory:
   - `mujoco_wasm.wasm` - WebAssembly binary
   - `mujoco_wasm.js` - JavaScript glue code (if separate)

3. Alternatively, run `npm install` which should download the binaries automatically via the mujoco-wasm package.

## Notes

- The mujoco-wasm package version should match the binaries
- If binaries are not available, the viewer will use a fallback 2D renderer