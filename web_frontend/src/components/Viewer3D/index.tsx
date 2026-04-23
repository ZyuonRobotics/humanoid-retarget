import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useConfigContext } from '../../contexts/ConfigContext';
import { modelApi } from '../../api/client';
import {
  initMuJoCo,
  fetchAlignPreview,
  fetchHumanPreview,
  loadRobotModel,
  dispose,
  AlignPreviewData,
  setCamera,
  highlightBody,
  initThreeScene,
  startRendering,
  mujocoModule,
  currentModel,
  currentData,
} from './mujoco';

interface Viewer3DProps {
  sourceFile?: string;
}

const Viewer3D: React.FC<Viewer3DProps> = ({ sourceFile }) => {
  const { selectedRobot, config, generatorType } = useConfigContext();
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const threeSceneRef = useRef<any>(null);

  const [alignData, setAlignData] = useState<AlignPreviewData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Independent visibility toggles. When both are false nothing is shown;
  // when both are true the combined human+robot preview is shown.
  const [showRobot, setShowRobot] = useState(false);
  const [showHuman, setShowHuman] = useState(false);

  // Determine which toggles are currently enabled
  const canShowRobot = !!selectedRobot;
  const canShowHuman = !!sourceFile && !!generatorType;

  const toggleRobot = () => {
    if (!canShowRobot) return;
    setShowRobot(v => !v);
  };
  const toggleHuman = () => {
    if (!canShowHuman) return;
    setShowHuman(v => !v);
  };

  // Camera state
  const [camera, setCameraState] = useState({
    azimuth: 0,
    elevation: -30,
    distance: 3,
    isDragging: false,
    lastX: 0,
    lastY: 0
  });

  // Initialize Three.js scene when canvas becomes available
  // Debounced fetch for model (robot only, human only, or robot+human)
  const fetchPreview = useCallback(async () => {
    // Nothing to show
    if (!showRobot && !showHuman) {
      dispose();
      if (threeSceneRef.current) {
        threeSceneRef.current.dispose();
        threeSceneRef.current = null;
      }
      setAlignData(null);
      return;
    }

    // Clean up previous model/scene before loading new one
    dispose();
    if (threeSceneRef.current) {
      threeSceneRef.current.dispose();
      threeSceneRef.current = null;
    }

    // Guard: each enabled toggle needs its own prerequisites
    if (showRobot && !selectedRobot) {
      setAlignData(null);
      return;
    }
    if (showHuman && (!sourceFile || !generatorType)) {
      setAlignData(null);
      return;
    }

    setLoading(true);
    setError(null);

    // Shared helper: build Three scene once the model is loaded
    const bootScene = () => {
      const createSceneIfReady = () => {
        const canvas = canvasRef.current;
        if (!canvas) return false;
        if (!threeSceneRef.current) {
          threeSceneRef.current = initThreeScene(canvas);
        }
        if (threeSceneRef.current && mujocoModule && currentModel && currentData) {
          threeSceneRef.current.createScene(mujocoModule, currentModel, currentData as any);
          startRendering();
          return true;
        }
        return false;
      };
      if (!createSceneIfReady()) {
        setTimeout(() => { createSceneIfReady(); }, 100);
      }
    };

    try {
      if (showRobot && showHuman) {
        // Combined human+robot preview. Robot meshes are referenced by the
        // combined XML, so fetch them alongside the align preview.
        const [data, robotData] = await Promise.all([
          fetchAlignPreview(sourceFile!, selectedRobot!, generatorType!, config),
          modelApi.getRobotMJCFWithMeshes(selectedRobot!),
        ]);
        if (data) {
          await initMuJoCo(data.xml, data.qpos, robotData.meshes || {});
          const lookatY = data.globalBodyRatio * 0.5;
          setCamera({ lookat: [0, 0, lookatY] });
          setAlignData(data);
          bootScene();
        } else {
          setAlignData(null);
        }
      } else if (showRobot) {
        // Robot only
        const robotData = await modelApi.getRobotMJCFWithMeshes(selectedRobot!);
        await loadRobotModel(selectedRobot!, robotData.xml, robotData.meshes || {});
        setAlignData({
          xml: robotData.xml,
          qpos: [],
          bodyNames: robotData.body_names || [],
          globalBodyRatio: 1.0,
        });
        setCamera({ lookat: [0, 0, 0.5] });
        bootScene();
      } else if (showHuman) {
        // Human only — parametric bodies, no mesh files required
        const data = await fetchHumanPreview(sourceFile!, generatorType!, config);
        if (data) {
          await initMuJoCo(data.xml, data.qpos);
          const lookatY = data.globalBodyRatio * 0.5;
          setCamera({ lookat: [0, 0, lookatY] });
          setAlignData(data);
          bootScene();
        } else {
          setAlignData(null);
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load preview');
      setAlignData(null);
    } finally {
      setLoading(false);
    }
  }, [sourceFile, selectedRobot, generatorType, config, showRobot, showHuman]);

  // Fetch preview when config or source changes
  useEffect(() => {
    const debounceTimer = setTimeout(() => {
      fetchPreview();
    }, 300); // Debounce 300ms

    return () => clearTimeout(debounceTimer);
  }, [fetchPreview]);

  // Handle body picking on click
  const handleClick = useCallback((_e: React.MouseEvent) => {
    const canvas = canvasRef.current;
    if (!canvas || !alignData) return;

    // For now, just highlight clicked position
    // Actual body picking would require raycasting in Three.js
    const bodyId = Math.floor(Math.random() * alignData.bodyNames.length); // Placeholder
    highlightBody(bodyId, [1, 0.5, 0]); // Orange highlight
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
        onMouseDown={(e) => setCameraState(prev => ({ ...prev, isDragging: true, lastX: e.clientX, lastY: e.clientY }))}
        onMouseMove={(e) => {
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
        }}
        onMouseUp={() => setCameraState(prev => ({ ...prev, isDragging: false }))}
        onMouseLeave={() => setCameraState(prev => ({ ...prev, isDragging: false }))}
        onWheel={(e) => {
          e.preventDefault();
          const delta = e.deltaY > 0 ? 0.1 : -0.1;
          const newDistance = Math.max(0.5, Math.min(10, camera.distance + delta));
          setCameraState(prev => ({ ...prev, distance: newDistance }));
          setCamera({ distance: newDistance });
        }}
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

        {/* Grid pattern - only show when no 3D model is loaded */}
        {!alignData && (
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
        )}

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
              {sourceFile ? 'Loading motion preview...' : '3D Preview: '}{selectedRobot || 'Select a robot'}
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

      {/* Display toggles: robot / human (independently toggleable) */}
      <div
        style={{
          position: 'absolute',
          top: 12,
          right: 12,
          display: 'flex',
          gap: 8,
          zIndex: 10
        }}
      >
        {/* Robot */}
        <button
          onClick={toggleRobot}
          disabled={!canShowRobot}
          style={{
            width: 36,
            height: 36,
            borderRadius: 8,
            border: showRobot ? '2px solid #3b82f6' : '2px solid rgba(255,255,255,0.2)',
            background: showRobot ? 'rgba(59,130,246,0.3)' : 'rgba(0,0,0,0.4)',
            color: canShowRobot ? 'rgba(255,255,255,0.9)' : 'rgba(255,255,255,0.3)',
            cursor: canShowRobot ? 'pointer' : 'not-allowed',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: 16,
            opacity: canShowRobot ? 1 : 0.5,
            transition: 'all 0.2s ease'
          }}
          title="机器人"
        >
          🤖
        </button>

        {/* Human */}
        <button
          onClick={toggleHuman}
          disabled={!canShowHuman}
          style={{
            width: 36,
            height: 36,
            borderRadius: 8,
            border: showHuman ? '2px solid #3b82f6' : '2px solid rgba(255,255,255,0.2)',
            background: showHuman ? 'rgba(59,130,246,0.3)' : 'rgba(0,0,0,0.4)',
            color: canShowHuman ? 'rgba(255,255,255,0.9)' : 'rgba(255,255,255,0.3)',
            cursor: canShowHuman ? 'pointer' : 'not-allowed',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: 16,
            opacity: canShowHuman ? 1 : 0.5,
            transition: 'all 0.2s ease'
          }}
          title="人体"
        >
          🧍
        </button>
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
