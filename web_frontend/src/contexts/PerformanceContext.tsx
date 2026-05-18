import React, { createContext, useContext, useState, ReactNode } from 'react';

export interface PerformanceSettings {
  lowPerformanceMode: boolean;
  geometryDetail: number; // segments for spheres/cylinders
  shadowMapSize: number;
  maxPixelRatio: number;
  antialiasing: boolean;
}

interface PerformanceContextType {
  settings: PerformanceSettings;
  setLowPerformanceMode: (enabled: boolean) => void;
}

const defaultSettings: PerformanceSettings = {
  lowPerformanceMode: false,
  geometryDetail: 32,
  shadowMapSize: 2048,
  maxPixelRatio: Infinity,
  antialiasing: true,
};

const lowPerformanceSettings: PerformanceSettings = {
  lowPerformanceMode: true,
  geometryDetail: 16,
  shadowMapSize: 1024,
  maxPixelRatio: 1.5,
  antialiasing: false,
};

const PerformanceContext = createContext<PerformanceContextType | undefined>(undefined);

interface PerformanceProviderProps {
  children: ReactNode;
}

export const PerformanceProvider: React.FC<PerformanceProviderProps> = ({ children }) => {
  const [settings, setSettings] = useState<PerformanceSettings>(() => {
    // Load from localStorage, default to low performance mode
    const saved = localStorage.getItem('performanceMode');
    return saved === 'high' ? defaultSettings : lowPerformanceSettings;
  });

  const setLowPerformanceMode = (enabled: boolean) => {
    const newSettings = enabled ? lowPerformanceSettings : defaultSettings;
    setSettings(newSettings);
    localStorage.setItem('performanceMode', enabled ? 'low' : 'high');
  };

  return (
    <PerformanceContext.Provider value={{ settings, setLowPerformanceMode }}>
      {children}
    </PerformanceContext.Provider>
  );
};

export const usePerformanceContext = () => {
  const context = useContext(PerformanceContext);
  if (context === undefined) {
    throw new Error('usePerformanceContext must be used within a PerformanceProvider');
  }
  return context;
};
