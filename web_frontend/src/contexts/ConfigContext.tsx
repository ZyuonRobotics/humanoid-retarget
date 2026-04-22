import React, { createContext, useContext, useState, useCallback, useEffect, useRef, ReactNode } from 'react';
import { message, Modal } from 'antd';
import { useTranslation } from 'react-i18next';
import { configApi } from '../api/client';
import { RobotInfo, RetargetConfig, defaultRetargetConfig, BodyTree } from '../types/config';

interface ConfigContextType {
  robots: RobotInfo[];
  selectedRobot: string;
  setSelectedRobot: (robot: string) => void;
  generatorType: string;
  setGeneratorType: (type: string) => void;
  selectedMotionFile: string;
  setSelectedMotionFile: (motion: string) => void;
  configs: string[];
  selectedConfig: string;
  setSelectedConfig: (config: string) => void;
  config: RetargetConfig;
  setConfig: (config: RetargetConfig) => void;
  bodyTree: BodyTree;
  loading: boolean;
  saving: boolean;
  loadRobots: () => Promise<void>;
  loadConfigs: () => Promise<void>;
  loadConfig: () => Promise<void>;
  loadBodyTree: (motionFile?: string) => Promise<void>;
  saveConfig: () => Promise<void>;
  handleCreateConfig: (name: string) => Promise<void>;
  handleDeleteConfig: () => void;
}

const ConfigContext = createContext<ConfigContextType | undefined>(undefined);

interface ConfigProviderProps {
  children: ReactNode;
}

export const ConfigProvider: React.FC<ConfigProviderProps> = ({ children }) => {
  const { t } = useTranslation();
  const [robots, setRobots] = useState<RobotInfo[]>([]);
  const [selectedRobot, setSelectedRobot] = useState<string>('');
  const [generatorType, setGeneratorType] = useState<string>('bvh');
  const [selectedMotionFile, setSelectedMotionFile] = useState<string>('');
  const [configs, setConfigs] = useState<string[]>([]);
  const [selectedConfig, setSelectedConfig] = useState<string>('default');
  const [config, setConfig] = useState<RetargetConfig>(defaultRetargetConfig);
  const [bodyTree, setBodyTree] = useState<BodyTree>({});
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const requestIdRef = useRef(0);

  const loadRobots = useCallback(async () => {
    try {
      const data = await configApi.getRobots();
      // Handle both old format (string[]) and new format (RobotInfo[])
      if (Array.isArray(data) && data.length > 0) {
        if (typeof data[0] === 'string') {
          // Old format - convert to new format
          setRobots((data as string[]).map(name => ({ name })));
          setSelectedRobot(data[0] as string);
        } else {
          // New format
          const robots = data as unknown as RobotInfo[];
          setRobots(robots);
          setSelectedRobot(robots[0].name);
        }
      }
    } catch (error) {
      message.error(t('message.failedToLoadRobots'));
    }
  }, [t]);

  const loadConfigs = useCallback(async () => {
    const currentRequestId = ++requestIdRef.current;
    try {
      const data = await configApi.listConfigs(selectedRobot, generatorType);
      if (currentRequestId !== requestIdRef.current) return;
      setConfigs(data);
      if (data.length > 0) {
        setSelectedConfig(data[0]);
      } else {
        setSelectedConfig('');
        message.info(t('configPanel.message.noConfigsPleaseCreate'));
      }
    } catch (error) {
      if (currentRequestId !== requestIdRef.current) return;
      message.error(t('message.failedToLoadConfigs'));
    }
  }, [selectedRobot, generatorType, t]);

  const loadConfig = useCallback(async () => {
    setLoading(true);
    const currentRequestId = ++requestIdRef.current;
    try {
      const data = await configApi.getConfig(selectedRobot, generatorType, selectedConfig);
      if (currentRequestId !== requestIdRef.current) return;
      setConfig(data);
    } catch (error) {
      setConfig(defaultRetargetConfig);
    } finally {
      if (currentRequestId === requestIdRef.current) {
        setLoading(false);
      }
    }
  }, [selectedRobot, generatorType, selectedConfig]);

  const loadBodyTree = useCallback(async (motionFile?: string) => {
    const currentRequestId = ++requestIdRef.current;
    try {
      const data = await configApi.getBodyTree(selectedRobot, generatorType, motionFile);
      if (currentRequestId !== requestIdRef.current) return;
      setBodyTree(data);
    } catch (error) {
      console.error('Failed to load body tree', error);
      if (currentRequestId === requestIdRef.current) {
        setBodyTree({ human: { error: 'Failed to load body tree' } });
      }
    }
  }, [selectedRobot, generatorType]);

  const saveConfig = useCallback(async () => {
    setSaving(true);
    try {
      await configApi.saveConfig(selectedRobot, generatorType, selectedConfig, config);
      message.success(t('configPanel.message.configSaved'));
    } catch (error) {
      message.error(t('configPanel.message.failedToSaveConfig'));
    } finally {
      setSaving(false);
    }
  }, [selectedRobot, generatorType, selectedConfig, config, t]);

  const handleCreateConfig = useCallback(async (name: string) => {
    try {
      await configApi.saveConfig(selectedRobot, generatorType, name, config);
      await loadConfigs();
      setSelectedConfig(name);
      message.success(t('configPanel.message.configCreated'));
    } catch (error) {
      message.error(t('configPanel.message.failedToCreateConfig'));
    }
  }, [selectedRobot, generatorType, config, loadConfigs, t]);

  const handleDeleteConfig = useCallback(() => {
    Modal.confirm({
      title: t('configPanel.deleteConfirmTitle'),
      content: t('configPanel.deleteConfirmContent', { name: selectedConfig }),
      okText: t('common.ok'),
      cancelText: t('common.cancel'),
      onOk: async () => {
        try {
          await configApi.deleteConfig(selectedRobot, generatorType, selectedConfig);
          message.success(t('configPanel.message.configDeleted'));
          await loadConfigs();
          if (configs.length > 1) {
            const newConfigs = configs.filter((c) => c !== selectedConfig);
            setSelectedConfig(newConfigs[0]);
          }
        } catch (error) {
          message.error(t('configPanel.message.failedToDeleteConfig'));
        }
      },
    });
  }, [selectedConfig, selectedRobot, generatorType, configs, loadConfigs, t]);

  useEffect(() => {
    loadRobots();
  }, [loadRobots]);

  useEffect(() => {
    if (selectedRobot && generatorType) {
      loadConfigs();
      loadBodyTree(selectedMotionFile || undefined);
    }
  }, [selectedRobot, generatorType, loadConfigs, loadBodyTree, selectedMotionFile]);

  useEffect(() => {
    if (selectedRobot && generatorType && selectedConfig) {
      loadConfig();
    }
  }, [selectedRobot, generatorType, selectedConfig, loadConfig]);

  return (
    <ConfigContext.Provider
      value={{
        robots,
        selectedRobot,
        setSelectedRobot,
        generatorType,
        setGeneratorType,
        selectedMotionFile,
        setSelectedMotionFile,
        configs,
        selectedConfig,
        setSelectedConfig,
        config,
        setConfig,
        bodyTree,
        loading,
        saving,
        loadRobots,
        loadConfigs,
        loadConfig,
        loadBodyTree,
        saveConfig,
        handleCreateConfig,
        handleDeleteConfig,
      }}
    >
      {children}
    </ConfigContext.Provider>
  );
};

export const useConfigContext = () => {
  const context = useContext(ConfigContext);
  if (context === undefined) {
    throw new Error('useConfigContext must be used within a ConfigProvider');
  }
  return context;
};