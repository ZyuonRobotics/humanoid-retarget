import React, { useState, useEffect, useRef } from 'react';
import { Button, Space, Upload, Slider } from 'antd';
import { PlayCircleOutlined, PauseCircleOutlined, UploadOutlined, SaveOutlined, ReloadOutlined } from '@ant-design/icons';
import { useTranslation } from 'react-i18next';

import TopBar from './components/TopBar';
import Viewer3D from './components/Viewer3D';
import DraggablePanel from './components/DraggablePanel';
import BaseSettingsWidget from './components/Widgets/BaseSettingsWidget';
import HumanSettingsWidget from './components/Widgets/BodyRotateWidget';
import TrackersWidget from './components/Widgets/TrackersWidget';
import BodyTreeWidget from './components/Widgets/BodyTreeWidget';
import ErrorBoundary from './components/ErrorBoundary';
import { ConfigProvider, useConfigContext } from './contexts/ConfigContext';
import { MotionProvider, useMotionContext } from './contexts/MotionContext';
import { PerformanceProvider } from './contexts/PerformanceContext';

type ThemeType = 'dark' | 'light' | 'ocean' | 'forest' | 'sunset';

const AppContent: React.FC = () => {
  const { t } = useTranslation();
  const {
    selectedMotion,
    uploadMotion,
    handleRetarget,
    handleSaveRetarget,
    retargetPreviewData,
    setRetargetPreviewData,
    loading,
    streamingMetadata,
    streamingFrames,
    isStreaming,
    streamingProgress
  } = useMotionContext();
  const { bodyTree, config, setConfig } = useConfigContext();
  const [activePanel, setActivePanel] = useState<string>('retargeter');
  const [theme, setTheme] = useState<ThemeType>(() => {
    const saved = localStorage.getItem('theme');
    return (saved as ThemeType) || 'dark';
  });
  const [containerWidth, setContainerWidth] = useState<number>(window.innerWidth);
  const appContainerRef = useRef<HTMLDivElement>(null);

  // Player mode state
  const [playerMotion, setPlayerMotion] = useState<{
    type: 'robot' | 'human' | 'retarget-preview' | 'retarget-stream';
    robotName: string;
    motionFile: string;
    generatorType?: string;
    reloadKey?: number;
  } | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [playbackFrame, setPlaybackFrame] = useState({ current: 0, total: 0 });

  // Retarget preview mode state - for future use
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const [_isRetargetPreviewPlaying, setIsRetargetPreviewPlaying] = useState(false);
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const [_retargetPreviewFrame, setRetargetPreviewFrame] = useState({ current: 0, total: 0 });

  // Get container width for rightmost positioning
  useEffect(() => {
    const updateWidth = () => {
      if (appContainerRef.current) {
        setContainerWidth(appContainerRef.current.offsetWidth);
      }
    };
    updateWidth();
    window.addEventListener('resize', updateWidth);
    return () => window.removeEventListener('resize', updateWidth);
  }, []);

  // Handle streaming metadata - switch to player mode when first metadata arrives
  useEffect(() => {
    if (streamingMetadata && isStreaming) {
      console.log('Streaming metadata received, switching to player mode', {
        robot: streamingMetadata.robot_name,
        frameNum: streamingMetadata.frame_num
      });
      // Switch to player mode to show streaming retarget
      setActivePanel('player');
      setIsPlaying(false);
      setRetargetPreviewFrame({ current: 0, total: streamingMetadata.frame_num });
      setIsRetargetPreviewPlaying(false);
      // Set player motion to streaming type
      setPlayerMotion({
        type: 'retarget-stream',
        robotName: streamingMetadata.robot_name,
        motionFile: streamingMetadata.output_name,
      });
    }
  }, [streamingMetadata, isStreaming]);

  // Handle retarget preview - when retargetPreviewData exists, switch to player mode
  useEffect(() => {
    if (retargetPreviewData) {
      console.log('Retarget preview data received, switching to player mode', {
        robot: retargetPreviewData.robot_name,
        frameNum: retargetPreviewData.frame_num
      });
      // Switch to player mode to show retarget preview
      setActivePanel('player');
      setIsPlaying(false);
      setRetargetPreviewFrame({ current: 0, total: retargetPreviewData.frame_num });
      setIsRetargetPreviewPlaying(false);
      // Set player motion to a special retarget-preview type
      setPlayerMotion({
        type: 'retarget-preview',
        robotName: retargetPreviewData.robot_name,
        motionFile: retargetPreviewData.output_name,
      });
    }
  }, [retargetPreviewData]);

  // Apply theme
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('theme', theme);
  }, [theme]);

  // Handle panel change - clear retarget data when switching to retargeter
  const handlePanelChange = (panel: string) => {
    setActivePanel(panel);
    setIsPlaying(false);
    setPlaybackFrame({ current: 0, total: 0 });

    // Clear retarget preview/stream data when switching to retargeter
    if (panel === 'retargeter') {
      setRetargetPreviewData(null);
      setPlayerMotion(null);
    }
  };

  // Handle close retarget stream - return to normal player
  const handleCloseRetargetStream = () => {
    setRetargetPreviewData(null);
    setPlayerMotion(null);
    setIsPlaying(false);
    setPlaybackFrame({ current: 0, total: 0 });
  };

  return (
    <div className="app-container" ref={appContainerRef}>
      {/* Top Bar */}
      <TopBar
        activePanel={activePanel}
        playerMotion={playerMotion}
        onPanelChange={handlePanelChange}
        theme={theme}
        onThemeChange={setTheme}
        onPlayerMotionChange={(type, robotName, motionFile, generatorType) => {
          setIsPlaying(false);
          setPlaybackFrame({ current: 0, total: 0 });
          setPlayerMotion({ type, robotName, motionFile, generatorType });
        }}
        onCloseRetargetStream={handleCloseRetargetStream}
      />

      {/* 3D Background */}
      <div className="viewer-3d-background">
        <Viewer3D
          sourceFile={selectedMotion}
          activePanel={activePanel}
          playerMotion={playerMotion}
          retargetPreviewData={retargetPreviewData}
          streamingMetadata={streamingMetadata}
          streamingFrames={streamingFrames}
          playing={isPlaying}
          onFrameChange={(current, total) => setPlaybackFrame(prev => ({ ...prev, current, total }))}
        />
      </div>

      {/* Floating Panels */}
      {activePanel === 'retargeter' && (
        <>
          {/* Base Settings Panel - Top Left */}
          <ErrorBoundary>
            <DraggablePanel
              title={t('configPanel.tabs.robotSettings')}
              defaultX={40}
              defaultY={220}
              defaultWidth={510}
              defaultHeight={300}
              minimizedIndex={0}
            >
              <BaseSettingsWidget config={config} onChange={setConfig} />
            </DraggablePanel>
          </ErrorBoundary>

          {/* Human Settings Panel - Left Bottom */}
          <ErrorBoundary>
            <DraggablePanel
              title={t('configPanel.tabs.humanSettings')}
              defaultX={40}
              defaultY={550}
              defaultWidth={510}
              defaultHeight={400}
              minimizedIndex={1}
            >
              <HumanSettingsWidget config={config} onChange={setConfig} bodyTree={bodyTree} />
            </DraggablePanel>
          </ErrorBoundary>

          {/* Retargeting Parameters Panel - Middle Left */}
          <ErrorBoundary>
            <DraggablePanel
              title={t('configPanel.tabs.retargetingParams')}
              defaultX={containerWidth - 520}
              defaultY={500}
              defaultWidth={510}
              defaultHeight={400}
              minimizedIndex={2}
            >
              <TrackersWidget config={config} onChange={setConfig} />
            </DraggablePanel>
          </ErrorBoundary>

          {/* Body Tree Panel - Right Side Full Height */}
          <ErrorBoundary>
            <DraggablePanel
              title={t('configPanel.tabs.bodyTree')}
              defaultX={containerWidth - 460}
              defaultY={220}
              defaultWidth={450}
              defaultHeight="calc(100vh - 80px)"
              minimizedIndex={3}
            >
              <BodyTreeWidget bodyTree={bodyTree} />
            </DraggablePanel>
          </ErrorBoundary>

          {/* Action Buttons - Bottom Center */}
          <div className="action-buttons-bottom">
            <Space>
              <Upload.Dragger
                showUploadList={false}
                accept=".bvh,.npz"
                beforeUpload={(file) => {
                  uploadMotion(file);
                  return false;
                }}
              >
                <Button icon={<UploadOutlined />} size="large">
                  {t('button.uploadMotion')}
                </Button>
              </Upload.Dragger>
              <Button
                type="primary"
                size="large"
                icon={<PlayCircleOutlined />}
                onClick={handleRetarget}
                loading={loading}
              >
                {t('button.retarget')}
              </Button>
            </Space>
          </div>
        </>
      )}

      {activePanel === 'player' && (
        <div className="action-buttons-bottom">
          <Space direction="vertical" style={{ width: '100%', alignItems: 'center' }}>
            {playbackFrame.total > 0 && (
              <div style={{ width: 400, display: 'flex', alignItems: 'center', gap: 12 }}>
                <div style={{ flex: 1, position: 'relative', height: 24 }}>
                  {/* Custom progress bar with three states */}
                  <div
                    style={{
                      position: 'absolute',
                      top: '50%',
                      left: 0,
                      transform: 'translateY(-50%)',
                      width: '100%',
                      height: 4,
                      background: '#3a3a3a',
                      borderRadius: 2,
                      overflow: 'hidden'
                    }}
                  >
                    {/* Loaded frames background (gray) */}
                    {isStreaming && streamingProgress.total > 0 && (
                      <div
                        style={{
                          position: 'absolute',
                          left: 0,
                          top: 0,
                          height: '100%',
                          width: `${(streamingProgress.current / streamingProgress.total) * 100}%`,
                          background: '#6b6b6b',
                          transition: 'width 0.3s ease'
                        }}
                      />
                    )}
                    {/* Played frames foreground (white) */}
                    <div
                      style={{
                        position: 'absolute',
                        left: 0,
                        top: 0,
                        height: '100%',
                        width: `${(playbackFrame.current / (playbackFrame.total - 1)) * 100}%`,
                        background: '#ffffff',
                        transition: 'width 0.1s linear'
                      }}
                    />
                  </div>

                  {/* Invisible slider for interaction */}
                  <Slider
                    min={0}
                    max={playbackFrame.total - 1}
                    value={playbackFrame.current}
                    style={{
                      position: 'absolute',
                      width: '100%',
                      top: '50%',
                      transform: 'translateY(-50%)',
                      margin: 0
                    }}
                    tooltip={{ formatter: (v) => `${v} / ${playbackFrame.total - 1}` }}
                    onChange={(value) => {
                      // Update local state immediately for responsive UI
                      setPlaybackFrame(prev => ({ ...prev, current: value }));
                      // Also seek the ThreeScene player to this frame
                      const seekHandler = (window as any).__playerSeekHandler;
                      if (seekHandler) {
                        seekHandler(value);
                      }
                    }}
                    styles={{
                      track: {
                        background: 'transparent'
                      },
                      tracks: {
                        background: 'transparent'
                      }
                    }}
                  />
                </div>
                <span style={{ color: 'rgba(255,255,255,0.7)', fontSize: 12, whiteSpace: 'nowrap' }}>
                  {playbackFrame.current} / {playbackFrame.total - 1}
                  {isStreaming && ` (${streamingProgress.current}/${streamingProgress.total})`}
                </span>
              </div>
            )}
            <Space>
              {/* Play/Pause button - always show in player mode */}
              <Button
                type={retargetPreviewData || streamingMetadata ? 'default' : 'primary'}
                size="large"
                icon={isPlaying ? <PauseCircleOutlined /> : <PlayCircleOutlined />}
                onClick={() => setIsPlaying(v => !v)}
                disabled={!playerMotion}
              >
                {isPlaying ? t('player.pause') : t('player.play')}
              </Button>

              {/* Reload button - reload human config and motion */}
              {playerMotion?.type === 'human' && (
                <Button
                  size="large"
                  icon={<ReloadOutlined />}
                  onClick={() => {
                    if (playerMotion) {
                      // Trigger reload by adding a new reloadKey timestamp
                      setIsPlaying(false);
                      setPlaybackFrame({ current: 0, total: 0 });
                      setPlayerMotion({ ...playerMotion, reloadKey: Date.now() });
                    }
                  }}
                  disabled={!playerMotion}
                  title={t('player.reload') || 'Reload'}
                />
              )}

              {/* Save button - only show when in retarget preview mode or streaming complete */}
              {(retargetPreviewData || (streamingMetadata && !isStreaming)) && (
                <Button
                  type="primary"
                  size="large"
                  icon={<SaveOutlined />}
                  onClick={handleSaveRetarget}
                  loading={loading}
                >
                  {t('saveRetarget') || 'Save Retarget'}
                </Button>
              )}
            </Space>
          </Space>
        </div>
      )}
    </div>
  );
};

const App: React.FC = () => {
  return (
    <PerformanceProvider>
      <ConfigProvider>
        <MotionProvider>
          <AppContent />
        </MotionProvider>
      </ConfigProvider>
    </PerformanceProvider>
  );
};

export default App;