import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [
    react(),
    {
      name: 'mujoco-worker-transform',
      transform(code, id) {
        if (id.indexOf('node_modules/mujoco/mujoco.js') === -1 &&
            id.indexOf('node_modules/mujoco-js/dist/mujoco_wasm.js') === -1) return null;
        return code.replace(
          /new Worker\(new URL\("mujoco.*?\.js", import\.meta\.url\),\s*/g,
          'new Worker(new URL("mujoco_wasm.js", import.meta.url), /* @vite-ignore */ '
        );
      }
    }
  ],
  build: {
    target: 'es2022',
    rollupOptions: {
      output: {
        manualChunks: undefined
      },
      external: ['mujoco', 'mujoco-js']
    }
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      }
    }
  },
  optimizeDeps: {
    exclude: ['mujoco', 'mujoco-js']
  }
})
