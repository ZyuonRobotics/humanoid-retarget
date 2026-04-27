import React, { createContext, useContext, useState, useCallback, ReactNode } from 'react';
import { message } from 'antd';
import { useTranslation } from 'react-i18next';
import { modelApi, RetargetPreviewResponse } from '../api/client';
import { useConfigContext } from './ConfigContext';

interface MotionContextType {
  selectedMotion: string;
  setSelectedMotion: (motion: string) => void;
  loading: boolean;
  uploadMotion: (file: File) => Promise<void>;
  handleRetarget: () => Promise<void>;
  handleSaveRetarget: () => Promise<void>;
  retargetPreviewData: RetargetPreviewResponse | null;
  setRetargetPreviewData: (data: RetargetPreviewResponse | null) => void;
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
  const [retargetPreviewData, setRetargetPreviewData] = useState<RetargetPreviewResponse | null>(null);

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
      // Call retarget-preview instead of retarget to get preview data without saving
      const result = await modelApi.retargetPreview(
        selectedMotion,
        selectedRobot,
        generatorType,
        selectedConfig
      );
      if (result.status === 'success') {
        setRetargetPreviewData(result);
        message.success(t('message.retargetPreviewSuccess') || 'Retarget preview generated successfully');
      } else {
        message.error(t('message.retargetFailed'));
      }
    } catch (error: any) {
      // Check if it's a 400 error with human config message
      if (error?.response?.status === 400 && error?.response?.data) {
        const detail = error.response.data;
        const msg = typeof detail === 'string' ? detail : (detail?.detail || JSON.stringify(detail));
        message.error(msg);
      } else {
        message.error(t('message.retargetFailed'));
      }
    } finally {
      setLoading(false);
    }
  }, [selectedMotion, selectedRobot, generatorType, selectedConfig, t]);

  const handleSaveRetarget = useCallback(async () => {
    if (!retargetPreviewData) {
      message.warning('No retarget preview to save');
      return;
    }
    setLoading(true);
    try {
      const result = await modelApi.saveRetarget();
      if (result.status === 'success') {
        message.success(t('message.retargetSuccess'));
        setRetargetPreviewData(null);
      } else {
        message.error(t('message.retargetFailed'));
      }
    } catch (error) {
      message.error(t('message.retargetFailed'));
    } finally {
      setLoading(false);
    }
  }, [retargetPreviewData, t]);

  return (
    <MotionContext.Provider
      value={{
        selectedMotion,
        setSelectedMotion,
        loading,
        uploadMotion,
        handleRetarget,
        handleSaveRetarget,
        retargetPreviewData,
        setRetargetPreviewData,
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