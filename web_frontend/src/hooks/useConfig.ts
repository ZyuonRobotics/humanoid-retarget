import { useCallback } from 'react';
import { RetargetConfig, TrackerConfig } from '../types/config';

export function useConfig(
  config: RetargetConfig,
  onChange: (config: RetargetConfig) => void
) {
  const updateConfig = useCallback(
    (key: keyof RetargetConfig, value: unknown) => {
      onChange({ ...config, [key]: value });
    },
    [config, onChange]
  );

  const addTracker = useCallback(() => {
    const key = `tracker_${Object.keys(config.tracker_dict).length + 1}`;
    updateConfig('tracker_dict', {
      ...config.tracker_dict,
      [key]: { human: [], robot: [], position_cost: 1.0, orientation_cost: 1.0 } as TrackerConfig,
    });
  }, [config.tracker_dict, updateConfig]);

  const removeTracker = useCallback(
    (key: string) => {
      const newDict = { ...config.tracker_dict };
      delete newDict[key];
      updateConfig('tracker_dict', newDict);
    },
    [config.tracker_dict, updateConfig]
  );

  const updateTracker = useCallback(
    (key: string, tracker: TrackerConfig) => {
      updateConfig('tracker_dict', { ...config.tracker_dict, [key]: tracker });
    },
    [config.tracker_dict, updateConfig]
  );

  return {
    updateConfig,
    addTracker,
    removeTracker,
    updateTracker,
  };
}
