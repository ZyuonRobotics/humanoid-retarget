import React, { useState, useEffect, useRef } from 'react';
import { useConfigContext } from '../../contexts/ConfigContext';

const Viewer3D: React.FC = () => {
  const { selectedRobot } = useConfigContext();
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [mjcfXml, setMjcfXml] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (selectedRobot) {
      loadRobotModel();
    }
  }, [selectedRobot]);

  const loadRobotModel = async () => {
    try {
      setLoading(true);
      // TODO: Use modelApi.getRobotMJCF when backend is ready
      // const data = await modelApi.getRobotMJCF(selectedRobot);
      // setMjcfXml(data.xml);
      // TODO: Initialize MuJoCo WASM here
    } catch (error) {
      // Background viewer - show placeholder instead of error
      console.debug('Viewer3D: Could not load robot model');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      style={{
        width: '100%',
        height: '100%',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: 'linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%)',
        position: 'relative',
        overflow: 'hidden',
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
        }}
      />

      {/* 3D Canvas placeholder */}
      {loading ? (
        <div style={{ color: 'rgba(255,255,255,0.5)', fontSize: 14 }}>
          Loading 3D Viewer...
        </div>
      ) : mjcfXml ? (
        <canvas
          ref={canvasRef}
          width={800}
          height={600}
          style={{
            background: 'transparent',
            borderRadius: 8,
          }}
        />
      ) : (
        <div
          style={{
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
      )}
    </div>
  );
};

export default Viewer3D;