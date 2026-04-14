import React, { useState, useEffect, useRef } from 'react';
import { Button, Space, Upload } from 'antd';
import { PlayCircleOutlined, UploadOutlined } from '@ant-design/icons';
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

type ThemeType = 'dark' | 'light' | 'ocean' | 'forest' | 'sunset';

const AppContent: React.FC = () => {
  const { t } = useTranslation();
  const { selectedMotion, uploadMotion, handleRetarget } = useMotionContext();
  const { loading, bodyTree, config, setConfig } = useConfigContext();
  const [activePanel, setActivePanel] = useState<string>('config');
  const [theme, setTheme] = useState<ThemeType>(() => {
    const saved = localStorage.getItem('theme');
    return (saved as ThemeType) || 'dark';
  });
  const [containerWidth, setContainerWidth] = useState<number>(window.innerWidth);
  const appContainerRef = useRef<HTMLDivElement>(null);

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

  // Apply theme
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('theme', theme);
  }, [theme]);

  return (
    <div className="app-container" ref={appContainerRef}>
      {/* Top Bar */}
      <TopBar
        activePanel={activePanel}
        onPanelChange={setActivePanel}
        theme={theme}
        onThemeChange={setTheme}
      />

      {/* 3D Background */}
      <div className="viewer-3d-background">
        <Viewer3D sourceFile={selectedMotion} />
      </div>

      {/* Floating Panels */}
      {activePanel === 'config' && (
        <>
          {/* Base Settings Panel - Top Left */}
          <ErrorBoundary>
            <DraggablePanel
              title={t('configPanel.tabs.robotSettings')}
              defaultX={40}
              defaultY={100}
              defaultWidth={510}
              defaultHeight={480}
            >
              <BaseSettingsWidget config={config} onChange={setConfig} />
            </DraggablePanel>
          </ErrorBoundary>

          {/* Human Settings Panel - Left Bottom */}
          <ErrorBoundary>
            <DraggablePanel
              title={t('configPanel.tabs.humanSettings')}
              defaultX={40}
              defaultY={600}
              defaultWidth={510}
              defaultHeight={400}
            >
              <HumanSettingsWidget config={config} onChange={setConfig} />
            </DraggablePanel>
          </ErrorBoundary>

          {/* Retargeting Parameters Panel - Middle Left */}
          <ErrorBoundary>
            <DraggablePanel
              title={t('configPanel.tabs.retargetingParams')}
              defaultX={560}
              defaultY={250}
              defaultWidth={510}
              defaultHeight={540}
            >
              <TrackersWidget config={config} onChange={setConfig} />
            </DraggablePanel>
          </ErrorBoundary>

          {/* Body Tree Panel - Right Side Full Height */}
          <ErrorBoundary>
            <DraggablePanel
              title={t('configPanel.tabs.bodyTree')}
              defaultX={containerWidth - 450}
              defaultY={60}
              defaultWidth={450}
              defaultHeight="calc(100vh - 80px)"
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
    </div>
  );
};

const App: React.FC = () => {
  return (
    <ConfigProvider>
      <MotionProvider>
        <AppContent />
      </MotionProvider>
    </ConfigProvider>
  );
};

export default App;