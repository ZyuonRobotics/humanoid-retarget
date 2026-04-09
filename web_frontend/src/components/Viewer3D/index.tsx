import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useConfigContext } from '../../contexts/ConfigContext';
import {
  initMuJoCo,
  render,
  fetchAlignPreview,
  AlignPreviewData,
  setCamera,
  getBodyPosition,
  highlightBody,
} from './mujoco';

interface Viewer3DProps {
  sourceFile?: string;
}

const Viewer3D: React.FC<Viewer3DProps> = ({ sourceFile }) => {
  const { selectedRobot, config, generatorType } = useConfigContext();
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const animationFrameRef = useRef<number>();

  const [alignData, setAlignData] = useState<AlignPreviewData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedBody, setSelectedBody] = useState<{ id: number; name: string } | null>(null);
  const [bodyInfo, setBodyInfo] = useState<{ name: string; position: [number, number, number] } | null>(null);

  // Camera state
  const [camera, setCameraState] = useState({
    azimuth: 0,
    elevation: -30,
    distance: 3,
    isDragging: false,
    lastX: 0,
    lastY: 0
  });

  // Debounced fetch for align preview
  const fetchPreview = useCallback(async () => {
    if (!sourceFile || !selectedRobot || !generatorType) {
      setAlignData(null);
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const data = await fetchAlignPreview(sourceFile, selectedRobot, generatorType, config);
      setAlignData(data);

      if (data) {
        // Initialize MuJoCo with the fetched data
        await initMuJoCo(data.xml, data.qpos);
        // Update camera lookat based on global body ratio
        const lookatY = data.globalBodyRatio * 0.5;
        setCamera({ lookat: [0, 0, lookatY] });
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load preview');
      setAlignData(null);
    } finally {
      setLoading(false);
    }
  }, [sourceFile, selectedRobot, generatorType, config]);

  // Fetch preview when config or source changes
  useEffect(() => {
    const debounceTimer = setTimeout(() => {
      fetchPreview();
    }, 300); // Debounce 300ms

    return () => clearTimeout(debounceTimer);
  }, [fetchPreview]);

  // Render loop
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const renderLoop = () => {
      render(canvas);
      animationFrameRef.current = requestAnimationFrame(renderLoop);
    };

    renderLoop();

    return () => {
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
    };
  }, [alignData]);

  // Handle mouse interactions for camera orbit
  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    setCameraState(prev => ({ ...prev, isDragging: true, lastX: e.clientX, lastY: e.clientY }));
  }, []);

  const handleMouseMove = useCallback((e: React.MouseEvent) => {
    if (!camera.isDragging) return;

    const deltaX = e.clientX - camera.lastX;
    const deltaY = e.clientY - camera.lastY;

    setCameraState(prev => ({
      ...prev,
      azimuth: prev.azimuth + deltaX * 0.5,
      elevation: Math.max(-90, Math.min(90, prev.elevation - deltaY * 0.5)),
      lastX: e.clientX,
      lastY: e.clientY
    }));

    setCamera({ azimuth: camera.azimuth + deltaX * 0.5, elevation: camera.elevation });
  }, [camera]);

  const handleMouseUp = useCallback(() => {
    setCameraState(prev => ({ ...prev, isDragging: false }));
  }, []);

  // Handle zoom
  const handleWheel = useCallback((e: React.WheelEvent) => {
    e.preventDefault();
    const delta = e.deltaY > 0 ? 0.1 : -0.1;
    const newDistance = Math.max(0.5, Math.min(10, camera.distance + delta));
    setCameraState(prev => ({ ...prev, distance: newDistance }));
    setCamera({ distance: newDistance });
  }, [camera.distance]);

  // Handle body picking on click
  const handleClick = useCallback((_e: React.MouseEvent) => {
    const canvas = canvasRef.current;
    if (!canvas || !alignData) return;

    // For now, just highlight clicked position
    // Actual body picking would require mujoco-wasm integration
    const bodyId = Math.floor(Math.random() * alignData.bodyNames.length); // Placeholder
    const bodyName = alignData.bodyNames[bodyId];

    setSelectedBody({ id: bodyId, name: bodyName });
    highlightBody(bodyId, [1, 0.5, 0]); // Orange highlight

    const position = getBodyPosition(bodyId);
    if (position) {
      setBodyInfo({ name: bodyName, position });
    }
  }, [alignData]);

  return (
    <div
      ref={containerRef}
      style={{
        width: '100%',
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        background: 'linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%)',
        position: 'relative',
        overflow: 'hidden',
      }}
    >
      {/* 3D Canvas */}
      <div
        style={{
          flex: 1,
          position: 'relative',
          cursor: camera.isDragging ? 'grabbing' : 'grab'
        }}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
        onWheel={handleWheel}
      >
        {/* Animated gradient background */}
        <div
          style={{
            position: 'absolute',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background: 'radial-gradient(ellipse at center, rgba(58, 123, 213, 0.15) 0%, transparent 70%)',
            animation: 'pulse 4s ease-in-out infinite',
            pointerEvents: 'none'
          }}
        />

        {/* Grid pattern */}
        <div
          style={{
            position: 'absolute',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundImage: `
              linear-gradient(rgba(255,255,255,0.03) 1px, transparent 1px),
              linear-gradient(90deg, rgba(255,255,255,0.03) 1px, transparent 1px)
            `,
            backgroundSize: '50px 50px',
            pointerEvents: 'none'
          }}
        />

        {loading ? (
          <div
            style={{
              position: 'absolute',
              top: '50%',
              left: '50%',
              transform: 'translate(-50%, -50%)',
              color: 'rgba(255,255,255,0.7)',
              fontSize: 14,
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              gap: 8
            }}
          >
            <div style={{ fontSize: 24 }}>⟳</div>
            <div>Loading 3D Preview...</div>
          </div>
        ) : error ? (
          <div
            style={{
              position: 'absolute',
              top: '50%',
              left: '50%',
              transform: 'translate(-50%, -50%)',
              color: 'rgba(255,100,100,0.8)',
              fontSize: 14,
              textAlign: 'center',
              maxWidth: 300
            }}
          >
            {error}
          </div>
        ) : !alignData ? (
          <div
            style={{
              position: 'absolute',
              top: '50%',
              left: '50%',
              transform: 'translate(-50%, -50%)',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              gap: 16,
              color: 'rgba(255,255,255,0.5)',
            }}
          >
            <div
              style={{
                width: 120,
                height: 180,
                border: '2px solid rgba(255,255,255,0.2)',
                borderRadius: 8,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: 48,
              }}
            >
              🤖
            </div>
            <div style={{ fontSize: 14 }}>
              3D Preview: {selectedRobot || 'Select a robot'}
            </div>
          </div>
        ) : (
          <canvas
            ref={canvasRef}
            width={800}
            height={600}
            onClick={handleClick}
            style={{
              background: 'transparent',
              borderRadius: 8,
            }}
          />
        )}
      </div>

      {/* Camera controls info */}
      <div
        style={{
          position: 'absolute',
          bottom: 8,
          left: 8,
          color: 'rgba(255,255,255,0.4)',
          fontSize: 11,
          fontFamily: 'monospace',
          pointerEvents: 'none'
        }}
      >
        Drag: Orbit | Scroll: Zoom | Click: Select Body
      </div>

      {/* Body info panel */}
      {selectedBody && bodyInfo && (
        <div
          style={{
            position: 'absolute',
            top: 8,
            right: 8,
            background: 'rgba(0,0,0,0.7)',
            border: '1px solid rgba(255,255,255,0.2)',
            borderRadius: 8,
            padding: '12px 16px',
            color: 'white',
            fontSize: 12,
            fontFamily: 'monospace',
            minWidth: 180
          }}
        >
          <div style={{ fontWeight: 'bold', marginBottom: 8, color: '#3a7bd5' }}>
            {bodyInfo.name}
          </div>
          <div style={{ color: 'rgba(255,255,255,0.7)' }}>
            Position: {bodyInfo.position.map(v => v.toFixed(3)).join(', ')}
          </div>
          <div style={{ marginTop: 8 }}>
            <button
              onClick={() => { setSelectedBody(null); setBodyInfo(null); }}
              style={{
                background: 'rgba(255,255,255,0.1)',
                border: 'none',
                borderRadius: 4,
                padding: '4px 8px',
                color: 'white',
                cursor: 'pointer',
                fontSize: 11
              }}
            >
              Close
            </button>
          </div>
        </div>
      )}

      {/* Status bar */}
      {alignData && (
        <div
          style={{
            position: 'absolute',
            bottom: 8,
            right: 8,
            color: 'rgba(255,255,255,0.4)',
            fontSize: 11,
            fontFamily: 'monospace',
            pointerEvents: 'none'
          }}
        >
          Bodies: {alignData.bodyNames.length} | Ratio: {alignData.globalBodyRatio.toFixed(3)}
        </div>
      )}
    </div>
  );
};

export default Viewer3D;