import React, { createContext, useContext, useState, useCallback, ReactNode } from 'react';
import { message } from 'antd';
import { useTranslation } from 'react-i18next';
import { modelApi } from '../api/client';
import { useConfigContext } from './ConfigContext';

interface MotionContextType {
  selectedMotion: string;
  setSelectedMotion: (motion: string) => void;
  loading: boolean;
  uploadMotion: (file: File) => Promise<void>;
  handleRetarget: () => Promise<void>;
}

const MotionContext = createContext<MotionContextType | undefined>(undefined);

interface MotionProviderProps {
  children: ReactNode;
}

export const MotionProvider: React.FC<MotionProviderProps> = ({ children }) => {
  const { t } = useTranslation();
  const { selectedRobot, generatorType, selectedConfig } = useConfigContext();
  const [selectedMotion, setSelectedMotion] = useState<string>('');
  const [loading, setLoading] = useState(false);

  const uploadMotion = useCallback(async (file: File) => {
    try {
      const result = await modelApi.uploadMotion(file, generatorType);
      if (result.status === 'uploaded') {
        setSelectedMotion(result.filename);
        message.success(t('message.uploadSuccess'));
      }
    } catch (error) {
      message.error(t('message.uploadFailed'));
    }
  }, [generatorType, t]);

  const handleRetarget = useCallback(async () => {
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
  }, [selectedMotion, selectedRobot, generatorType, selectedConfig, t]);

  return (
    <MotionContext.Provider
      value={{
        selectedMotion,
        setSelectedMotion,
        loading,
        uploadMotion,
        handleRetarget,
      }}
    >
      {children}
    </MotionContext.Provider>
  );
};

export const useMotionContext = () => {
  const context = useContext(MotionContext);
  if (context === undefined) {
    throw new Error('useMotionContext must be used within a MotionProvider');
  }
  return context;
};