import React, { useState, useEffect } from 'react';
import { message, Button, Space, Upload } from 'antd';
import { PlayCircleOutlined, UploadOutlined } from '@ant-design/icons';
import { useTranslation } from 'react-i18next';

import TopBar from './components/TopBar';
import Viewer3D from './components/Viewer3D';
import DraggablePanel from './components/DraggablePanel';
import BaseSettingsWidget from './components/Widgets/BaseSettingsWidget';
import BodyRatioWidget from './components/Widgets/BodyRatioWidget';
import BodyRotateWidget from './components/Widgets/BodyRotateWidget';
import TrackersWidget from './components/Widgets/TrackersWidget';
import BodyTreeWidget from './components/Widgets/BodyTreeWidget';
import { configApi, modelApi } from './api/client';
import { RobotInfo, RetargetConfig, defaultRetargetConfig } from './types/config';

const App: React.FC = () => {
  const { t } = useTranslation();
  const [theme, setTheme] = useState<'light' | 'dark'>(() => {
    const saved = localStorage.getItem('theme');
    return (saved as 'light' | 'dark') || 'dark';
  });
  const [robots, setRobots] = useState<string[]>([]);
  const [selectedRobot, setSelectedRobot] = useState<string>('');
  const [generatorType, setGeneratorType] = useState<string>('bvh');
  const [configs, setConfigs] = useState<string[]>([]);
  const [selectedConfig, setSelectedConfig] = useState<string>('default');
  const [activePanel, setActivePanel] = useState<string>('config');
  const [config, setConfig] = useState<RetargetConfig>(defaultRetargetConfig);
  const [bodyTree, setBodyTree] = useState<any>({});
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [selectedMotion, setSelectedMotion] = useState<string>('');

  // Apply theme
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('theme', theme);
  }, [theme]);

  useEffect(() => {
    loadRobots();
  }, []);

  useEffect(() => {
    if (selectedRobot && generatorType) {
      loadConfigs();
    }
  }, [selectedRobot, generatorType]);

  useEffect(() => {
    if (selectedRobot && generatorType && selectedConfig) {
      loadConfig();
      loadBodyTree();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedRobot, generatorType, selectedConfig]);

  const loadRobots = async () => {
    try {
      const data = await configApi.getRobots();
      setRobots(data);
      if (data.length > 0) {
        setSelectedRobot(data[0]);
      }
    } catch (error) {
      message.error(t('message.failedToLoadRobots'));
    }
  };

  const loadConfigs = async () => {
    try {
      const data = await configApi.listConfigs(selectedRobot, generatorType);
      setConfigs(data);
      if (data.length > 0) {
        setSelectedConfig(data[0]);
      } else {
        setSelectedConfig('default');
      }
    } catch (error) {
      message.error(t('message.failedToLoadConfigs'));
    }
  };

  const loadConfig = async () => {
    setLoading(true);
    try {
      const data = await configApi.getConfig(selectedRobot, generatorType, selectedConfig);
      setConfig(data);
    } catch (error) {
      setConfig(defaultRetargetConfig);
    } finally {
      setLoading(false);
    }
  };

  const loadBodyTree = async () => {
    try {
      const data = await configApi.getBodyTree(selectedRobot, generatorType);
      setBodyTree(data);
    } catch (error) {
      console.error('Failed to load body tree', error);
    }
  };

  const saveConfig = async () => {
    setSaving(true);
    try {
      await configApi.saveConfig(selectedRobot, generatorType, selectedConfig, config);
      message.success(t('configPanel.message.configSaved'));
    } catch (error) {
      message.error(t('configPanel.message.failedToSaveConfig'));
    } finally {
      setSaving(false);
    }
  };

  const handleRetarget = async () => {
    if (!selectedRobot || !selectedConfig) {
      message.warning(t('message.pleaseSelectRobotAndConfig'));
      return;
    }
    if (!selectedMotion) {
      message.warning(t('message.pleaseSelectMotion'));
      return;
    }
    setLoading(true);
    try {
      const result = await modelApi.retarget(
        selectedMotion,
        selectedRobot,
        generatorType,
        selectedConfig
      );
      if (result.status === 'success') {
        message.success(t('message.retargetSuccess'));
      } else {
        message.error(t('message.retargetFailed'));
      }
    } catch (error) {
      message.error(t('message.retargetFailed'));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="app-container">
      {/* Top Bar */}
      <TopBar
        robots={robots}
        selectedRobot={selectedRobot}
        onRobotChange={setSelectedRobot}
        generatorType={generatorType}
        onGeneratorTypeChange={setGeneratorType}
        configs={configs}
        selectedConfig={selectedConfig}
        onConfigChange={setSelectedConfig}
        activePanel={activePanel}
        onPanelChange={setActivePanel}
        theme={theme}
        onThemeChange={setTheme}
      />

      {/* 3D Background */}
      <div className="viewer-3d-background">
        <Viewer3D robotName={selectedRobot} />
      </div>

      {/* Floating Panels */}
      {activePanel === 'config' && (
        <>
          {/* Base Settings Panel - Top Left */}
          <DraggablePanel
            title={t('configPanel.tabs.baseSettings')}
            defaultX={40}
            defaultY={100}
            defaultWidth={340}
            defaultHeight={320}
          >
            <BaseSettingsWidget
              config={config}
              onChange={setConfig}
              onSave={saveConfig}
              saving={saving}
            />
          </DraggablePanel>

          {/* Body Ratio Panel - Top Right */}
          <DraggablePanel
            title={t('configPanel.tabs.bodyRatio')}
            defaultX={400}
            defaultY={100}
            defaultWidth={300}
            defaultHeight={280}
          >
            <BodyRatioWidget config={config} onChange={setConfig} />
          </DraggablePanel>

          {/* Body Rotate Panel - Left Middle */}
          <DraggablePanel
            title={t('configPanel.tabs.bodyRotate')}
            defaultX={40}
            defaultY={440}
            defaultWidth={340}
            defaultHeight={320}
          >
            <BodyRotateWidget config={config} onChange={setConfig} />
          </DraggablePanel>

          {/* Trackers Panel - Right Middle */}
          <DraggablePanel
            title={t('configPanel.tabs.trackers')}
            defaultX={400}
            defaultY={400}
            defaultWidth={340}
            defaultHeight={360}
          >
            <TrackersWidget config={config} onChange={setConfig} />
          </DraggablePanel>

          {/* Body Tree Panel - Right Side */}
          <DraggablePanel
            title={t('configPanel.tabs.bodyTree')}
            defaultX={760}
            defaultY={100}
            defaultWidth={300}
            defaultHeight={320}
          >
            <BodyTreeWidget bodyTree={bodyTree} />
          </DraggablePanel>

          {/* Action Buttons - Bottom Center */}
          <div
            style={{
              position: 'absolute',
              bottom: 40,
              left: '50%',
              transform: 'translateX(-50%)',
              zIndex: 50,
            }}
          >
            <Space>
              <Upload.Dragger
                showUploadList={false}
                accept=".bvh,.npz"
                beforeUpload={async (file) => {
                  try {
                    const result = await modelApi.uploadMotion(file, generatorType);
                    if (result.status === 'uploaded') {
                      setSelectedMotion(result.filename);
                      message.success(t('message.uploadSuccess'));
                    }
                  } catch (error) {
                    message.error(t('message.uploadFailed'));
                  }
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

export default App;
