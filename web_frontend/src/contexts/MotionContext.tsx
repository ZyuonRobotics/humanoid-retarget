import React, { createContext, useContext, useState, useCallback, useRef, ReactNode } from 'react';
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
  streamingFrames: Map<number, any>;
  streamingMetadata: any | null;
  isStreaming: boolean;
  streamingProgress: { current: number; total: number };
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

  // Streaming state - use ref to avoid triggering re-renders on every frame
  const streamingFramesRef = useRef<Map<number, any>>(new Map());
  const [streamingFrames, setStreamingFrames] = useState<Map<number, any>>(new Map());
  const [streamingMetadata, setStreamingMetadata] = useState<any | null>(null);
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamingProgress, setStreamingProgress] = useState({ current: 0, total: 0 });

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
    setIsStreaming(true);
    streamingFramesRef.current = new Map();
    setStreamingFrames(new Map());
    setStreamingMetadata(null);
    setStreamingProgress({ current: 0, total: 0 });

    try {
      // Use streaming retarget
      modelApi.retargetStream(
        selectedMotion,
        selectedRobot,
        generatorType,
        selectedConfig,
        // onMetadata
        (metadata) => {
          console.log('Received metadata:', metadata);
          setStreamingMetadata(metadata);
          setStreamingProgress({ current: 0, total: metadata.frame_num });
          message.success(t('message.retargetStarted'));
        },
        // onFrame
        (frameData) => {
          console.log('Received frame:', frameData.frame_id);
          // Update ref directly (no re-render)
          streamingFramesRef.current.set(frameData.frame_id, frameData);
          // Only trigger state update every 10 frames or on last frame to reduce re-renders
          const shouldUpdate = frameData.frame_id % 10 === 0 || frameData.frame_id === streamingProgress.total - 1;
          if (shouldUpdate) {
            setStreamingFrames(new Map(streamingFramesRef.current));
          }
          setStreamingProgress(prev => ({ ...prev, current: frameData.frame_id + 1 }));
        },
        // onComplete
        () => {
          console.log('Streaming complete');
          setIsStreaming(false);
          setLoading(false);
          // Final update to ensure all frames are reflected in state
          setStreamingFrames(new Map(streamingFramesRef.current));
          message.success(t('message.retargetComplete'));
        },
        // onError
        (error) => {
          console.error('Streaming error:', error);
          setIsStreaming(false);
          setLoading(false);
          message.error(error);
        }
      );
    } catch (error: any) {
      setIsStreaming(false);
      setLoading(false);
      if (error?.response?.status === 400 && error?.response?.data) {
        const detail = error.response.data;
        const msg = typeof detail === 'string' ? detail : (detail?.detail || JSON.stringify(detail));
        message.error(msg);
      } else {
        message.error(t('message.retargetFailed'));
      }
    }
  }, [selectedMotion, selectedRobot, generatorType, selectedConfig, t]);

  const handleSaveRetarget = useCallback(async () => {
    if (!retargetPreviewData && !streamingMetadata) {
      message.warning(t('message.noRetargetPreview'));
      return;
    }
    setLoading(true);
    try {
      const result = await modelApi.saveRetarget();
      if (result.status === 'success') {
        message.success(t('message.retargetSuccess'));
        setRetargetPreviewData(null);
        setStreamingMetadata(null);
        streamingFramesRef.current = new Map();
        setStreamingFrames(new Map());
      } else {
        message.error(t('message.retargetFailed'));
      }
    } catch (error) {
      message.error(t('message.retargetFailed'));
    } finally {
      setLoading(false);
    }
  }, [retargetPreviewData, streamingMetadata, t]);

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
        streamingFrames,
        streamingMetadata,
        isStreaming,
        streamingProgress,
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