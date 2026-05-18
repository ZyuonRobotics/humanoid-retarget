# MuJoCo WASM Integration Guide

## 概述

MuJoCo WASM 是 MuJoCo 物理引擎的 WebAssembly 版本，可以在浏览器中直接运行物理模拟。

## 集成步骤

### 1. 安装 mujoco-wasm

```bash
npm install mujoco-wasm
```

### 2. 下载 MuJoCo 资源文件

需要下载以下文件放到 `public/mujoco/` 目录:
- `mujoco_wasm.wasm` - WebAssembly 二进制
- `mujoco_wasm.js` - JavaScript 胶水代码

可以从 https://github.com/google-deepmind/mujoco/releases 下载。

### 3. Viewer3D 组件示例

```typescript
// src/components/Viewer3D/mujoco.ts
import * as mujoco from 'mujoco-wasm';

let model: mujoco.MjModel | null = null;
let data: mujoco.MjData | null = null;

export async function initMuJoCo(xmlString: string) {
  model = mujoco.MjModel.from_xml_string(xmlString);
  data = new mujoco.MjData(model);

  // Initialize
  mujoco.mj_step(model, data);
}

export function setQPos(qpos: number[]) {
  if (!data || !model) return;
  data.qpos.set(qpos);
  mujoco.mj_step(model, data);
}

export function render(canvas: HTMLCanvasElement) {
  if (!model || !data) return;

  const ctx = canvas.getContext('2d');
  if (!ctx) return;

  // Use mujoco's built-in renderer
  const renderer = new mujoco.MjrContext(model, 50);
  mujoco.mjr_render(
    { width: canvas.width, height: canvas.height, viewport: { width: canvas.width, height: canvas.height } },
    renderer
  );
}
```

## 注意事项

1. **CORS**: 加载 .wasm 文件可能需要正确的 CORS 配置
2. **性能**: WASM 版本可能比原生版本慢
3. **调试**: 使用浏览器的开发者工具调试 WASM

## 替代方案

如果 MuJoCo WASM 集成困难，可以考虑:
1. 使用 Three.js + 自定义渲染
2. 使用服务器端渲染 + WebRTC 流式传输
3. 使用已经支持 WebGL 的物理引擎 (如 Cannon.js, Ammo.js)
