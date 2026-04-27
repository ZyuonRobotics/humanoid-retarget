import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useConfigContext } from '../../contexts/ConfigContext';
import { modelApi, RetargetPreviewResponse } from '../../api/client';
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
  loadRobotPlayerMotion,
  loadHumanPlayerMotion,
} from './mujoco';

// Module-level cache so robot mesh data is not re-fetched across re-renders or config changes
const robotDataCache = new Map<string, { xml: string; meshes: Record<string, string>; body_names: string[] }>();

interface Viewer3DProps {
  sourceFile?: string;
  activePanel?: string;
  playerMotion?: {
    type: 'robot' | 'human' | 'retarget-preview';
    robotName: string;
    motionFile: string;
    generatorType?: string;
  } | null;
  // Retarget preview data (when retarget completes but not yet saved)
  retargetPreviewData?: RetargetPreviewResponse | null;
  // Playback control props
  playing?: boolean;
  onFrameChange?: (frame: number, total: number) => void;
}

const Viewer3D: React.FC<Viewer3DProps> = ({ sourceFile, activePanel, playerMotion, retargetPreviewData, playing = false, onFrameChange }) => {
  const { selectedRobot, config, generatorType } = useConfigContext();
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const threeSceneRef = useRef<any>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  const [alignData, setAlignData] = useState<AlignPreviewData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [playerModelLoaded, setPlayerModelLoaded] = useState(false);

  // Independent visibility toggles. When both are false nothing is shown;
  // when both are true the combined human+robot preview is shown.
  const [showRobot, setShowRobot] = useState(false);
  const [showHuman, setShowHuman] = useState(false);

  // Skin visibility toggle for human model
  const [showSkin, setShowSkin] = useState(true);

  // Keep a ref so fetchPreview can read the latest config without it being a dep
  const configRef = useRef(config);
  useEffect(() => { configRef.current = config; }, [config]);

  // Track previous playerMotion to detect actual changes
  const prevPlayerMotionRef = useRef<typeof playerMotion>(null);
  const prevRetargetPreviewDataRef = useRef<typeof retargetPreviewData>(null);
  const prevShowSkinRef = useRef<boolean>(showSkin);

  // Shared bootScene function - creates Three.js scene from loaded MuJoCo model
  // MUST be defined before any useEffect that uses it
  const bootScene = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) {
      console.warn('bootScene: canvas not available');
      return false;
    }
    if (!threeSceneRef.current) {
      console.log('bootScene: creating new ThreeScene');
      threeSceneRef.current = initThreeScene(canvas);
      if (!threeSceneRef.current) {
        console.error('bootScene: failed to create ThreeScene');
        return false;
      }
    }
    console.log('bootScene: checking scene creation conditions', {
      hasThreeScene: !!threeSceneRef.current,
      hasMujocoModule: !!mujocoModule,
      hasCurrentModel: !!currentModel,
      hasCurrentData: !!currentData,
      modelNbody: currentModel?.nbody
    });
    if (threeSceneRef.current && mujocoModule && currentModel && currentData) {
      console.log('bootScene: creating scene with model nbody=', currentModel.nbody);
      try {
        threeSceneRef.current.createScene(mujocoModule, currentModel, currentData as any);
        startRendering();
        console.log('bootScene: scene created and rendering started');
        return true;
      } catch (err) {
        console.error('bootScene: failed to create scene:', err);
        return false;
      }
    }
    console.warn('bootScene: missing required objects for scene creation');
    return false;
  }, []);

  // Clear models when switching between retargeter and player modes
  useEffect(() => {
    setShowRobot(false);
    setShowHuman(false);
    setShowSkin(true);
    setAlignData(null);
    setPlayerModelLoaded(false);
    dispose();
  }, [activePanel]);

  // Player mode: load and display robot motion
  useEffect(() => {
    if (activePanel !== 'player' || !playerMotion) return;

    const prevPlayerMotion = prevPlayerMotionRef.current;
    const prevRetargetData = prevRetargetPreviewDataRef.current;

    // For retarget-preview mode, skip reload if only showSkin changed
    if (playerMotion.type === 'retarget-preview') {
      // Check if only showSkin changed (playerMotion and retargetPreviewData are the same)
      if (prevPlayerMotion?.type === 'retarget-preview' &&
          prevPlayerMotion.robotName === playerMotion.robotName &&
          prevPlayerMotion.motionFile === playerMotion.motionFile &&
          prevRetargetData === retargetPreviewData &&
          threeSceneRef.current) {
        // Only showSkin changed, just toggle visibility
        threeSceneRef.current.setShowSkin(showSkin);
        return;
      }
    }

    // For robot mode, skip reload if only showSkin changed (robot has no skin)
    if (playerMotion.type === 'robot') {
      if (prevPlayerMotion?.type === 'robot' &&
          prevPlayerMotion.robotName === playerMotion.robotName &&
          prevPlayerMotion.motionFile === playerMotion.motionFile &&
          threeSceneRef.current) {
        // Only showSkin changed, but robot has no skin, so do nothing
        return;
      }
    }

    // For human mode, check if anything actually changed
    if (playerMotion.type === 'human') {
      const prevShowSkin = prevShowSkinRef.current;
      if (prevPlayerMotion?.type === 'human' &&
          prevPlayerMotion.generatorType === playerMotion.generatorType &&
          prevPlayerMotion.motionFile === playerMotion.motionFile &&
          prevShowSkin === showSkin &&
          threeSceneRef.current) {
        // Nothing changed, skip reload
        return;
      }
    }

    const loadPlayer = async () => {
      const canvas = canvasRef.current;
      if (!canvas) return;

      setLoading(true);
      setError(null);

      try {
        // Clear previous scene and model state BEFORE loading new data
        dispose();
        if (threeSceneRef.current) {
          threeSceneRef.current.dispose();
          threeSceneRef.current = null;
        }

        let motionData = null;

        if (playerMotion.type === 'retarget-preview') {
          // Retarget preview mode - requires retargetPreviewData
          if (!retargetPreviewData) {
            setLoading(false);
            return; // No preview data yet, skip loading
          }

          // Load robot meshes (required for combined human-robot XML)
          let robotCached = robotDataCache.get(retargetPreviewData.robot_name);
          if (!robotCached) {
            try {
              const data = await modelApi.getRobotMJCFWithMeshes(retargetPreviewData.robot_name);
              robotCached = data;
              robotDataCache.set(retargetPreviewData.robot_name, data);
            } catch (err) {
              setError('Failed to load robot mesh data');
              setLoading(false);
              return;
            }
          }

          if (!robotCached) {
            setError('Failed to load robot mesh data');
            setLoading(false);
            return;
          }

          // Initialize MuJoCo with combined human-robot XML and robot meshes
          await initMuJoCo(retargetPreviewData.xml, undefined, robotCached.meshes || {});

          motionData = {
            robotName: retargetPreviewData.robot_name,
            motionFile: retargetPreviewData.output_name,
            frameNum: retargetPreviewData.frame_num,
            frameRate: retargetPreviewData.frame_rate,
            bodyNames: retargetPreviewData.body_names,
            nbody: retargetPreviewData.nbody,
            xpos: retargetPreviewData.body_transforms.xpos,
            xquat: retargetPreviewData.body_transforms.xquat,
          };
        } else if (playerMotion.type === 'robot') {
          // Robot motion playback
          motionData = await loadRobotPlayerMotion(playerMotion.robotName, playerMotion.motionFile);
          if (!motionData) {
            setError('Failed to load motion data');
            return;
          }

          // Load robot model (with cache)
          let robotCached = robotDataCache.get(playerMotion.robotName);
          if (!robotCached) {
            try {
              const data = await modelApi.getRobotMJCFWithMeshes(playerMotion.robotName);
              robotCached = data;
              robotDataCache.set(playerMotion.robotName, data);
            } catch (err) {
              setError('Failed to load robot data');
              return;
            }
          }

          if (!robotCached) {
            setError('Failed to load robot data');
            return;
          }

          await initMuJoCo(robotCached.xml, undefined, robotCached.meshes || {});
        } else if (playerMotion.type === 'human') {
          // Human motion playback
          const generatorType = playerMotion.generatorType || 'bvh';

          // Remove generator_type prefix from motion file path if present
          // e.g., "smpl/elegant.npz" -> "elegant.npz"
          let motionFilePath = playerMotion.motionFile;
          const prefix = `${generatorType}/`;
          if (motionFilePath.startsWith(prefix)) {
            motionFilePath = motionFilePath.substring(prefix.length);
          }

          motionData = await loadHumanPlayerMotion(generatorType, motionFilePath, showSkin);

          if (!motionData) {
            setError('Failed to load human motion data');
            return;
          }

          // Initialize MuJoCo with human model XML (includes skin if SMPL)
          await initMuJoCo(motionData.xml!);
        } else {
          // Unknown playerMotion type, skip loading
          console.warn('Unknown playerMotion type:', playerMotion.type);
          return;
        }

        // Create Three.js scene
        console.log('Player mode: creating ThreeScene', {
          hasCanvas: !!canvas,
          hasMujocoModule: !!mujocoModule,
          hasCurrentModel: !!currentModel,
          hasCurrentData: !!currentData,
          motionDataFrameNum: motionData?.frameNum
        });

        // initThreeScene will automatically call createScene if model is loaded
        threeSceneRef.current = initThreeScene(canvas);
        if (threeSceneRef.current) {
          console.log('Player mode: ThreeScene created, setting player motion');

          // Set player motion data for animation (don't autostart, let playing prop control it)
          threeSceneRef.current.setPlayerMotion({
            xpos: motionData.xpos,
            xquat: motionData.xquat,
            frameNum: motionData.frameNum,
            frameRate: motionData.frameRate,
            nbody: motionData.nbody
          }, false);

          // Set up frame change callback to update slider
          threeSceneRef.current.setPlayerFrameCallback((frame: number) => {
            onFrameChange?.(frame, motionData.frameNum);
          });

          // Report frame info to parent
          onFrameChange?.(0, motionData.frameNum);

          // Set camera to look at model
          setCamera({ lookat: [0, 0, 0.5] });

          // Set initial showSkin state for retarget-preview mode
          if (playerMotion.type === 'retarget-preview') {
            threeSceneRef.current.setShowSkin(showSkin);
          }

          // Mark player model as loaded to hide grid
          setPlayerModelLoaded(true);

          // Force initial render to show frame 0
          threeSceneRef.current.setPlayerFrame(0);

          console.log('Player mode: scene setup complete');
        } else {
          console.error('Player mode: failed to create ThreeScene');
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load player motion');
        setPlayerModelLoaded(false);
      } finally {
        setLoading(false);
        // Update refs after successful load
        prevPlayerMotionRef.current = playerMotion;
        prevRetargetPreviewDataRef.current = retargetPreviewData;
        prevShowSkinRef.current = showSkin;
      }
    };

    loadPlayer();
  }, [playerMotion, activePanel, retargetPreviewData, showSkin, onFrameChange, bootScene]);

  // Player mode: control animation based on playing prop
  useEffect(() => {
    if (!threeSceneRef.current || activePanel !== 'player' || !playerMotion) return;

    if (playing) {
      threeSceneRef.current.resumePlayer();
    } else {
      threeSceneRef.current.pausePlayer();
    }
  }, [playing, activePanel, playerMotion]);

  // Player mode: handle seek (drag slider to change frame)
  useEffect(() => {
    if (!threeSceneRef.current || activePanel !== 'player' || !playerMotion) return;

    const handleSeek = (frame: number) => {
      if (threeSceneRef.current) {
        threeSceneRef.current.setPlayerFrame(frame);
        onFrameChange?.(frame, threeSceneRef.current.getPlayerFrame());
      }
    };

    // Store seek handler for external access via window
    (window as any).__playerSeekHandler = handleSeek;
  }, [activePanel, playerMotion, onFrameChange]);

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
    // Cancel any previous in-flight request
    abortControllerRef.current?.abort();
    const abortController = new AbortController();
    abortControllerRef.current = abortController;

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

    // Helper: get robot MJCF+meshes, using cache to avoid repeated heavy fetches
    const getRobotData = async (robotName: string) => {
      const cached = robotDataCache.get(robotName);
      if (cached) return cached;
      const data = await modelApi.getRobotMJCFWithMeshes(robotName);
      robotDataCache.set(robotName, data);
      return data;
    };

    try {
      if (showRobot && showHuman) {
        // Combined human+robot preview. Robot meshes are referenced by the
        // combined XML, so fetch them alongside the align preview.
        const [data, robotData] = await Promise.all([
          fetchAlignPreview(sourceFile!, selectedRobot!, generatorType!, configRef.current),
          getRobotData(selectedRobot!),
        ]);
        if (abortController.signal.aborted) return;
        if (data) {
          await initMuJoCo(data.xml, data.qpos, robotData.meshes || {});
          const lookatY = data.globalBodyRatio * 0.5;
          setCamera({ lookat: [0, 0, lookatY] });
          setAlignData(data);
          setTimeout(() => bootScene(), 100);
        } else {
          setAlignData(null);
        }
      } else if (showRobot) {
        // Robot only — use cache to avoid re-fetching unchanged mesh data
        const robotData = await getRobotData(selectedRobot!);
        if (abortController.signal.aborted) return;
        await loadRobotModel(selectedRobot!, robotData.xml, robotData.meshes || {});
        setAlignData({
          xml: robotData.xml,
          qpos: [],
          bodyNames: robotData.body_names || [],
          globalBodyRatio: 1.0,
        });
        setCamera({ lookat: [0, 0, 0.5] });
        setTimeout(() => bootScene(), 100);
      } else if (showHuman) {
        // Human only — parametric bodies, no mesh files required
        const data = await fetchHumanPreview(sourceFile!, generatorType!, configRef.current);
        if (abortController.signal.aborted) return;
        if (data) {
          await initMuJoCo(data.xml, data.qpos);
          const lookatY = data.globalBodyRatio * 0.5;
          setCamera({ lookat: [0, 0, lookatY] });
          setAlignData(data);
          setTimeout(() => bootScene(), 100);
        } else {
          setAlignData(null);
        }
      }
    } catch (err) {
      if (abortController.signal.aborted) return;
      setError(err instanceof Error ? err.message : 'Failed to load preview');
      setAlignData(null);
    } finally {
      if (!abortController.signal.aborted) {
        setLoading(false);
      }
    }
  }, [sourceFile, selectedRobot, generatorType, showRobot, showHuman, bootScene]);

  // Re-fetch when non-config things change (robot switch, toggle, file change)
  useEffect(() => {
    const debounceTimer = setTimeout(() => {
      fetchPreview();
    }, 300);

    return () => clearTimeout(debounceTimer);
  }, [fetchPreview]);

  // Re-fetch when config changes, but only if human data is involved
  const showHumanRef = useRef(showHuman);
  showHumanRef.current = showHuman;
  useEffect(() => {
    if (!showHumanRef.current) return; // robot-only view is config-independent
    const debounceTimer = setTimeout(() => {
      fetchPreview();
    }, 300);

    return () => clearTimeout(debounceTimer);
  }, [config, fetchPreview]);

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
        {!alignData && !playerModelLoaded && (
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
        ) : !alignData && activePanel !== 'player' ? (
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
        ) : null}

        {/* Canvas - always render in player mode or when alignData exists */}
        {(activePanel === 'player' || alignData) && (
          <canvas
            ref={canvasRef}
            onClick={handleClick}
            style={{
              background: 'transparent',
              borderRadius: 8,
              width: '100%',
              height: '100%',
              display: 'block',
            }}
          />
        )}
      </div>

      {/* Display toggles: robot / human (only show in retargeter mode) */}
      {activePanel !== 'player' && (
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

          {/* Skin toggle - only enabled when human is showing and generator type is SMPL */}
          {generatorType === 'smpl' && (
            <button
              onClick={() => {
                const newShowSkin = !showSkin;
                setShowSkin(newShowSkin);
                threeSceneRef.current?.setShowSkin(newShowSkin);
              }}
              disabled={!showHuman}
              style={{
                width: 36,
                height: 36,
                borderRadius: 8,
                border: showHuman && showSkin ? '2px solid #10b981' : '2px solid rgba(255,255,255,0.2)',
                background: showHuman && showSkin ? 'rgba(16,185,129,0.3)' : 'rgba(0,0,0,0.4)',
                color: showHuman ? 'rgba(255,255,255,0.9)' : 'rgba(255,255,255,0.3)',
                cursor: showHuman ? 'pointer' : 'not-allowed',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: 16,
                opacity: showHuman ? 1 : 0.5,
                transition: 'all 0.2s ease'
              }}
              title="皮肤"
            >
              👤
            </button>
          )}
        </div>
      )}

      {/* Skin toggle for player mode - show for SMPL human motion or retarget-preview with SMPL */}
      {activePanel === 'player' && (
        (playerMotion?.type === 'human' && playerMotion?.generatorType === 'smpl') ||
        (playerMotion?.type === 'retarget-preview' && generatorType === 'smpl')
      ) && (
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
          <button
            onClick={() => {
              const newShowSkin = !showSkin;
              setShowSkin(newShowSkin);
              threeSceneRef.current?.setShowSkin(newShowSkin);
            }}
            style={{
              width: 36,
              height: 36,
              borderRadius: 8,
              border: showSkin ? '2px solid #10b981' : '2px solid rgba(255,255,255,0.2)',
              background: showSkin ? 'rgba(16,185,129,0.3)' : 'rgba(0,0,0,0.4)',
              color: 'rgba(255,255,255,0.9)',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: 16,
              transition: 'all 0.2s ease'
            }}
            title="皮肤"
          >
            👤
          </button>
        </div>
      )}

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
